"""两个工具的 Schema 与实现：``search_book_catalog`` 与 ``query_store_policy``。

作业要求的两个工具：

1. ``search_book_catalog(query, ...)``  —— 模拟查书。按关键词在书目数据里检索，
   支持分类、价格上限、只看有货三个过滤条件。
2. ``query_store_policy(question, ...)`` —— 调用 RAG 检索政策库，返回带块编号与
   相似度的原文片段。

三个约定和作业2保持一致，因为它们在 ReAct 循环里同样成立：

1. Schema 用 OpenAI tools 格式声明（``TOOL_SCHEMAS``）。ReAct 提示词里的工具说明书
   由同一份 Schema 渲染（``describe_tools``），文字与参数只有一处来源，
   不会出现「提示词说支持某参数、实现里没这个参数」的偏差。
2. 函数可以直接调用（单元测试、CLI 都这么用），但在循环里一律走 ``dispatch``，
   由它把异常收敛成结构化错误。
3. 不向模型抛异常，而是返回 ``{"ok": false, "error": {...}}``。
   ``error.hint`` 是模型自我纠错的唯一输入：``retryable=true`` 表示换个说法再试，
   ``false`` 表示这条路走不通，应当如实告知用户。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .catalog import DEFAULT_CATALOG, Catalog
from .config import CATALOG, RAG
from .embedding import EmbeddingError
from .corpus import CorpusError
from .rag import RagIndex, RagPipeline


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class ToolError(Exception):
    """工具层异常基类。code 给模型看，hint 给模型用来纠错。"""

    code = "TOOL_ERROR"
    retryable = False

    def __init__(self, message: str, hint: str, *, retryable: bool | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        if retryable is not None:
            self.retryable = retryable


class InvalidArgumentError(ToolError):
    code = "INVALID_ARGUMENT"


class CatalogNoMatchError(ToolError):
    """书目检索没有命中任何一本。可换个更宽的关键词重试。"""

    code = "CATALOG_NO_MATCH"
    retryable = True


class PolicyNotCoveredError(ToolError):
    """政策库中没有与问题足够相关的条款。可换个说法重试。"""

    code = "POLICY_NOT_COVERED"
    retryable = True


class PolicyIndexError(ToolError):
    """政策索引不可用（语料缺失、向量化失败）。重试没有意义。"""

    code = "POLICY_INDEX_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------


def _require_text(value: Any, name: str, hint: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise InvalidArgumentError(f"缺少必填参数 {name}", hint=hint)
    if not isinstance(value, str):
        raise InvalidArgumentError(
            f"参数 {name} 必须是字符串，收到 {type(value).__name__}",
            hint=f"把 {name} 写成字符串再调用一次。",
        )
    return value.strip()


def _optional_int(value: Any, name: str, low: int, high: int) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidArgumentError(
            f"参数 {name} 必须是整数，收到 {type(value).__name__}",
            hint=f"{name} 去掉单位，只写数字，例如 {low}。",
        )
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        raise InvalidArgumentError(
            f"参数 {name} 不是合法整数：{value!r}",
            hint=f"{name} 只写数字，例如 {low}。",
        ) from None
    if parsed < low or parsed > high:
        raise InvalidArgumentError(
            f"参数 {name} 必须在 {low} 到 {high} 之间，收到 {parsed}",
            hint=f"把 {name} 调整到 {low} 至 {high} 之间再调用。",
        )
    return parsed


def _optional_bool(value: Any, name: str) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "是"}:
            return True
        if lowered in {"false", "0", "no", "否"}:
            return False
    raise InvalidArgumentError(
        f"参数 {name} 必须是布尔值，收到 {value!r}",
        hint=f"{name} 只能写 true 或 false。",
    )


# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------


@dataclass
class BookstoreTools:
    """两个工具的实现。

    ``index`` 懒加载：只查书的时候不必先建政策索引，
    索引构建耗时与语料规模成正比，把它挂在第一次政策查询上，
    启动与只查书的链路都不会被拖慢。
    """

    catalog: Catalog = DEFAULT_CATALOG
    index: RagIndex | None = None
    pipeline: RagPipeline | None = None

    # -- 工具一：模拟查书 ---------------------------------------------------
    def search_book_catalog(
        self,
        query: str,
        category: str | None = None,
        max_price: int | None = None,
        in_stock_only: bool = False,
        limit: int | None = None,
    ) -> dict:
        """按关键词检索书目。

        :raises InvalidArgumentError: 参数缺失或类型不对
        :raises CatalogNoMatchError: 没有命中的书
        """
        query = _require_text(
            query,
            "query",
            hint="query 是要检索的主题词，例如「微服务」「Kubernetes」「余华」。",
        )
        limit = _optional_int(limit, "limit", 1, CATALOG.max_limit) or CATALOG.default_limit
        max_price = _optional_int(max_price, "max_price", 1, 100000)
        in_stock_only = _optional_bool(in_stock_only, "in_stock_only")
        if category is not None and not isinstance(category, str):
            raise InvalidArgumentError(
                f"参数 category 必须是字符串，收到 {type(category).__name__}",
                hint="category 用书名里的分类词，例如「计算机」。",
            )

        hits = self.catalog.search(
            query,
            category=category,
            max_price=max_price,
            in_stock_only=in_stock_only,
            limit=limit,
            min_score=CATALOG.min_score,
        )

        if not hits:
            raise CatalogNoMatchError(
                f"书目中没有与「{query}」足够匹配的图书（相关度阈值 {CATALOG.min_score}）",
                hint=(
                    "换一个更宽的主题词再试一次，例如把「Rust 异步编程」放宽成「编程」"
                    "「架构」，或去掉价格与分类限制。可选分类："
                    + "、".join(self.catalog.categories())
                    + "。"
                ),
            )

        # 命中但被过滤掉的数量：如果是因为「只看有货」把书滤没了，
        # 模型应当知道「有这本书但缺货」，而不是「没有这本书」。
        # 已经在结果里的缺货书不再重复列一遍。
        listed = {book["isbn"] for book in (item.to_payload() for item, _, _ in hits)}
        out_of_stock_matches = [
            book
            for book, _, _ in self.catalog.search(
                query,
                category=category,
                max_price=max_price,
                in_stock_only=False,
                limit=CATALOG.max_limit,
                min_score=CATALOG.min_score,
            )
            if not book.in_stock and book.isbn not in listed
        ]

        return {
            "query": query,
            "filters": {
                "category": category,
                "maxPrice": max_price,
                "inStockOnly": in_stock_only,
                "limit": limit,
            },
            "count": len(hits),
            "results": [book.to_payload(score, matched) for book, score, matched in hits],
            "outOfStockMatches": [book.title for book in out_of_stock_matches],
            "source": "mock-catalog",
        }

    # -- 工具二：RAG 检索政策 -----------------------------------------------
    def query_store_policy(self, question: str, top_k: int | None = None) -> dict:
        """在政策库中检索与问题相关的条款。

        :raises InvalidArgumentError: 问题为空
        :raises PolicyNotCoveredError: 没有达到相似度阈值的条款
        :raises PolicyIndexError: 索引不可用
        """
        question = _require_text(
            question,
            "question",
            hint="question 是要查的政策问题，例如「拆了塑封还能退吗」。",
        )
        top_k = _optional_int(top_k, "top_k", 1, 6) or RAG.top_k

        index = self.ensure_index()
        passages = index.retrieve(question, top_k=top_k)

        if not passages:
            raise PolicyNotCoveredError(
                f"政策库中没有与「{question}」足够相关的条款（相似度阈值 {RAG.min_score}）",
                hint=(
                    "换一个更贴近政策原文的说法再查一次，例如把「不喜欢能退吗」换成"
                    "「七天无理由退货」「塑封拆封」「会员日折扣」。"
                    "如果换过说法仍然查不到，说明政策库确实没有覆盖这个问题，"
                    "应当如实告知用户并建议联系客服，不要自行推测。"
                ),
            )

        return {
            "question": question,
            "topScore": round(passages[0].score, 4),
            "count": len(passages),
            "passages": [item.to_dict() for item in passages],
            "source": "policy-rag",
            "index": {
                "embedder": index.embedder.name if index.embedder else "",
                "chunks": len(index.chunks),
                "fingerprint": index.fingerprint,
            },
        }

    # -- 索引管理 -----------------------------------------------------------
    def ensure_index(self, force: bool = False) -> RagIndex:
        if self.index is None or force:
            if self.pipeline is None:
                self.pipeline = RagPipeline()
            try:
                self.index = self.pipeline.build(force=force)
            except (CorpusError, EmbeddingError) as error:
                hint = getattr(error, "hint", "") or "检查 data/policy.txt 与向量化配置。"
                raise PolicyIndexError(
                    f"政策索引构建失败：{error}",
                    hint=f"{hint} 该问题重试没有意义，请如实告知用户政策查询暂时不可用。",
                ) from error
        return self.index


# ---------------------------------------------------------------------------
# Tool Schema
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_book_catalog",
            "description": (
                "在本店书目中按主题关键词检索图书，返回书名、作者、价格、库存与简介。"
                "当用户想买书、要求推荐、询问某类主题有没有货时调用。"
                "query 用主题词而不是整句话，例如「微服务」「Kubernetes」「算法」。"
                "用户提到预算就传 max_price，只想要能立刻下单的书就传 in_stock_only=true。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "主题关键词，如「微服务」「云原生」「量子物理」。不要传整句问句。",
                    },
                    "category": {
                        "type": "string",
                        "description": "可选，按分类过滤，如「计算机」「文学」。不确定就不要传。",
                    },
                    "max_price": {
                        "type": "integer",
                        "description": "可选，价格上限（元）。用户说「100 块以内」时传 100。",
                    },
                    "in_stock_only": {
                        "type": "boolean",
                        "description": "可选，为 true 时只返回有货的书。用户着急买时传 true。",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "可选，返回条数上限，默认 3，最大 10。",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_store_policy",
            "description": (
                "检索本店《退换货与会员政策》原文，返回相关条款片段、所属条款号与相似度。"
                "当用户询问退货、换货、退款、塑封拆封、运费、会员等级、折扣、积分、"
                "发票、价保等政策问题时调用。question 写成一句政策问题，"
                "例如「拆了塑封还能退吗」「金卡会员有什么折扣」。"
                "回答必须引用返回的条款，不得凭常识推测政策。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要查的政策问题，一句一查。多个问题请分多次调用。",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "可选，返回条款数，默认 3，最大 6。",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_NAMES = tuple(schema["function"]["name"] for schema in TOOL_SCHEMAS)

_JSON_TYPES = {
    "string": "字符串",
    "integer": "整数",
    "boolean": "布尔值",
}


def describe_tools(schemas: list[dict] | None = None) -> str:
    """把 Tool Schema 渲染成 ReAct 提示词里的工具说明书。

    ReAct 走的是纯文本协议，没有 ``tools`` 字段可用，
    所以模型只能靠这段文字知道有哪些工具、参数怎么填。
    """
    schemas = schemas or TOOL_SCHEMAS
    lines: list[str] = []
    for index, schema in enumerate(schemas, start=1):
        function = schema["function"]
        parameters = function.get("parameters", {})
        required = set(parameters.get("required") or [])
        pieces = []
        for name, spec in (parameters.get("properties") or {}).items():
            type_name = _JSON_TYPES.get(spec.get("type", "string"), spec.get("type", "值"))
            mark = "必填" if name in required else "可选"
            pieces.append(f"{name}:{type_name}（{mark}）")
        signature = ", ".join(pieces)
        lines.append(f"{index}. {function['name']}({signature})")
        lines.append(f"   说明：{function['description']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 统一派发
# ---------------------------------------------------------------------------


@dataclass
class ToolOutcome:
    """一次工具调用的完整结果。"""

    name: str
    arguments: dict
    ok: bool
    payload: dict
    duration_ms: int

    def log_line(self) -> str:
        status = "ok" if self.ok else f"failed:{self.payload.get('error', {}).get('code')}"
        return f"[TOOL] {self.name} -> {status} ({self.duration_ms}ms)"


class ToolRegistry:
    """把 Schema、实现与派发绑在一起。"""

    def __init__(self, tools: BookstoreTools | None = None) -> None:
        self.tools = tools or BookstoreTools()
        self._handlers: dict[str, Callable[..., dict]] = {
            "search_book_catalog": self.tools.search_book_catalog,
            "query_store_policy": self.tools.query_store_policy,
        }

    @property
    def schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    @property
    def names(self) -> tuple[str, ...]:
        return TOOL_NAMES

    def dispatch(self, name: str, arguments: dict) -> ToolOutcome:
        """执行一次工具调用。**任何**失败都以结构化错误返回，不向上抛异常。"""
        started = time.perf_counter()
        try:
            handler = self._handlers.get(name)
            if handler is None:
                raise InvalidArgumentError(
                    f"不存在名为 {name} 的工具",
                    hint=f"可用工具只有：{'、'.join(self._handlers)}。请改用其中之一。",
                )
            payload = {"ok": True, **handler(**arguments)}
            ok = True
        except ToolError as error:
            payload = {
                "ok": False,
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "retryable": error.retryable,
                    "hint": error.hint,
                },
            }
            ok = False
        except TypeError as error:
            payload = {
                "ok": False,
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": f"参数与工具签名不匹配：{error}",
                    "retryable": True,
                    "hint": (
                        "只使用 Schema 里声明过的参数名，"
                        "例如 {\"query\": \"微服务\"}，不要自造参数名。"
                    ),
                },
            }
            ok = False
        except Exception as error:  # noqa: BLE001 - 兜底，避免任何异常打断 ReAct 循环
            payload = {
                "ok": False,
                "error": {
                    "code": "TOOL_INTERNAL_ERROR",
                    "message": f"{type(error).__name__}: {error}",
                    "retryable": False,
                    "hint": "工具内部错误，请如实告知用户暂时无法查询。",
                },
            }
            ok = False

        return ToolOutcome(
            name=name,
            arguments=arguments,
            ok=ok,
            payload=payload,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


def build_registry(tools: BookstoreTools | None = None) -> ToolRegistry:
    return ToolRegistry(tools)
