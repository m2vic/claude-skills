import smtplib
from email.message import EmailMessage


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str):
        self._host, self._port, self._sender = host, port, sender

    def refund_succeeded(self, to: str, refund_id: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self._sender, to, "Your refund was successful"
        message.set_content(f"Refund {refund_id} has been issued.")
        with smtplib.SMTP(self._host, self._port, timeout=10) as client:
            client.send_message(message)
