"""A queue consumer is an inbound adapter. Ack, nack, retry limit and dead-lettering stop here."""
import time
from typing import Callable

from refunds.adapters.event_schema import MalformedMessage, decode
from refunds.adapters.queue_client import HttpQueueClient
from refunds.domain.refund import RefundSucceeded

MAX_ATTEMPTS = 5


def consume_one(queue: HttpQueueClient, handle: Callable[[RefundSucceeded], None],
                max_attempts: int = MAX_ATTEMPTS) -> bool:
    delivery = queue.receive()
    if delivery is None:
        return False
    try:
        event = decode(delivery.body)
    except MalformedMessage as error:
        queue.dead_letter(delivery.body, f"malformed: {error}")  # retrying cannot fix it
        queue.ack(delivery.receipt)
        return True
    try:
        handle(event)
    except Exception as error:
        if delivery.attempts >= max_attempts:
            queue.dead_letter(delivery.body, f"gave up after {delivery.attempts} attempts: {error}")
            queue.ack(delivery.receipt)
        else:
            queue.nack(delivery.receipt)
        return True
    queue.ack(delivery.receipt)
    return True


def run_consumer(queue: HttpQueueClient, handle: Callable[[RefundSucceeded], None],
                 poll_seconds: float = 1.0) -> None:
    while True:
        if not consume_one(queue, handle):
            time.sleep(poll_seconds)
