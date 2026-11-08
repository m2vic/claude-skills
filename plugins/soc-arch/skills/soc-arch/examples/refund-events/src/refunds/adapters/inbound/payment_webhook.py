"""A webhook is an inbound adapter: a third party calls us, and we call a use case.
Signature, vendor event names and status codes all stop here."""
import hashlib
import hmac
import json
from typing import Callable

from refunds.domain.refund import RefundStatus, UnknownRefund

VENDOR_OUTCOMES = {"refund.succeeded": RefundStatus.SUCCEEDED, "refund.failed": RefundStatus.FAILED}


def handle_payment_webhook(raw_body: bytes, signature: str, secret: bytes,
                           record_outcome: Callable[[str, RefundStatus], None]) -> int:
    """Return the status code. Non-2xx asks the provider to retry. Unexpected errors
    propagate, and the server turns them into a 500, which also retries."""
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), signature.encode()):
        return 401
    try:
        payload = json.loads(raw_body)
        event_type = payload["type"]
        refund_id = payload["data"]["refund_id"]
    except (ValueError, KeyError, TypeError):
        return 400
    outcome = VENDOR_OUTCOMES.get(event_type)
    if outcome is None:
        return 200  # an event we do not use: acknowledge it so retries stop
    try:
        record_outcome(refund_id, outcome)
    except UnknownRefund:
        return 409  # may have arrived before our own record: let the provider retry
    return 200
