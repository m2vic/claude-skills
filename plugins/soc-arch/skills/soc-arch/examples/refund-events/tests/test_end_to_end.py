"""Webhook to outbox to queue to email, with real SQLite and a fake queue and mailer."""
import hashlib
import hmac
import json
import os
import tempfile
import unittest

from fakes import FakeMailer, FakeQueue
from refunds.adapters.inbound.payment_webhook import handle_payment_webhook
from refunds.adapters.inbound.queue_consumer import consume_one
from refunds.adapters.outbound.queue_event_publisher import QueueEventPublisher
from refunds.adapters.outbound.sqlite_database import SqliteDatabase
from refunds.application.notify_customer import notify_customer
from refunds.application.publish_pending_events import publish_pending_events
from refunds.application.record_refund_outcome import record_refund_outcome
from refunds.domain.refund import Refund

SECRET = b"secret"


class Flow(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.db = SqliteDatabase(os.path.join(folder.name, "e2e.db"))
        with self.db.transaction() as tx:
            tx.save_refund(Refund("r1", "a@b.c"))
        self.queue, self.mailer = FakeQueue(), FakeMailer()

    def webhook(self, event_type):
        raw = json.dumps({"type": event_type, "data": {"refund_id": "r1"}}).encode()
        signature = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
        return handle_payment_webhook(raw, signature, SECRET,
                                      lambda r, o: record_refund_outcome(self.db, r, o))

    def relay(self):
        return publish_pending_events(self.db, QueueEventPublisher(self.queue))

    def consume(self):
        return consume_one(self.queue, lambda e: notify_customer(self.db, self.mailer, e))

    def test_out_of_order_duplicate_webhooks_and_redelivery_send_one_email(self):
        self.assertEqual(self.webhook("refund.failed"), 200)
        self.assertEqual(self.webhook("refund.succeeded"), 200)
        self.assertEqual(self.webhook("refund.succeeded"), 200)
        self.assertEqual(self.webhook("refund.failed"), 200)
        self.assertEqual(self.relay(), 1)
        message = self.queue.ready[0]
        self.queue.publish(message.body)  # the queue delivers it a second time
        while self.consume():
            pass
        self.assertEqual(self.mailer.sent, [("a@b.c", "r1")])

    def test_webhook_succeeds_while_queue_is_down(self):
        self.assertEqual(self.webhook("refund.succeeded"), 200)  # nothing touches the queue yet
        self.assertEqual(self.queue.ready, [])
        self.assertEqual(self.relay(), 1)
        self.assertEqual(self.relay(), 0)
        self.assertEqual(len(self.queue.ready), 1)

    def test_email_retries_after_smtp_failure(self):
        self.webhook("refund.succeeded")
        self.relay()
        self.mailer.failures_left = 2
        while self.consume():
            pass
        self.assertEqual(len(self.mailer.sent), 1)
