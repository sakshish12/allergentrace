"""Login protection, password hashing, password reset and input sanitising."""

from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import get_hasher, make_password
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from accounts import security
from accounts.forms import clean_text

pytestmark = pytest.mark.django_db
User = get_user_model()
PASSWORD = "Mehl-und-Wasser-42"


@pytest.fixture
def anna(db):
    return User.objects.create_user("anna@example.com", "anna@example.com", PASSWORD)


def login(client, password, email="anna@example.com"):
    return client.post(reverse("login"), {"username": email, "password": password})


class Clock:
    """Moves time forward without waiting."""

    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    c = Clock()
    with mock.patch("accounts.security.time.time", c):
        yield c


def test_rate_limit_ten_requests_per_ip_and_minute(client):
    for _ in range(10):
        assert client.get(reverse("login")).status_code == 200
    response = client.get(reverse("login"))
    assert response.status_code == 429 and response["Retry-After"] == "60"
    other_ip = Client(HTTP_TRUE_CLIENT_IP="203.0.113.9")
    assert other_ip.get(reverse("login")).status_code == 200


def test_progressive_delay_then_lockout_with_one_generic_message(client, anna, clock, caplog):
    for delay in (1, 2, 4, 8):
        assert "Incorrect email or password" in login(client, "wrong").content.decode()
        # during the delay even the right password is refused, with the same message
        assert "Incorrect email or password" in login(client, PASSWORD).content.decode()
        clock.now += delay
    cache.delete("rate:login:127.0.0.1")  # this test is about the account, not the IP limit
    assert "Incorrect email or password" in login(client, "wrong").content.decode()  # 5th failure: locked
    assert len(mail.outbox) == 1 and "/reset/" in mail.outbox[0].body and mail.outbox[0].to == [anna.email]
    clock.now += 14 * 60
    assert login(client, PASSWORD).status_code == 200  # still locked, still the same message
    clock.now += 61
    assert login(client, PASSWORD).status_code == 302
    assert PASSWORD not in caplog.text


def test_unknown_accounts_behave_like_existing_ones(client, clock):
    for _ in range(5):
        login(client, "wrong", email="nobody@example.com")
        clock.now += 10
    assert mail.outbox == []  # nobody to notify
    assert security.login_blocked("nobody@example.com")


def test_reset_link_from_lockout_sets_new_password_and_unlocks(client, anna, clock):
    for _ in range(5):
        login(client, "wrong")
        clock.now += 10
    link = mail.outbox[0].body.split("http://testserver")[1].split()[0]
    form_url = client.get(link).url  # Django swaps the token for a session marker
    client.post(form_url, {"new_password1": "Neues-Passwort-77", "new_password2": "Neues-Passwort-77"})
    assert not security.login_blocked("anna@example.com")
    assert login(client, "Neues-Passwort-77").status_code == 302


def test_password_reset_answer_is_the_same_for_unknown_addresses(client, anna):
    for email in ("anna@example.com", "nobody@example.com"):
        response = client.post(reverse("password_reset"), {"email": email}, follow=True)
        assert "If that email is registered, you'll receive a reset link" in response.content.decode()
    assert len(mail.outbox) == 1


def test_bcrypt_with_cost_12_and_upgrade_of_old_hashes(settings, client):
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]
    assert get_hasher().algorithm == "bcrypt_sha256" and get_hasher().rounds >= 12
    old = User.objects.create(
        username="old@example.com", password=make_password(PASSWORD, hasher="pbkdf2_sha256")
    )
    assert login(client, PASSWORD, email="old@example.com").status_code == 302
    old.refresh_from_db()
    assert old.password.startswith("bcrypt_sha256$$2b$12$")  # re-hashed at login
    assert old.check_password(PASSWORD) and not old.check_password(PASSWORD + "x")


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Café <b>Linde</b>", "Café Linde"),
        ("<script>alert(1)</script>Bäckerei", "Bäckerei"),
        ("Müller &  Söhne\x00\n", "Müller & Söhne"),
    ],
)
def test_clean_text(raw, clean):
    assert clean_text(raw) == clean


def test_overlong_inputs_are_rejected_before_authentication(client, anna):
    with mock.patch("accounts.forms.AuthenticationForm.clean") as authenticate:
        login(client, "x" * 129)
        login(client, PASSWORD, email="a" * 200 + "@example.com")
    authenticate.assert_not_called()
