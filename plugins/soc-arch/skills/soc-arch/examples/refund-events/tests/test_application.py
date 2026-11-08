import unittest

from fakes import FakeMailer, InMemoryDatabase
from refunds.application.notify_customer import notify_customer
from refunds.application.publish_pending_events import publish_pending_events
from refunds.application.record_refund_outcome import record_refund_outcome
from refunds.domain.refund import Refund, RefundStatus as S, RefundSucceeded, UnknownRefund

EVENT = RefundSucceeded("e1", "r1", "a@b.c")


class FlakyPublisher:
    def __init__(self):
        self.published, self.down = [], False

    def publish(self, event):
        if self.down:
            raise ConnectionError("queue down")
        self.published.append(event)


class RecordOutcome(unittest.TestCase):
    def setUp(self):
        self.db = InMemoryDatabase()
        self.db.save_refund(Refund("r1", "a@b.c"))

    def test_duplicate_success_adds_one_outbox_event(self):
        record_refund_outcome(self.db, "r1", S.SUCCEEDED)
        record_refund_outcome(self.db, "r1", S.SUCCEEDED)
        self.assertEqual(len(self.db.pending_events(10)), 1)

    def test_late_failure_does_not_undo_success(self):
        record_refund_outcome(self.db, "r1", S.SUCCEEDED)
        record_refund_outcome(self.db, "r1", S.FAILED)
        self.assertEqual(self.db.get_refund("r1").status, S.SUCCEEDED)

    def test_unknown_refund_raises(self):
        with self.assertRaises(UnknownRefund):
            record_refund_outcome(self.db, "nope", S.SUCCEEDED)


class Relay(unittest.TestCase):
    def test_queue_outage_keeps_events_until_it_returns(self):
        db, publisher = InMemoryDatabase(), FlakyPublisher()
        db.add_to_outbox(EVENT)
        publisher.down = True
        with self.assertRaises(ConnectionError):
            publish_pending_events(db, publisher)
        self.assertEqual(db.pending_events(10), [EVENT])
        publisher.down = False
        publish_pending_events(db, publisher)
        self.assertEqual((publisher.published, db.pending_events(10)), ([EVENT], []))


class Notify(unittest.TestCase):
    def test_duplicate_message_sends_one_email(self):
        db, mailer = InMemoryDatabase(), FakeMailer()
        notify_customer(db, mailer, EVENT)
        notify_customer(db, mailer, EVENT)
        self.assertEqual(mailer.sent, [("a@b.c", "r1")])

    def test_failed_send_is_not_marked_handled(self):
        db, mailer = InMemoryDatabase(), FakeMailer()
        mailer.failures_left = 1
        with self.assertRaises(ConnectionError):
            notify_customer(db, mailer, EVENT)
        notify_customer(db, mailer, EVENT)
        self.assertEqual(len(mailer.sent), 1)
