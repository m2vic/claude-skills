"""Business rules only. Nothing here knows about webhooks, queues or SQL."""
from dataclasses import dataclass, replace
from enum import Enum


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class UnknownRefund(Exception):
    pass


@dataclass(frozen=True)
class RefundSucceeded:
    """A business fact. The JSON shape on the queue lives in adapters/event_schema.py."""
    event_id: str
    refund_id: str
    customer_email: str


@dataclass(frozen=True)
class Refund:
    id: str
    customer_email: str
    status: RefundStatus = RefundStatus.PENDING

    def apply_outcome(self, outcome: RefundStatus) -> tuple["Refund", list[RefundSucceeded]]:
        """Duplicates and out-of-order outcomes are absorbed here, as business rules."""
        if self.status is RefundStatus.SUCCEEDED or outcome is self.status:
            return self, []
        updated = replace(self, status=outcome)
        if outcome is RefundStatus.SUCCEEDED:
            return updated, [RefundSucceeded(f"refund-succeeded:{self.id}", self.id, self.customer_email)]
        return updated, []
