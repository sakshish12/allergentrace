"""E-mail through the Brevo HTTP API.

Render's free web services cannot open outgoing SMTP connections, so mails are sent over HTTPS
(https://developers.brevo.com/reference/sendtransacemail). Without BREVO_API_KEY, settings use
Django's console backend instead, which prints mails to the log.
"""

import json
import logging
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

API_URL = "https://api.brevo.com/v3/smtp/email"
log = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            sender_name, sender_email = parseaddr(message.from_email)
            payload = {
                "sender": {"name": sender_name or "AllergenTrace", "email": sender_email},
                "to": [{"email": address} for address in message.to],
                "subject": message.subject,
                "textContent": message.body,
            }
            request = urllib.request.Request(
                API_URL,
                data=json.dumps(payload).encode(),
                headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=10):
                    sent += 1
            except OSError:
                # A failed notification must never break the change that triggered it.
                log.exception("Brevo did not accept the e-mail %r", message.subject)
                if not self.fail_silently:
                    raise
        return sent
