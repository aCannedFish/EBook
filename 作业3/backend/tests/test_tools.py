"""书目检索与两个工具的测试。"""

from __future__ import annotations

import pytest

from backend.catalog import Catalog
from backend.tools import (
    BookstoreTools,
    ToolRegistry,
    build_registry,
    describe_tools,
    TOOL_SCHEMAS,
)


@pytest.fixture(scope="module")
def catalog():
    return Catalog()


class TestCatalog:
    def test_title_match_ranks_first(self, catalog):
        hits = catalog.search("微服务", limit=3, min_score=1.0)
        assert hits[0][0].title.startswith("微服务")
        assert hits[0][1] > hits[-1][1]

    def test_max_price_filter(self, catalog):
        hits = catalog.search("微服务", max_price=80, limit=5, min_score=1.0)
        assert hits and all(book.price <= 80 for book, _, _ in hits)

    def test_in_stock_filter_and_out_of_stock_listing(self, catalog):
        in_stock = catalog.search("微服务", in_stock_only=True, limit=10, min_score=1.0)
        assert all(book.in_stock for book, _, _ in in_stock)
        everything = catalog.search("微服务", limit=10, min_score=1.0)
        assert any(not book.in_stock for book, _, _ in everything)

    def test_low_relevance_is_rejected(self, catalog):
        assert catalog.search("Rust", limit=3, min_score=1.0) == []

    def test_empty_query_has_no_hits(self, catalog):
        assert catalog.search("", min_score=0.0) == []

    def test_matched_terms_are_readable(self, catalog):
        hits = catalog.search("Kubernetes", limit=1, min_score=1.0)
        assert hits[0][2]


class TestSearchBookCatalogTool:
    def test_returns_books_with_payload_fields(self, tools):
        payload = tools.search_book_catalog("微服务")
        assert payload["count"] == len(payload["results"]) == 3
        first = payload["results"][0]
        assert set(first) >= {"isbn", "title", "price", "stockQty", "inStock", "score", "matchedTerms"}
        assert payload["source"] == "mock-catalog"

    def test_filters_are_passed_through(self, tools):
        payload = tools.search_book_catalog("微服务", max_price=100, in_stock_only=True, limit=5)
        assert payload["filters"]["maxPrice"] == 100
        assert payload["filters"]["inStockOnly"] is True
        assert all(book["price"] <= 100 and book["inStock"] for book in payload["results"])

    def test_out_of_stock_matches_do_not_duplicate_results(self, tools):
        payload = tools.search_book_catalog("微服务", limit=10)
        listed = {book["title"] for book in payload["results"]}
        assert not listed & set(payload["outOfStockMatches"])

    def test_no_match_raises_with_hint(self, tools):
        with pytest.raises(Exception) as error:
            tools.search_book_catalog("Rust")
        assert error.value.code == "CATALOG_NO_MATCH"
        assert error.value.retryable is True
        assert "分类" in error.value.hint

    def test_category_and_price_validation(self, tools):
        with pytest.raises(Exception) as error:
            tools.search_book_catalog("")
        assert error.value.code == "INVALID_ARGUMENT"

        with pytest.raises(Exception) as error:
            tools.search_book_catalog("微服务", limit=99)
        assert error.value.code == "INVALID_ARGUMENT"

        with pytest.raises(Exception) as error:
            tools.search_book_catalog("微服务", max_price="不限")
        assert error.value.code == "INVALID_ARGUMENT"

    def test_category_filter(self, tools):
        payload = tools.search_book_catalog("编程", category="计算机")
        assert all("计算机" in book["category"] for book in payload["results"])


class TestQueryStorePolicyTool:
    def test_returns_passages_with_citations(self, tools):
        payload = tools.query_store_policy("拆了塑封还能退吗")
        assert payload["count"] >= 1
        assert payload["source"] == "policy-rag"
        top = payload["passages"][0]
        assert top["clause"].startswith("第六条")
        assert 0 < top["score"] <= 1
        assert "塑封" in top["text"]
        assert payload["index"]["chunks"] > 0

    def test_top_k_is_honoured(self, tools):
        assert tools.query_store_policy("退货", top_k=1)["count"] == 1

    def test_uncovered_question_raises(self, tools):
        with pytest.raises(Exception) as error:
            tools.query_store_policy("海外直邮的书可以退吗")
        assert error.value.code == "POLICY_NOT_COVERED"
        assert error.value.retryable is True
        assert "客服" in error.value.hint

    def test_blank_question_is_rejected(self, tools):
        with pytest.raises(Exception) as error:
            tools.query_store_policy("  ")
        assert error.value.code == "INVALID_ARGUMENT"

    def test_index_is_built_lazily(self):
        toolset = BookstoreTools()
        assert toolset.index is None
        toolset.query_store_policy("退货运费谁承担")
        assert toolset.index is not None


class TestToolRegistry:
    def test_dispatch_wraps_success(self, tools):
        outcome = build_registry(tools).dispatch("search_book_catalog", {"query": "Kubernetes"})
        assert outcome.ok is True
        assert outcome.payload["ok"] is True
        assert outcome.duration_ms >= 0
        assert outcome.log_line().startswith("[TOOL] search_book_catalog -> ok")

    def test_dispatch_turns_errors_into_payloads(self, tools):
        outcome = build_registry(tools).dispatch("search_book_catalog", {"query": "Rust"})
        assert outcome.ok is False
        assert outcome.payload["error"]["code"] == "CATALOG_NO_MATCH"
        assert outcome.payload["error"]["retryable"] is True

    def test_unknown_tool_is_reported(self, tools):
        outcome = build_registry(tools).dispatch("no_such_tool", {})
        assert outcome.payload["error"]["code"] == "INVALID_ARGUMENT"
        assert "search_book_catalog" in outcome.payload["error"]["hint"]

    def test_bad_argument_names_are_reported(self, tools):
        outcome = build_registry(tools).dispatch("search_book_catalog", {"keyword": "微服务"})
        assert outcome.payload["error"]["code"] == "INVALID_ARGUMENT"
        assert outcome.payload["error"]["retryable"] is True

    def test_internal_errors_never_escape(self, tools):
        registry = build_registry(tools)

        def boom(**kwargs):
            raise RuntimeError("数据库连接断了")

        registry._handlers["search_book_catalog"] = boom
        outcome = registry.dispatch("search_book_catalog", {"query": "微服务"})
        assert outcome.ok is False
        assert outcome.payload["error"]["code"] == "TOOL_INTERNAL_ERROR"
        assert outcome.payload["error"]["retryable"] is False


class TestToolSchemas:
    def test_both_tools_are_declared(self):
        names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
        assert names == ["search_book_catalog", "query_store_policy"]

    def test_required_arguments(self):
        for schema in TOOL_SCHEMAS:
            function = schema["function"]
            assert function["parameters"]["required"]
            assert function["description"]
            assert function["parameters"]["additionalProperties"] is False

    def test_text_description_matches_schema(self):
        text = describe_tools()
        assert "search_book_catalog" in text
        assert "query_store_policy" in text
        assert "query:字符串（必填）" in text
        assert "可选" in text

    def test_registry_exposes_schemas(self, tools):
        registry = build_registry(tools)
        assert registry.names == ("search_book_catalog", "query_store_policy")
        assert registry.schemas == TOOL_SCHEMAS


def test_tools_default_registry_builds():
    assert isinstance(build_registry(), ToolRegistry)
