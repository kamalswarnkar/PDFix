"""Gmail API email backend.

Sends over HTTPS (gmail.googleapis.com) rather than SMTP, because several PaaS
providers - Render's free and starter tiers among them - block outbound ports
587 and 465 outright, so an SMTP send simply hangs until it times out.

ponytail: stdlib urllib rather than google-api-python-client. That package pulls
in google-auth, googleapis-common-protos, protobuf and friends to do one token
refresh and one POST. Swap to it if you ever need more of the Gmail API than
"send this message".
"""
import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
# Minimum scope that can send mail. It cannot read or delete anything.
SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailAPIError(Exception):
    """A Gmail API call failed. The message carries Google's own explanation."""


class GmailAPIBackend(BaseEmailBackend):
    """Django email backend that posts messages through the Gmail API."""

    # Access tokens last about an hour, so cache one across sends and across
    # threads instead of paying a token round-trip per email.
    _token = None
    _token_expires_at = 0.0
    _token_lock = threading.Lock()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            token = self._access_token()
        except Exception as exc:
            logger.error("Gmail API: could not obtain an access token: %s", exc)
            if not self.fail_silently:
                raise
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send(message, token)
                sent += 1
            except Exception as exc:
                logger.error("Gmail API: send failed: %s", exc)
                if not self.fail_silently:
                    raise
        return sent

    @classmethod
    def _access_token(cls):
        """Exchange the long-lived refresh token for a short-lived access token."""
        with cls._token_lock:
            if cls._token and time.monotonic() < cls._token_expires_at:
                return cls._token

            for name in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
                if not getattr(settings, name, ""):
                    raise GmailAPIError(f"{name} is not set - run: manage.py gmail_auth")

            payload = urllib.parse.urlencode({
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            }).encode()

            data = _post(TOKEN_URL, payload, {"Content-Type": "application/x-www-form-urlencoded"})

            cls._token = data["access_token"]
            # Renew a minute early so a send never races the expiry.
            cls._token_expires_at = time.monotonic() + max(int(data.get("expires_in", 3600)) - 60, 0)
            return cls._token

    def _send(self, message, token):
        # Gmail wants the whole RFC 2822 message, base64url-encoded.
        raw = base64.urlsafe_b64encode(message.message().as_bytes()).decode("ascii")
        _post(
            SEND_URL,
            json.dumps({"raw": raw}).encode(),
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        logger.info("Gmail API: sent %r to %s", message.subject, ", ".join(message.to))


def _post(url, data, headers):
    """POST and decode JSON, turning Google's error bodies into readable messages."""
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    timeout = getattr(settings, "EMAIL_TIMEOUT", 15) or 15
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        # Google's body says exactly what is wrong ("invalid_grant",
        # "Gmail API has not been used in project ...", etc). Surface it.
        detail = exc.read()[:600].decode("utf-8", errors="replace")
        raise GmailAPIError(f"HTTP {exc.code} from {url}: {detail}") from None
    except urllib.error.URLError as exc:
        raise GmailAPIError(f"could not reach {url}: {exc.reason}") from None
