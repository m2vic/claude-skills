from refunds.adapters.event_schema import encode
from refunds.adapters.queue_client import HttpQueueClient
from refunds.domain.refund import RefundSucceeded


class QueueEventPublisher:
    def __init__(self, queue: HttpQueueClient):
        self._queue = queue

    def publish(self, event: RefundSucceeded) -> None:
        self._queue.publish(encode(event))
