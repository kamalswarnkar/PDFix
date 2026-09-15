"""Per-IP request throttling.

Three things need it and they all need the same two pieces - work out who the
caller is, then count what they have done recently - so it lives here rather
than being reinvented per endpoint:

  * the feedback and suggestion forms, which send email
  * the tool endpoints, which each occupy a worker for up to a few minutes
  * the admin login, which Django does not rate-limit at all

ponytail: an in-process dict, so each gunicorn worker counts separately and the
counters reset on deploy. That is the right trade at this size; move to the
cache framework (one shared Redis) if you ever run enough workers for the
division to matter.
"""
import threading
import time

from django.conf import settings
from django.http import HttpResponse

_hits = {}
_lock = threading.Lock()
_MAX_TRACKED_KEYS = 10000


def client_ip(request):
    """The address our own proxy saw, not the one the caller asked us to see.

    X-Forwarded-For is appended to by each hop, so the *last* entry is the one
    our reverse proxy wrote and the only one a client cannot forge. Reading the
    first entry - as this used to - let anyone mint a fresh identity per request
    by sending their own header, which bypassed every limit below entirely.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        last_hop = forwarded.split(",")[-1].strip()
        if last_hop:
            return last_hop
    return request.META.get("REMOTE_ADDR", "unknown")


def throttled(request, bucket, limit, window):
    """Record a hit for this caller; True if they are over `limit` in `window`."""
    key = (bucket, client_ip(request))
    now = time.time()

    with _lock:
        if len(_hits) > _MAX_TRACKED_KEYS:
            _hits.clear()
        recent = [t for t in _hits.get(key, []) if now - t < window]
        if len(recent) >= limit:
            _hits[key] = recent
            return True
        recent.append(now)
        _hits[key] = recent
        return False


def reset():
    """Clear every counter. For tests."""
    with _lock:
        _hits.clear()


class AdminLoginThrottleMiddleware:
    """Cap admin sign-in attempts per IP.

    Django ships no brute-force protection, and /admin/ is reachable from the
    internet, so without this a weak superuser password is guessable at wire
    speed. Only the login POST is counted - once you are in, ordinary admin work
    is not throttled.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and self._is_login(request.path):
            if throttled(request, "admin-login", settings.ADMIN_LOGIN_RATE_LIMIT,
                         settings.ADMIN_LOGIN_RATE_WINDOW_SECONDS):
                return HttpResponse(
                    "Too many sign-in attempts. Try again later.",
                    status=429,
                    content_type="text/plain",
                )
        return self.get_response(request)

    @staticmethod
    def _is_login(path):
        root = "/" + settings.ADMIN_URL
        return path in (root, root + "login/")
