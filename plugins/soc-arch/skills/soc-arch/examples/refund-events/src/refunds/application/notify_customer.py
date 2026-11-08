from refunds.application.ports import CustomerMailer, Database
from refunds.domain.refund import RefundSucceeded


def notify_customer(db: Database, mailer: CustomerMailer, event: RefundSucceeded) -> None:
    """Takes a business event, with no receipts, acks or JSON. Duplicates are skipped."""
    key = f"notify-customer:{event.event_id}"
    with db.transaction() as tx:
        if tx.was_handled(key):
            return
    mailer.refund_succeeded(event.customer_email, event.refund_id)
    with db.transaction() as tx:
        tx.mark_handled(key)
