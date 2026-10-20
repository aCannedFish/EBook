"""保存按书城用户隔离的客服会话与执行事件。

SQLite 只保存问题、回复和工具观测，不保存 JWT 或模型密钥。每次消息更新与
对应事件在同一事务内提交：页面重连时先读取快照，再从快照游标继续订阅，
因此切页、刷新或网络中断不会丢失已经产生的步骤。
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
import uuid


class SessionNotFound(LookupError):
    """会话不存在或属于另一位用户；对外使用相同的 404。"""


class SessionBusy(RuntimeError):
    """同一会话已有回复在生成，防止上下文顺序交错。"""


def timestamp() -> str:
    """以统一 UTC 时间保存排序字段，前端再按用户时区显示。"""
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    """以短事务维护会话快照和可重放事件。

    进程内只保留一个连接，并用可重入锁串行化访问：SQLite 的连接不适合跨线程
    并发使用，而且每次操作都开/关连接会在 WAL 模式下产生大量锁竞争。
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.executescript("""
                CREATE TABLE IF NOT EXISTS assistant_sessions (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS assistant_sessions_owner
                    ON assistant_sessions(owner_id, updated_at);
                CREATE TABLE IF NOT EXISTS assistant_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES assistant_sessions(id),
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS assistant_messages_session
                    ON assistant_messages(session_id, id);
                CREATE UNIQUE INDEX IF NOT EXISTS assistant_one_running_turn
                    ON assistant_messages(session_id) WHERE status = 'running';
                CREATE TABLE IF NOT EXISTS assistant_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES assistant_sessions(id),
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS assistant_events_session
                    ON assistant_events(session_id, id);
            """)
        self._recover_interrupted()

    @contextmanager
    def _connect(self):
        """同一时刻只允许一个线程使用连接；事务由 ``with`` 自动提交或回滚。"""
        with self._lock:
            with self._connection:
                yield self._connection

    @staticmethod
    def _owned(connection, owner_id: str, session_id: str):
        row = connection.execute(
            "SELECT * FROM assistant_sessions WHERE id = ? AND owner_id = ?",
            (session_id, owner_id),
        ).fetchone()
        if row is None:
            raise SessionNotFound(session_id)
        return row

    @staticmethod
    def _summary(row) -> dict:
        return {
            "id": row["id"], "title": row["title"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        }

    def list_sessions(self, owner_id: str) -> list[dict]:
        """列表仅查询当前用户，会话标题使用首条问题，最近活跃会话排在前面。"""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM assistant_sessions WHERE owner_id = ? ORDER BY updated_at DESC, id",
                (owner_id,),
            ).fetchall()
        return [self._summary(row) for row in rows]

    def create(self, owner_id: str) -> dict:
        session_id, now = uuid.uuid4().hex, timestamp()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO assistant_sessions VALUES (?, ?, ?, ?, ?)",
                (session_id, owner_id, "新会话", now, now),
            )
        return self.get(owner_id, session_id)

    def get(self, owner_id: str, session_id: str) -> dict:
        """在同一读事务内读取消息及事件游标，保证快照与后续订阅之间没有空隙。"""
        with self._connect() as connection:
            connection.execute("BEGIN")
            row = self._owned(connection, owner_id, session_id)
            messages = connection.execute(
                "SELECT payload FROM assistant_messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            cursor = connection.execute(
                "SELECT COALESCE(MAX(id), 0) FROM assistant_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        return {
            **self._summary(row), "cursor": cursor,
            "messages": [json.loads(message["payload"]) for message in messages],
        }

    @staticmethod
    def _history(messages: list[dict]) -> list[dict]:
        """仅把已完成的问答对带给模型，失败或中断的半轮仍保留在页面中。"""
        history = []
        question = None
        for message in messages:
            if message["role"] == "user":
                question = message
            elif question and message["status"] == "completed":
                history.extend([
                    {"role": "user", "content": question["content"]},
                    {"role": "assistant", "content": message["content"]},
                ])
                question = None
        return history[-12:]

    def start_turn(self, owner_id: str, session_id: str, question: str) -> tuple[int, list[dict]]:
        """原子地预留一轮问答；并发发送只允许一方成功，另一方得到冲突响应。"""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._owned(connection, owner_id, session_id)
            rows = connection.execute(
                "SELECT payload, status FROM assistant_messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            if any(row["status"] == "running" for row in rows):
                raise SessionBusy("当前会话正在回复，请等待完成后继续提问")
            history = self._history([json.loads(row["payload"]) for row in rows])
            if not rows:
                title = question[:28] + ("…" if len(question) > 28 else "")
                connection.execute("UPDATE assistant_sessions SET title = ? WHERE id = ?", (title, session_id))
            self._insert_message(connection, session_id, {
                "role": "user", "content": question, "status": "completed", "createdAt": timestamp(),
            })
            message_id = self._insert_message(connection, session_id, {
                "role": "assistant", "content": "", "status": "running", "phase": "preparing",
                "steps": [], "createdAt": timestamp(), "requestId": uuid.uuid4().hex[:12],
            })
            self._publish(connection, session_id, {"id": message_id, "status": "running"})
        return message_id, history

    @staticmethod
    def _insert_message(connection, session_id: str, message: dict) -> int:
        cursor = connection.execute(
            "INSERT INTO assistant_messages(session_id, role, status, payload) VALUES (?, ?, ?, '{}')",
            (session_id, message["role"], message["status"]),
        )
        message_id = cursor.lastrowid
        connection.execute(
            "UPDATE assistant_messages SET payload = ? WHERE id = ?",
            (json.dumps({**message, "id": message_id}, ensure_ascii=False), message_id),
        )
        return message_id

    @staticmethod
    def _publish(connection, session_id: str, patch: dict) -> None:
        now = timestamp()
        connection.execute("UPDATE assistant_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        connection.execute(
            "INSERT INTO assistant_events(session_id, payload) VALUES (?, ?)",
            (session_id, json.dumps({"sessionId": session_id, "updatedAt": now, "message": patch}, ensure_ascii=False)),
        )

    def update_message(self, session_id: str, message_id: int, patch: dict) -> None:
        """后台任务内部更新；快照保存完整消息，事件只携带变化字段。"""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload FROM assistant_messages WHERE id = ? AND session_id = ?",
                (message_id, session_id),
            ).fetchone()
            message = {**json.loads(row["payload"]), **patch}
            connection.execute(
                "UPDATE assistant_messages SET status = ?, payload = ? WHERE id = ?",
                (message["status"], json.dumps(message, ensure_ascii=False), message_id),
            )
            self._publish(connection, session_id, {**patch, "id": message_id})

    def events_after(self, session_id: str, cursor: int) -> list[dict]:
        """调用方先验证会话所有权；按递增游标重放，不遗漏短时间内连续产生的步骤。"""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, payload FROM assistant_events WHERE session_id = ? AND id > ? ORDER BY id LIMIT 100",
                (session_id, cursor),
            ).fetchall()
        return [{"id": row["id"], "data": json.loads(row["payload"])} for row in rows]

    def is_running(self, session_id: str) -> bool:
        """订阅连接只检查任务状态，不反复加载整个会话。"""
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM assistant_messages WHERE session_id = ? AND status = 'running' LIMIT 1",
                (session_id,),
            ).fetchone() is not None

    def _recover_interrupted(self) -> None:
        """重启后结束遗留的生成状态，保留已有步骤，并允许用户继续这个会话。"""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, session_id, payload FROM assistant_messages WHERE status = 'running'",
            ).fetchall()
        for row in rows:
            message = json.loads(row["payload"])
            steps = [dict(step, status="interrupted") if step.get("status") == "running" else step
                     for step in message["steps"]]
            self.update_message(row["session_id"], row["id"], {
                "status": "interrupted", "phase": "finished", "steps": steps,
                "content": "服务已重启，本次回复未完成。已完成的查询记录保留，可以继续提问。",
                "stoppedReason": "interrupted",
            })
