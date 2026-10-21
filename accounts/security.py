"""Protection of the login: rate limit per IP, progressive delay and lockout per account.

State lives in Django's cache, which is a database table in production, so every Gunicorn
worker sees the same counters and they survive a restart of the free instance.

shortcut: get/set on the cache is not atomic, so two parallel requests can both pass a limit
by one; acceptable for a login, switch the cache to Redis with atomic INCR if that matters.
"""

import hashlib
import logging
import time
from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpResponse
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

log = logging.getLogger("accounts.security")

RATE_LIMIT = 10  # requests per IP and minute
RATE_WINDOW = 60
MAX_FAILURES = 5  # consecutive failed logins before the account is locked
LOCK_SECONDS = 15 * 60
MAX_DELAY = 8  # seconds; the delay doubles with every failure: 1, 2, 4, 8


def client_ip(request):
    # Render's edge overwrites True-Client-IP with the real address; X-Forwarded-For can be spoofed.
    return request.META.get("HTTP_TRUE_CLIENT_IP") or request.META.get("REMOTE_ADDR", "")


def rate_limit(scope, methods=("GET", "POST")):
    """View decorator: at most RATE_LIMIT requests per IP and minute for this scope (HTTP 429)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                key = f"rate:{scope}:{client_ip(request)}"
                cache.add(key, 0, RATE_WINDOW)
                if cache.incr(key) > RATE_LIMIT:
                    log.warning("rate limit hit scope=%s ip=%s", scope, client_ip(request))
                    return HttpResponse(
                        "Too many requests. Please wait a minute and try again.",
                        status=429,
                        content_type="text/plain; charset=utf-8",
                        headers={"Retry-After": str(RATE_WINDOW)},
                    )
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def _key(email):
    # The e-mail itself is not stored as a cache key.
    return "login-fail:" + hashlib.sha256(email.encode()).hexdigest()


def login_blocked(email):
    """True while the account is locked or its progressive delay has not passed yet."""
    state = cache.get(_key(email))
    return bool(state) and time.time() < max(state["locked_until"], state["retry_at"])


def record_failure(email, request):
    """Count a failed login; lock the account and notify its owner after MAX_FAILURES."""
    state = cache.get(_key(email)) or {"count": 0, "locked_until": 0, "retry_at": 0}
    state["count"] += 1
    now = time.time()
    if state["count"] >= MAX_FAILURES:
        state.update(count=0, locked_until=now + LOCK_SECONDS, retry_at=0)
        log.warning(
            "account locked for %d s after %d failures ip=%s", LOCK_SECONDS, MAX_FAILURES, client_ip(request)
        )
        _send_lockout_mail(email, request)
    else:
        state["retry_at"] = now + min(2 ** (state["count"] - 1), MAX_DELAY)
    cache.set(_key(email), state, LOCK_SECONDS * 2)


def clear_failures(email):
    cache.delete(_key(email))


def _send_lockout_mail(email, request):
    user = get_user_model().objects.filter(username=email, is_active=True).first()
    if user is None:  # unknown accounts are "locked" too, but nobody can be told
        return
    link = request.build_absolute_uri(
        reverse(
            "password_reset_confirm",
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
            },
        )
    )
    send_mail(
        "AllergenTrace: sign-in paused for your account",
        (
            "Hello,\n\nthere were several unsuccessful attempts to sign in to your AllergenTrace account, "
            "so signing in is paused for 15 minutes.\n\nIf this was you and you forgot your password, "
            f"set a new one here:\n{link}\n\nIf it was not you, your password is still safe; "
            "you can set a new one with the same link to be sure.\n\nAllergenTrace"
        ),
        None,
        [user.email],
        fail_silently=True,
    )
