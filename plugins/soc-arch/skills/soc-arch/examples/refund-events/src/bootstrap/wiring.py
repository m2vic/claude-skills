"""The only place that reads config and chooses adapters. Runs three separate processes."""
import os
import sys

from refunds.adapters.inbound.http_server import make_server
from refunds.adapters.inbound.outbox_relay import run_relay
from refunds.adapters.inbound.payment_webhook import handle_payment_webhook
from refunds.adapters.inbound.queue_consumer import run_consumer
from refunds.adapters.outbound.queue_event_publisher import QueueEventPublisher
from refunds.adapters.outbound.smtp_mailer import SmtpMailer
from refunds.adapters.outbound.sqlite_database import SqliteDatabase
from refunds.adapters.queue_client import HttpQueueClient
from refunds.application.notify_customer import notify_customer
from refunds.application.publish_pending_events import publish_pending_events
from refunds.application.record_refund_outcome import record_refund_outcome


def main(command: str) -> None:
    db = SqliteDatabase(os.environ.get("DB_PATH", "refunds.db"))
    if command == "server":
        secret = os.environ["WEBHOOK_SECRET"].encode()
        on_webhook = lambda body, signature: handle_payment_webhook(
            body, signature, secret, lambda refund_id, outcome: record_refund_outcome(db, refund_id, outcome))
        make_server("0.0.0.0", int(os.environ.get("PORT", "8000")), on_webhook).serve_forever()
    queue = HttpQueueClient(os.environ["QUEUE_URL"])
    if command == "relay":
        publisher = QueueEventPublisher(queue)
        run_relay(lambda: publish_pending_events(db, publisher))
    elif command == "consumer":
        mailer = SmtpMailer(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "25")), os.environ["MAIL_FROM"])
        run_consumer(queue, lambda event: notify_customer(db, mailer, event))
    else:
        sys.exit(f"unknown command: {command}")
