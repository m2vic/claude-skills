from refunds.application.ports import Database
from refunds.domain.refund import RefundStatus, UnknownRefund


def record_refund_outcome(db: Database, refund_id: str, outcome: RefundStatus) -> None:
    """The state change and its outgoing event commit together, or not at all."""
    with db.transaction() as tx:
        refund = tx.get_refund(refund_id)
        if refund is None:
            raise UnknownRefund(refund_id)
        updated, events = refund.apply_outcome(outcome)
        if updated != refund:
            tx.save_refund(updated)
        for event in events:
            tx.add_to_outbox(event)
