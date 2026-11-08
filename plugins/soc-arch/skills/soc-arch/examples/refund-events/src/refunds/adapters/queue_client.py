"""One vendor client, shared by the inbound consumer and the outbound publisher."""
import json
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Delivery:
    receipt: str
    attempts: int
    body: object


class HttpQueueClient:
    def __init__(self, base_url: str, timeout: float = 5):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _call(self, method: str, path: str, payload: object = None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self._base_url + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            raw = response.read()
            return (response.status, json.loads(raw)) if raw else (response.status, None)

    def publish(self, body: object) -> None:
        self._call("POST", "/messages", {"body": body})

    def receive(self) -> Optional[Delivery]:
        status, message = self._call("GET", "/messages/next")
        if status == 204:
            return None
        return Delivery(message["receipt"], message["attempts"], message["body"])

    def ack(self, receipt: str) -> None:
        self._call("POST", f"/messages/{receipt}/ack", {})

    def nack(self, receipt: str) -> None:
        self._call("POST", f"/messages/{receipt}/nack", {})

    def dead_letter(self, body: object, reason: str) -> None:
        self._call("POST", "/dead-letter", {"body": body, "reason": reason})
