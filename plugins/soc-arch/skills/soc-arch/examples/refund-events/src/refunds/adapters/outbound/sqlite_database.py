import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

from refunds.adapters.event_schema import decode, encode
from refunds.domain.refund import Refund, RefundStatus, RefundSucceeded

SCHEMA = """
CREATE TABLE IF NOT EXISTS refunds (id TEXT PRIMARY KEY, customer_email TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (event_id TEXT PRIMARY KEY, body TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS handled (key TEXT PRIMARY KEY);
"""


class _SqliteTransaction:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_refund(self, refund_id: str) -> Optional[Refund]:
        row = self._connection.execute(
            "SELECT id, customer_email, status FROM refunds WHERE id=?", (refund_id,)).fetchone()
        return Refund(row[0], row[1], RefundStatus(row[2])) if row else None

    def save_refund(self, refund: Refund) -> None:
        self._connection.execute(
            "INSERT INTO refunds (id, customer_email, status) VALUES (?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status",
            (refund.id, refund.customer_email, refund.status.value))

    def add_to_outbox(self, event: RefundSucceeded) -> None:
        self._connection.execute("INSERT OR IGNORE INTO outbox (event_id, body) VALUES (?,?)",
                                 (event.event_id, json.dumps(encode(event))))

    def was_handled(self, key: str) -> bool:
        return self._connection.execute("SELECT 1 FROM handled WHERE key=?", (key,)).fetchone() is not None

    def mark_handled(self, key: str) -> None:
        self._connection.execute("INSERT OR IGNORE INTO handled (key) VALUES (?)", (key,))


class SqliteDatabase:
    def __init__(self, path: str):
        self._path = path
        connection = self._connect()
        connection.executescript(SCHEMA)
        connection.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=10, isolation_level=None)

    @contextmanager
    def transaction(self) -> Iterator[_SqliteTransaction]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield _SqliteTransaction(connection)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def pending_events(self, limit: int) -> list[RefundSucceeded]:
        with self.transaction() as tx:
            rows = tx._connection.execute(
                "SELECT body FROM outbox WHERE published=0 ORDER BY rowid LIMIT ?", (limit,)).fetchall()
        return [decode(json.loads(row[0])) for row in rows]

    def mark_published(self, event_id: str) -> None:
        with self.transaction() as tx:
            tx._connection.execute("UPDATE outbox SET published=1 WHERE event_id=?", (event_id,))
