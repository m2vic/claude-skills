from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

from refunds.adapters.queue_client import Delivery


class InMemoryDatabase:
    """Rolls back when the transaction body raises, like the real database."""

    def __init__(self):
        self.state = {"refunds": {}, "outbox": {}, "published": set(), "handled": set()}

    @contextmanager
    def transaction(self):
        before = deepcopy(self.state)
        try:
            yield self
        except BaseException:
            self.state = before
            raise

    def get_refund(self, refund_id):
        return self.state["refunds"].get(refund_id)

    def save_refund(self, refund):
        self.state["refunds"][refund.id] = refund

    def add_to_outbox(self, event):
        self.state["outbox"].setdefault(event.event_id, event)

    def was_handled(self, key):
        return key in self.state["handled"]

    def mark_handled(self, key):
        self.state["handled"].add(key)

    def pending_events(self, limit):
        events = [e for i, e in self.state["outbox"].items() if i not in self.state["published"]]
        return events[:limit]

    def mark_published(self, event_id):
        self.state["published"].add(event_id)


class FakeQueue:
    def __init__(self):
        self.ready, self.in_flight, self.dead, self._next_receipt = [], {}, [], 0

    def publish(self, body):
        self.ready.append(Delivery("", 0, body))

    def receive(self):
        if not self.ready:
            return None
        self._next_receipt += 1
        message = self.ready.pop(0)
        delivery = replace(message, receipt=str(self._next_receipt), attempts=message.attempts + 1)
        self.in_flight[delivery.receipt] = delivery
        return delivery

    def ack(self, receipt):
        del self.in_flight[receipt]

    def nack(self, receipt):
        self.ready.append(self.in_flight.pop(receipt))

    def dead_letter(self, body, reason):
        self.dead.append((body, reason))


class FakeMailer:
    def __init__(self):
        self.sent, self.failures_left = [], 0

    def refund_succeeded(self, to, refund_id):
        if self.failures_left:
            self.failures_left -= 1
            raise ConnectionError("smtp down")
        self.sent.append((to, refund_id))
