import hashlib
import hmac
import json
import unittest

from fakes import FakeQueue
from refunds.adapters.event_schema import encode
from refunds.adapters.inbound.payment_webhook import handle_payment_webhook
from refunds.adapters.inbound.queue_consumer import consume_one
from refunds.domain.refund import RefundStatus as S, RefundSucceeded, UnknownRefund

SECRET = b"secret"
EVENT = RefundSucceeded("e1", "r1", "a@b.c")


def signed(payload):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return raw, hmac.new(SECRET, raw, hashlib.sha256).hexdigest()


class Webhook(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def post(self, raw, signature, record=None):
        return handle_payment_webhook(raw, signature, SECRET, record or (lambda r, o: self.calls.append((r, o))))

    def test_valid_event_calls_use_case_with_domain_outcome(self):
        raw, sig = signed({"type": "refund.succeeded", "data": {"refund_id": "r1"}})
        self.assertEqual(self.post(raw, sig), 200)
        self.assertEqual(self.calls, [("r1", S.SUCCEEDED)])

    def test_bad_signature_is_rejected_before_parsing(self):
        self.assertEqual(self.post(b"not json", "wrong"), 401)
        self.assertEqual(self.calls, [])

    def test_non_ascii_signature_is_rejected_cleanly(self):
        self.assertEqual(self.post(b"{}", "café"), 401)

    def test_malformed_body_with_valid_signature_is_400(self):
        raw, sig = signed(b"[]")
        self.assertEqual(self.post(raw, sig), 400)

    def test_unused_event_type_is_acknowledged(self):
        raw, sig = signed({"type": "charge.created", "data": {"refund_id": "r1"}})
        self.assertEqual(self.post(raw, sig), 200)
        self.assertEqual(self.calls, [])

    def test_unknown_refund_asks_provider_to_retry(self):
        def record(refund_id, outcome):
            raise UnknownRefund(refund_id)
        raw, sig = signed({"type": "refund.succeeded", "data": {"refund_id": "r1"}})
        self.assertEqual(self.post(raw, sig, record), 409)

    def test_unexpected_error_propagates_so_server_returns_500(self):
        def record(refund_id, outcome):
            raise ConnectionError("database down")
        raw, sig = signed({"type": "refund.succeeded", "data": {"refund_id": "r1"}})
        with self.assertRaises(ConnectionError):
            self.post(raw, sig, record)


class Consumer(unittest.TestCase):
    def setUp(self):
        self.queue = FakeQueue()

    def test_empty_queue_returns_false(self):
        self.assertFalse(consume_one(self.queue, lambda e: None))

    def test_success_decodes_and_acks(self):
        handled = []
        self.queue.publish(encode(EVENT))
        self.assertTrue(consume_one(self.queue, handled.append))
        self.assertEqual((handled, self.queue.in_flight, self.queue.ready), ([EVENT], {}, []))

    def test_malformed_message_goes_straight_to_dead_letter(self):
        self.queue.publish({"nonsense": True})
        consume_one(self.queue, lambda e: self.fail("must not be handled"))
        self.assertEqual((len(self.queue.dead), self.queue.ready, self.queue.in_flight), (1, [], {}))

    def test_future_version_goes_to_dead_letter(self):
        self.queue.publish({**encode(EVENT), "version": 2})
        consume_one(self.queue, lambda e: self.fail("must not be handled"))
        self.assertEqual(len(self.queue.dead), 1)

    def test_failure_is_retried_until_limit_then_dead_lettered(self):
        def always_fails(event):
            raise ConnectionError("smtp down")
        self.queue.publish(encode(EVENT))
        for _ in range(4):
            consume_one(self.queue, always_fails)
            self.assertEqual((len(self.queue.ready), self.queue.dead), (1, []))
        consume_one(self.queue, always_fails)
        self.assertEqual((self.queue.ready, self.queue.in_flight, len(self.queue.dead)), ([], {}, 1))
