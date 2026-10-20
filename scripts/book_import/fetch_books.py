#!/usr/bin/env python3
"""把一批计算机 / 电子类图书导入书城：核对元数据、下载封面、生成种子 SQL。

数据来源是 Open Library 的公开书目与封面接口：

- 书目：``https://openlibrary.org/api/books?bibkeys=ISBN:<isbn>&format=json&jscmd=data``
- 封面：``https://covers.openlibrary.org/b/isbn/<isbn>-L.jpg``

脚本对每本书做三件事：
1. 用 ISBN 查 Open Library，确认这本书存在，把出版社、出版年、作者等原始信息
   记进 ``sources.json``，便于核对信息不是编的；
2. 下载封面到 ``react-ebook/public/assets/covers/<isbn>.jpg``，校验确实是 JPEG；
3. 把书目拼成 INSERT 语句，写进 ``springboot-ebook/src/main/resources/data.sql``
   的标记块里（重复执行会整块替换，不会叠加），同时把同一段 SQL 打到标准输出，
   方便直接灌进正在运行的数据库。

店内的价格、库存与中文简介是本项目自己的演示数据，不来自 Open Library；
``books.json`` 里的分类与简介由人工整理，脚本只负责核对与落库。

用法：

    # 只核对与下载，不改 data.sql
    python3 scripts/book_import/fetch_books.py --check

    # 下载封面并更新 data.sql
    python3 scripts/book_import/fetch_books.py

    # 把生成的 INSERT 灌进正在运行的库
    python3 scripts/book_import/fetch_books.py --print-sql \\
        | mysql -h127.0.0.1 -P3307 -uroot -proot ebook_backend
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKS_JSON = ROOT / "scripts" / "book_import" / "books.json"
SOURCES_JSON = ROOT / "scripts" / "book_import" / "sources.json"
DATA_SQL = ROOT / "springboot-ebook" / "src" / "main" / "resources" / "data.sql"
COVER_DIR = ROOT / "react-ebook" / "public" / "assets" / "covers"

BEGIN_MARK = "-- BEGIN EXTRA BOOKS"
END_MARK = "-- END EXTRA BOOKS"

OPENLIBRARY_API = "https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
USER_AGENT = "ebook-course-demo/1.0 (book import script)"


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def lookup(isbn: str) -> dict:
    """按 ISBN 取 Open Library 的记录；不存在时返回空字典。"""
    payload = fetch_json(OPENLIBRARY_API.format(isbn=isbn))
    return payload.get(f"ISBN:{isbn}", {})


def download_cover(isbn: str, cover_id: int | None, *, refresh: bool) -> tuple[Path, bytes, str]:
    """下载封面；已存在且是合法 JPEG 时直接复用。

    有些版本的封面按 ISBN 只能拿到很小的缩略图，这时在 books.json 里用
    ``coverId`` 指定 Open Library 的另一张封面图（/b/id/<id>-L.jpg）。
    """
    target = COVER_DIR / f"{isbn}.jpg"
    if target.exists() and not refresh:
        data = target.read_bytes()
        if data.startswith(b"\xff\xd8"):
            return target, data, COVER_URL.format(isbn=isbn)

    url = COVER_URL.format(isbn=isbn)
    if cover_id:
        url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    data = fetch_bytes(url)
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError("封面不是 JPEG 数据")
    if len(data) < 5_000:
        raise RuntimeError(f"封面文件过小（{len(data)} 字节），可能不是真实封面")
    target.write_bytes(data)
    return target, data, url


def stock_fields(quantity: int) -> tuple[str, str]:
    """库存状态与文案：与既有书目的写法保持一致。"""
    if quantity <= 0:
        return "warn", "暂时缺货"
    if quantity <= 5:
        return "warn", "库存紧张"
    return "ok", "有货"


def sql_text(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def book_row(book: dict) -> str:
    stock_type, stock_text = stock_fields(int(book["stock"]))
    fields = [
        sql_text(book["title"]),
        sql_text(book["authors"]),
        str(int(book["price"])),
        sql_text(book["category"]),
        sql_text(book["publisher"]),
        sql_text(book["isbn"]),
        sql_text("纸质书"),
        sql_text(stock_type),
        sql_text(stock_text),
        str(int(book["stock"])),
        sql_text(f"/assets/covers/{book['isbn']}.jpg"),
        sql_text(book["summary"]),
    ]
    return "(" + ", ".join(fields) + ")"


def build_sql(books: list[dict]) -> str:
    columns = (
        "INSERT IGNORE INTO books "
        "(title, author, price, category, publisher, isbn, format, stock_type, stock_text, "
        "stock_qty, cover_url, description) VALUES"
    )
    rows = ",\n".join(book_row(book) for book in books)
    header = (
        f"{BEGIN_MARK}\n"
        "-- 计算机 / 电子类扩充书目：由 scripts/book_import/fetch_books.py 生成，请勿手改。\n"
        "-- 元数据经 Open Library 按 ISBN 核对；价格、库存与中文简介是课程演示数据。\n"
    )
    return f"{header}{columns}\n{rows};\n{END_MARK}\n"


def update_data_sql(block: str) -> None:
    """把标记块写进 data.sql；已有标记时整块替换。"""
    original = DATA_SQL.read_text(encoding="utf-8")
    if BEGIN_MARK in original and END_MARK in original:
        start = original.index(BEGIN_MARK)
        end = original.index(END_MARK) + len(END_MARK)
        updated = original[:start].rstrip() + "\n\n" + block + original[end:].lstrip("\n")
    else:
        updated = original.rstrip() + "\n\n" + block
    DATA_SQL.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只核对书目与封面，不写 SQL")
    parser.add_argument("--refresh", action="store_true", help="重新下载已有封面")
    parser.add_argument("--print-sql", action="store_true", help="把 INSERT 语句打到标准输出")
    args = parser.parse_args()

    books = json.loads(BOOKS_JSON.read_text(encoding="utf-8"))
    COVER_DIR.mkdir(parents=True, exist_ok=True)

    sources = []
    failures = []
    prepared = []

    for index, book in enumerate(books, start=1):
        isbn = book["isbn"]
        print(f"[{index:02d}/{len(books)}] {isbn} {book['title']}", end=" ... ", flush=True)
        try:
            record = lookup(isbn)
            if not record:
                raise RuntimeError("Open Library 没有该 ISBN 的记录")
            cover_path, cover_bytes, cover_source = download_cover(
                isbn, book.get("coverId"), refresh=args.refresh
            )
        except (urllib.error.URLError, RuntimeError, TimeoutError) as error:
            print(f"失败：{error}")
            failures.append({"isbn": isbn, "title": book["title"], "error": str(error)})
            continue

        prepared.append(book)
        sources.append(
            {
                "isbn": isbn,
                "title": book["title"],
                "openLibraryTitle": record.get("title"),
                "openLibraryUrl": record.get("url"),
                "openLibraryAuthors": [author.get("name") for author in record.get("authors", [])],
                "publisher": (record.get("publishers") or [{}])[0].get("name"),
                "publishDate": record.get("publish_date"),
                "coverUrl": cover_source,
                "coverFile": str(cover_path.relative_to(ROOT)),
                "coverSha256": hashlib.sha256(cover_bytes).hexdigest(),
            }
        )
        print("ok")
        time.sleep(0.2)  # 对公开接口客气一点

    SOURCES_JSON.write_text(
        json.dumps(
            {"source": "Open Library", "api": OPENLIBRARY_API, "books": sources, "failures": failures},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if failures:
        print(f"有 {len(failures)} 本没有导入成功，详见 {SOURCES_JSON.relative_to(ROOT)}")
    if not prepared:
        return 1

    block = build_sql(prepared)
    if args.print_sql:
        sys.stdout.write(block)
    if not args.check:
        update_data_sql(block)
        print(f"已更新 {DATA_SQL.relative_to(ROOT)}（{len(prepared)} 本）")

    print(f"完成：{len(prepared)} 本，封面目录 {COVER_DIR.relative_to(ROOT)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
