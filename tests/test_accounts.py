"""US-01 (register a business) and US-02 (staff accounts with roles)."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from accounts.models import Business, Membership, Role

pytestmark = pytest.mark.django_db
SIGNUP = {
    "business_name": "Bäckerei Sonnenschein",
    "email": "Anna@Example.com",
    "password1": "Mehl-und-Wasser-42",
    "password2": "Mehl-und-Wasser-42",
}


def activation_link(message):
    return re.search(r"http://testserver(/activate/\S+/)", message.body).group(1)


def test_signup_sends_link_that_activates_and_logs_in(client):
    response = client.post(reverse("signup"), SIGNUP)
    assert response.status_code == 302 and response.url == reverse("signup_done")
    membership = Membership.objects.get(user__username="anna@example.com")
    assert membership.role == Role.OWNER and not membership.user.is_active
    assert membership.business.name == "Bäckerei Sonnenschein"
    response = client.get(activation_link(mail.outbox[-1]))
    assert response.url == reverse("dashboard")
    assert client.get(reverse("dashboard")).status_code == 200
    client.logout()
    assert client.get(activation_link(mail.outbox[-1])).url == reverse("signup")  # used only once


def test_signup_does_not_reveal_existing_email(client, owner):
    response = client.post(reverse("signup"), {**SIGNUP, "email": owner.email})
    assert response.status_code == 302 and response.url == reverse("signup_done")  # same answer as new
    assert "already has an account" in mail.outbox[-1].body and mail.outbox[-1].to == [owner.email]
    assert Business.objects.count() == 1


def test_signup_answers_every_invalid_input_with_one_message(client):
    for data in (
        {**SIGNUP, "password1": "123", "password2": "123"},
        {**SIGNUP, "email": "not-an-email"},
        {**SIGNUP, "business_name": "<script>alert(1)</script>"},
        {**SIGNUP, "email": "a" * 200 + "@example.com"},
    ):
        html = client.post(reverse("signup"), data).content.decode()
        assert "We could not register you with these details" in html
        assert "aria-invalid" not in html  # no field is singled out
    assert not Business.objects.exists()


def test_login_is_case_insensitive_and_error_does_not_reveal_account(client):
    client.post(reverse("signup"), SIGNUP)
    client.get(activation_link(mail.outbox[-1]))
    client.logout()
    ok = client.post(reverse("login"), {"username": "ANNA@example.com", "password": SIGNUP["password1"]})
    assert ok.status_code == 302
    client.logout()
    wrong_password = client.post(reverse("login"), {"username": "anna@example.com", "password": "nope"})
    unknown_user = client.post(reverse("login"), {"username": "nobody@example.com", "password": "nope"})
    assert wrong_password.status_code == unknown_user.status_code == 200
    assert "Incorrect email or password" in wrong_password.content.decode()
    assert "Incorrect email or password" in unknown_user.content.decode()


def test_owner_creates_kitchen_account(owner_client, owner):
    response = owner_client.post(
        reverse("staff_create"),
        {
            "email": "koch@example.com",
            "password1": "Topf-und-Deckel-7",
            "password2": "Topf-und-Deckel-7",
            "role": 2,
        },
    )
    assert response.status_code == 302
    membership = Membership.objects.get(user__username="koch@example.com")
    assert membership.role == Role.KITCHEN
    assert membership.business == owner.membership.business


def test_deactivated_staff_cannot_log_in(owner_client, make_member, owner):
    cook = make_member(Role.KITCHEN, business=owner.membership.business)
    response = owner_client.post(reverse("staff_update", args=[cook.membership.pk]), {"role": 2})
    assert response.status_code == 302
    cook.refresh_from_db()
    assert not cook.is_active
    owner_client.logout()
    assert (
        owner_client.post(reverse("login"), {"username": cook.username, "password": "pw"}).status_code == 200
    )


def test_owner_cannot_edit_own_membership(owner_client, owner):
    assert owner_client.get(reverse("staff_update", args=[owner.membership.pk])).status_code == 404


@pytest.mark.parametrize("role", [Role.KITCHEN, Role.SERVICE])
def test_only_owner_manages_staff(client, make_member, role):
    client.force_login(make_member(role))
    for url in (reverse("staff_list"), reverse("staff_create")):
        assert client.get(url).status_code == 403


def test_owner_cannot_edit_staff_of_other_business(owner_client, make_member):
    stranger = make_member(Role.KITCHEN)  # creates a second business
    assert owner_client.get(reverse("staff_update", args=[stranger.membership.pk])).status_code == 404


def test_back_office_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302 and response.url.startswith(reverse("login"))


def test_user_without_business_is_refused(client):
    user = get_user_model().objects.create_user(username="admin@example.com", password="pw")
    client.force_login(user)
    assert client.get(reverse("dashboard")).status_code == 403


@pytest.mark.django_db
def test_create_demo_needs_password_and_runs_once(monkeypatch, client):
    from django.core.management import call_command

    monkeypatch.delenv("DJANGO_DEMO_PASSWORD", raising=False)
    call_command("create_demo")
    assert not Membership.objects.exists()

    monkeypatch.setenv("DJANGO_DEMO_PASSWORD", "Demo-pass-2026")
    call_command("create_demo")
    call_command("create_demo")  # second run changes nothing
    roles = sorted(Membership.objects.values_list("role", flat=True))
    assert roles == [Role.SERVICE, Role.KITCHEN, Role.OWNER]
    owner = Membership.objects.get(role=Role.OWNER).business
    assert owner.name == "Café Demo" and owner.recipes.exists()
    assert client.login(username="demo-kitchen@example.com", password="Demo-pass-2026")
