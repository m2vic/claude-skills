"""Fakes and real adapters must behave alike, so one suite runs against both."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fakes import FakeQueue, InMemoryDatabase
from refunds.adapters.outbound.sqlite_database import SqliteDatabase
from refunds.adapters.queue_client import HttpQueueClient
from refunds.domain.refund import Refund, RefundStatus as S, RefundSucceeded

EVENT = RefundSucceeded("e1", "r1", "a@b.c")


class DatabaseContract:
    def test_saved_refund_reads_back(self):
        with self.db.transaction() as tx:
            tx.save_refund(Refund("r1", "a@b.c", S.FAILED))
        with self.db.transaction() as tx:
            self.assertEqual(tx.get_refund("r1"), Refund("r1", "a@b.c", S.FAILED))
            self.assertIsNone(tx.get_refund("nope"))

    def test_error_rolls_back_refund_and_outbox_together(self):
        with self.assertRaises(ValueError):
            with self.db.transaction() as tx:
                tx.save_refund(Refund("r1", "a@b.c"))
                tx.add_to_outbox(EVENT)
                raise ValueError
        with self.db.transaction() as tx:
            self.assertIsNone(tx.get_refund("r1"))
        self.assertEqual(self.db.pending_events(10), [])

    def test_outbox_keeps_event_until_published_and_ignores_duplicates(self):
        with self.db.transaction() as tx:
            tx.add_to_outbox(EVENT)
            tx.add_to_outbox(EVENT)
        self.assertEqual(self.db.pending_events(10), [EVENT])
        self.db.mark_published("e1")
        self.assertEqual(self.db.pending_events(10), [])

    def test_handled_keys_are_remembered(self):
        with self.db.transaction() as tx:
            self.assertFalse(tx.was_handled("k"))
            tx.mark_handled("k")
        with self.db.transaction() as tx:
            self.assertTrue(tx.was_handled("k"))


class InMemoryDatabaseContract(DatabaseContract, unittest.TestCase):
    def setUp(self):
        self.db = InMemoryDatabase()


class SqliteDatabaseContract(DatabaseContract, unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = SqliteDatabase(os.path.join(folder.name, "test.db"))


class QueueContract:
    def test_message_redelivers_after_nack_with_higher_attempts(self):
        self.queue.publish({"n": 1})
        first = self.queue.receive()
        self.assertEqual((first.attempts, first.body), (1, {"n": 1}))
        self.queue.nack(first.receipt)
        self.assertEqual(self.queue.receive().attempts, 2)

    def test_ack_removes_message(self):
        self.queue.publish({"n": 1})
        self.queue.ack(self.queue.receive().receipt)
        self.assertIsNone(self.queue.receive())


class FakeQueueContract(QueueContract, unittest.TestCase):
    def setUp(self):
        self.queue = FakeQueue()


class HttpQueueClientContract(QueueContract, unittest.TestCase):
    """Runs the real client against a local stub of the queue's HTTP API."""

    def setUp(self):
        backing = FakeQueue()

        class Stub(BaseHTTPRequestHandler):
            def _reply(self, status, payload=None):
                data = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                delivery = backing.receive()
                if delivery is None:
                    return self._reply(204)
                self._reply(200, {"receipt": delivery.receipt, "attempts": delivery.attempts, "body": delivery.body})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                parts = self.path.strip("/").split("/")
                if parts == ["messages"]:
                    backing.publish(body["body"])
                elif parts[-1] == "ack":
                    backing.ack(parts[1])
                elif parts[-1] == "nack":
                    backing.nack(parts[1])
                self._reply(200, {})

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.queue = HttpQueueClient(f"http://127.0.0.1:{server.server_port}")
