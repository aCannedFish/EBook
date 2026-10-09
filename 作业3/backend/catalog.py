"""模拟书目数据源与关键词检索。

作业要求的工具之一 ``search_book_catalog`` 是「模拟查书」，所以这里内置一份
书目数据（``DEMO_CATALOG``），字段与真实书城后端 ``GET /api/v1/books`` 对齐，
另外补充标签、评分、简介三项 —— 它们让「关于微服务的书」这种模糊需求有东西可匹配。

检索是纯本地的关键词打分，没有用向量：书目标题短、领域词明确，
按字段加权的关键词匹配已经足够，而且打分过程可解释 ——
返回结果里会带 ``matchedTerms``，模型（和读日志的人）能看出为什么这几本书被选中。

数据里刻意留了两个「坑」，用于演示 Agent 的自我纠错：
- 《微服务与容器化实践》库存为 0，用来触发「有货才推荐」的过滤；
- 目录里没有任何一本 Rust 书，用来触发「检索不到 → 换个说法再试」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

#: 字段权重：标题命中最能说明问题，标签次之，简介只作补充。
FIELD_WEIGHTS = {
    "title": 6.0,
    "tags": 4.0,
    "category": 3.0,
    "author": 2.0,
    "publisher": 1.5,
    "summary": 1.0,
}

CJK_RUN_PATTERN = re.compile(r"[一-鿿]+")
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-_]*|\d+")


@dataclass(frozen=True)
class Book:
    """书目条目。"""

    isbn: str
    title: str
    author: str
    publisher: str
    year: int
    price: int
    category: str
    tags: tuple[str, ...]
    summary: str
    stock_qty: int
    rating: float
    sales: int

    @property
    def in_stock(self) -> bool:
        return self.stock_qty > 0

    def searchable_fields(self) -> dict[str, str]:
        return {
            "title": self.title,
            "tags": " ".join(self.tags),
            "category": self.category,
            "author": self.author,
            "publisher": self.publisher,
            "summary": self.summary,
        }

    def to_payload(self, score: float = 0.0, matched: Sequence[str] = ()) -> dict:
        return {
            "isbn": self.isbn,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "year": self.year,
            "price": self.price,
            "category": self.category,
            "tags": list(self.tags),
            "summary": self.summary,
            "stockQty": self.stock_qty,
            "inStock": self.in_stock,
            "rating": self.rating,
            "sales": self.sales,
            "score": score,
            "matchedTerms": list(matched),
        }


DEMO_CATALOG: tuple[Book, ...] = (
    Book(
        isbn="978-7-111-60000-1",
        title="微服务架构设计模式",
        author="Chris Richardson",
        publisher="机械工业出版社",
        year=2019,
        price=129,
        category="计算机 / 软件架构",
        tags=("微服务", "架构", "分布式系统", "Spring Cloud", "领域驱动"),
        summary="从单体到微服务的拆分模式与迁移策略，覆盖服务边界、分布式事务与事件溯源。",
        stock_qty=42, rating=4.8, sales=3200,
    ),
    Book(
        isbn="978-7-115-40000-2",
        title="微服务设计",
        author="Sam Newman",
        publisher="人民邮电出版社",
        year=2016,
        price=79,
        category="计算机 / 软件架构",
        tags=("微服务", "架构", "服务拆分", "持续交付"),
        summary="讲清服务边界怎么划、集成方式怎么选、部署与监控怎么做，适合作为入门第一本。",
        stock_qty=8, rating=4.6, sales=2100,
    ),
    Book(
        isbn="978-1-61729-400-3",
        title="Spring Microservices in Action",
        author="John Carnell",
        publisher="Manning",
        year=2021,
        price=89,
        category="计算机 / 编程语言",
        tags=("微服务", "Spring Boot", "Java", "英文原版"),
        summary="以 Spring Boot 与 Spring Cloud 为主线，实现配置中心、网关、熔断与链路追踪。",
        stock_qty=15, rating=4.4, sales=860,
    ),
    Book(
        isbn="978-7-121-30000-4",
        title="微服务与容器化实践",
        author="张开元",
        publisher="电子工业出版社",
        year=2022,
        price=99,
        category="计算机 / 软件架构",
        tags=("微服务", "Docker", "Kubernetes", "云原生"),
        summary="用容器编排微服务的完整实践手册，包含 CI/CD 流水线与灰度发布案例。",
        stock_qty=0, rating=4.3, sales=1500,
    ),
    Book(
        isbn="978-7-111-50000-5",
        title="Kubernetes 权威指南",
        author="龚正",
        publisher="机械工业出版社",
        year=2020,
        price=168,
        category="计算机 / 运维",
        tags=("Kubernetes", "容器", "云原生", "运维"),
        summary="从集群搭建到生产运维，覆盖调度、网络、存储与安全加固。",
        stock_qty=6, rating=4.7, sales=1900,
    ),
    Book(
        isbn="978-7-115-20000-6",
        title="领域驱动设计：软件核心复杂性应对之道",
        author="Eric Evans",
        publisher="人民邮电出版社",
        year=2010,
        price=108,
        category="计算机 / 软件工程",
        tags=("领域驱动", "架构", "建模", "设计模式"),
        summary="领域模型、限界上下文与统一语言的经典之作，微服务拆分前必读。",
        stock_qty=12, rating=4.9, sales=2600,
    ),
    Book(
        isbn="978-7-111-20000-7",
        title="设计模式：可复用面向对象软件的基础",
        author="Erich Gamma",
        publisher="机械工业出版社",
        year=2007,
        price=79,
        category="计算机 / 软件工程",
        tags=("设计模式", "面向对象", "架构"),
        summary="二十三种经典设计模式的源头，讲的是怎么组织代码而不是怎么用框架。",
        stock_qty=3, rating=4.7, sales=4100,
    ),
    Book(
        isbn="978-7-111-30000-8",
        title="代码整洁之道",
        author="Robert C. Martin",
        publisher="人民邮电出版社",
        year=2010,
        price=69,
        category="计算机 / 软件工程",
        tags=("编程", "重构", "工程实践", "代码规范"),
        summary="命名、函数、注释与错误处理的具体做法，附带大量正反例对照。",
        stock_qty=18, rating=4.5, sales=5200,
    ),
    Book(
        isbn="978-7-115-30000-9",
        title="重构：改善既有代码的设计",
        author="Martin Fowler",
        publisher="人民邮电出版社",
        year=2019,
        price=118,
        category="计算机 / 软件工程",
        tags=("编程", "重构", "工程实践"),
        summary="以案例串起一整套重构手法，讲的是在不改变外部行为的前提下改结构。",
        stock_qty=7, rating=4.8, sales=1800,
    ),
    Book(
        isbn="978-7-121-40000-A",
        title="Go 语言并发编程实战",
        author="郝林",
        publisher="电子工业出版社",
        year=2018,
        price=79,
        category="计算机 / 编程语言",
        tags=("编程", "Go", "并发", "微服务"),
        summary="从 goroutine 与 channel 讲到并发模式与超时控制，适合写后端服务的人。",
        stock_qty=14, rating=4.4, sales=900,
    ),
    Book(
        isbn="978-7-111-40000-B",
        title="深入理解计算机系统",
        author="Randal E. Bryant",
        publisher="机械工业出版社",
        year=2016,
        price=139,
        category="计算机 / 计算机科学",
        tags=("计算机系统", "操作系统", "编译", "教材"),
        summary="从二进制表示讲到链接与并发，理解程序究竟是怎么跑起来的。",
        stock_qty=20, rating=4.9, sales=3400,
    ),
    Book(
        isbn="978-7-115-50000-C",
        title="算法导论",
        author="Thomas H. Cormen",
        publisher="人民邮电出版社",
        year=2012,
        price=128,
        category="计算机 / 计算机科学",
        tags=("算法", "数据结构", "教材"),
        summary="算法领域的标准教材，覆盖排序、图论、动态规划与 NP 完全性。",
        stock_qty=5, rating=4.8, sales=2200,
    ),
    Book(
        isbn="978-7-121-50000-D",
        title="量子物理导论",
        author="David J. Griffiths",
        publisher="电子工业出版社",
        year=2018,
        price=68,
        category="自然科学 / 物理",
        tags=("物理", "量子力学", "教材"),
        summary="以波函数与薛定谔方程为主线，兼顾数学推导与物理图像。",
        stock_qty=11, rating=4.6, sales=700,
    ),
    Book(
        isbn="978-7-121-60000-E",
        title="人类简史",
        author="尤瓦尔·赫拉利",
        publisher="中信出版社",
        year=2017,
        price=68,
        category="人文社科 / 历史",
        tags=("历史", "人类学", "畅销书"),
        summary="从认知革命讲到科学革命，讨论智人如何成为地球的主宰。",
        stock_qty=30, rating=4.5, sales=6800,
    ),
    Book(
        isbn="978-7-5063-60000-F",
        title="活着",
        author="余华",
        publisher="作家出版社",
        year=2012,
        price=45,
        category="文学 / 当代小说",
        tags=("小说", "当代文学", "畅销书"),
        summary="以福贵的一生写尽普通人在时代里的忍耐与坚韧。",
        stock_qty=25, rating=4.9, sales=9100,
    ),
    Book(
        isbn="978-7-301-60000-G",
        title="经济学原理",
        author="N. Gregory Mankiw",
        publisher="北京大学出版社",
        year=2020,
        price=98,
        category="经济管理 / 经济学",
        tags=("经济学", "教材", "微观经济", "宏观经济"),
        summary="以十大原理串联微观与宏观，是经济学入门的通用教材。",
        stock_qty=9, rating=4.7, sales=2600,
    ),
)


class Catalog:
    """书目检索。"""

    def __init__(self, books: Iterable[Book] = DEMO_CATALOG) -> None:
        self._books: list[Book] = list(books)
        self._field_features: dict[str, dict[str, set[str]]] = {}
        for book in self._books:
            self._field_features[book.isbn] = {
                name: features(text) for name, text in book.searchable_fields().items()
            }

    def __len__(self) -> int:
        return len(self._books)

    @property
    def books(self) -> list[Book]:
        return list(self._books)

    def categories(self) -> list[str]:
        return sorted({book.category for book in self._books})

    def search(
        self,
        query: str,
        category: str | None = None,
        max_price: int | None = None,
        in_stock_only: bool = False,
        limit: int = 3,
        min_score: float = 0.0,
    ) -> list[tuple[Book, float, list[str]]]:
        """返回 ``[(书, 得分, 命中词)]``，按得分降序（同分先看评分，再看销量）。

        ``min_score`` 是命中质量闸门：低于它的书直接不算命中，
        让上层能明确回答「没查到」，而不是给出一串沾边的结果。
        """
        query_features = features(query)
        if not query_features:
            return []

        hits: list[tuple[Book, float, list[str]]] = []
        for book in self._books:
            if category and category.lower() not in book.category.lower():
                continue
            if max_price is not None and book.price > max_price:
                continue
            if in_stock_only and not book.in_stock:
                continue

            score = 0.0
            matched: set[str] = set()
            for name, weight in FIELD_WEIGHTS.items():
                available = self._field_features[book.isbn][name]
                overlap = query_features & available
                if overlap:
                    score += weight * len(overlap)
                    matched |= overlap

            if score <= 0:
                continue
            # 归一化：得分与查询长度无关，阈值才好设，日志里的数字也才好比较。
            normalized = score / len(query_features)
            if normalized < min_score:
                continue
            hits.append((book, round(normalized, 3), _readable_terms(matched)))

        hits.sort(key=lambda item: (-item[1], -item[0].rating, -item[0].sales, item[0].title))
        return hits[: max(limit, 0)]


def features(text: str) -> set[str]:
    """把查询/字段切成特征集合：中文 bigram + 英文数字词。"""
    result: set[str] = set()
    for run in CJK_RUN_PATTERN.findall(text):
        if len(run) == 1:
            result.add(run)
        else:
            result.update(run[index : index + 2] for index in range(len(run) - 1))
            result.add(run)
    for word in WORD_PATTERN.findall(text):
        result.add(word.lower())
    return result


def _readable_terms(matched: set[str]) -> list[str]:
    """挑几个可读的命中词放进结果里（bigram 全列出来太吵）。"""
    words = sorted(term for term in matched if len(term) > 1 and not _is_cjk_bigram(term))
    if words:
        return words[:4]
    return sorted(matched, key=len, reverse=True)[:4]


def _is_cjk_bigram(term: str) -> bool:
    return len(term) == 2 and all("一" <= char <= "鿿" for char in term)


DEFAULT_CATALOG = Catalog()
