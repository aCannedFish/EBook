"""书店库存数据源。

两种后端实现：
- ``MockInventoryBackend``：内置目录，数据取自项目 springboot-ebook 的 data.sql 演示数据，
  不依赖任何外部服务，用于本地演示与单元测试。
- ``HttpInventoryBackend``：把请求转发到电子书城真实后端的 ``GET /api/v1/books``，
  设置环境变量 ``BOOKSTORE_API_BASE`` 后自动启用。

两者返回同一种结构，所以 tools.py 不需要关心数据到底从哪来。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .config import TOOLS

#: ISBN 归一化：去掉连字符与空格后，应剩下 10 位或 13 位数字。
#: 这里只校验长度与字符集，不校验 EAN-13 校验位 —— 项目演示数据里的 ISBN 是构造出来的，
#: 校验位并不合法，若开启校验位检查会把全部演示数据误判为非法输入。
ISBN_LENGTHS = (10, 13)


def normalize_isbn(raw: str) -> str:
    """去掉连字符、空格，并统一大写（ISBN-10 的尾位可能是 X）。"""
    return "".join(ch for ch in str(raw) if ch not in "- \t").upper()


def is_isbn_shaped(isbn: str) -> bool:
    if len(isbn) not in ISBN_LENGTHS:
        return False
    return isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X")


@dataclass(frozen=True)
class BookStock:
    """库存查询结果。"""

    isbn: str
    title: str
    author: str
    price: int
    category: str
    stock_qty: int
    stock_text: str

    @property
    def in_stock(self) -> bool:
        return self.stock_qty > 0

    def to_payload(self) -> dict:
        return {
            "isbn": self.isbn,
            "title": self.title,
            "author": self.author,
            "price": self.price,
            "category": self.category,
            "stockQty": self.stock_qty,
            "stockText": self.stock_text,
            "inStock": self.in_stock,
        }


# 与 springboot-ebook/src/main/resources/data.sql 保持一致。
DEMO_CATALOG: tuple[dict, ...] = (
    {
        "isbn": "978-0-00-000000-1",
        "title": "Digital Fundamentals",
        "author": "Thomas L. Floyd",
        "price": 59,
        "category": "电子技术 / 数字电路",
        "stock_qty": 50,
        "stock_text": "有货",
    },
    {
        "isbn": "978-1-00-000000-2",
        "title": "Fundamentals of Computer Graphics",
        "author": "Steve Marschner",
        "price": 88,
        "category": "计算机图形学",
        "stock_qty": 40,
        "stock_text": "有货",
    },
    {
        "isbn": "978-2-00-000000-3",
        "title": "Intorduction to Computing Systems",
        "author": "Yale N. Patt",
        "price": 79,
        "category": "计算机系统导论",
        "stock_qty": 4,
        "stock_text": "库存紧张",
    },
    {
        "isbn": "978-3-00-000000-4",
        "title": "Introduction To Algorithms",
        "author": "Thomas H. Cormen",
        "price": 99,
        "category": "算法",
        "stock_qty": 30,
        "stock_text": "有货",
    },
    {
        "isbn": "978-4-00-000000-5",
        "title": "Qt 6 C++开发指南",
        "author": "王维波",
        "price": 68,
        "category": "C++ / Qt",
        "stock_qty": 25,
        "stock_text": "有货",
    },
    {
        "isbn": "978-5-00-000000-6",
        "title": "应用随机过程",
        "author": "熊德文",
        "price": 56,
        "category": "数学 / 概率",
        "stock_qty": 20,
        "stock_text": "有货",
    },
    {
        "isbn": "978-6-00-000000-7",
        "title": "深入理解计算机系统",
        "author": "兰德尔·E·布莱恩特 / 大卫·R·奥哈拉伦",
        "price": 86,
        "category": "计算机系统",
        "stock_qty": 3,
        "stock_text": "库存紧张",
    },
    {
        "isbn": "978-7-00-000000-8",
        "title": "量子物理",
        "author": "吕智国",
        "price": 72,
        "category": "物理",
        "stock_qty": 15,
        "stock_text": "有货",
    },
)


class InventoryBackend(Protocol):
    """库存数据源协议。"""

    def find_by_isbn(self, isbn: str) -> BookStock | None:
        """按归一化后的 ISBN 查询；不存在返回 None。"""


class MockInventoryBackend:
    """内置模拟数据源。"""

    def __init__(self, catalog=DEMO_CATALOG) -> None:
        self._index = {normalize_isbn(item["isbn"]): item for item in catalog}

    def find_by_isbn(self, isbn: str) -> BookStock | None:
        item = self._index.get(normalize_isbn(isbn))
        if item is None:
            return None
        return BookStock(**{**item, "isbn": normalize_isbn(item["isbn"])})

    def all_isbns(self) -> list[str]:
        return list(self._index)


class BookstoreOutOfReach(RuntimeError):
    """无法访问电子书城后端。"""


class HttpInventoryBackend:
    """从电子书城真实后端读取库存。"""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def find_by_isbn(self, isbn: str) -> BookStock | None:
        books = self._fetch_books()
        target = normalize_isbn(isbn)
        for book in books:
            if normalize_isbn(book.get("isbn", "")) == target:
                return BookStock(
                    isbn=target,
                    title=str(book.get("title", "")),
                    author=str(book.get("author", "")),
                    price=int(book.get("price") or 0),
                    category=str(book.get("category", "")),
                    stock_qty=int(book.get("stockQty") or 0),
                    stock_text=str(book.get("stockText") or ""),
                )
        return None

    def _fetch_books(self) -> list[dict]:
        url = f"{self._base_url}/api/v1/books"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise BookstoreOutOfReach(f"访问 {url} 失败：{error}") from error


def build_inventory_backend() -> InventoryBackend:
    """按配置选择数据源。"""
    if TOOLS.bookstore_api_base:
        return HttpInventoryBackend(TOOLS.bookstore_api_base)
    return MockInventoryBackend()
