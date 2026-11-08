"""The wire format of queue messages, in one place, used by both publisher and consumer."""
from refunds.domain.refund import RefundSucceeded


class MalformedMessage(Exception):
    pass


def encode(event: RefundSucceeded) -> dict:
    return {
        "type": "RefundSucceeded",
        "version": 1,
        "event_id": event.event_id,
        "data": {"refund_id": event.refund_id, "customer_email": event.customer_email},
    }


def decode(body: object) -> RefundSucceeded:
    try:
        if body["type"] != "RefundSucceeded" or body["version"] != 1:
            raise MalformedMessage(f"unsupported message: {body['type']} v{body['version']}")
        return RefundSucceeded(body["event_id"], body["data"]["refund_id"], body["data"]["customer_email"])
    except (KeyError, TypeError) as error:
        raise MalformedMessage(f"missing or invalid field: {error}") from error
