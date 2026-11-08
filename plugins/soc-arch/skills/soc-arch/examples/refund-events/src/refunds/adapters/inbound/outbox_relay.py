"""A timer is an inbound adapter too. This loop triggers the relay use case."""
import time
from typing import Callable


def run_relay(publish_pending: Callable[[], int], poll_seconds: float = 1.0) -> None:
    while True:
        try:
            published = publish_pending()
        except OSError:  # queue unreachable: events stay in the outbox until it returns
            published = 0
        if not published:
            time.sleep(poll_seconds)
