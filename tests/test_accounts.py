"""US-01 (register a business) and US-02 (staff accounts with roles)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import Business, Membership, Role

pytestmark = pytest.mark.django_db
SIGNUP = {
    "business_name": "Bäckerei Sonnenschein",
    "email": "Anna@Example.com",
    "password1": "Mehl-und-Wasser-42",
    "password2": "Mehl-und-Wasser-42",
}


def test_signup_creates_business_and_owner_and_logs_in(client):
    response = client.post(reverse("signup"), SIGNUP)
    assert response.status_code == 302 and response.url == reverse("dashboard")
    membership = Membership.objects.get(user__username="anna@example.com")
    assert membership.role == Role.OWNER
    assert membership.business.name == "Bäckerei Sonnenschein"
    assert client.get(reverse("dashboard")).status_code == 200


def test_signup_rejects_existing_email_and_weak_password(client, owner):
    response = client.post(reverse("signup"), {**SIGNUP, "email": owner.email})
    assert "already exists" in response.content.decode()
    response = client.post(
        reverse("signup"), {**SIGNUP, "email": "new@example.com", "password1": "123", "password2": "123"}
    )
    assert response.status_code == 200
    assert Business.objects.count() == 1  # only the owner fixture's business


def test_login_is_case_insensitive_and_error_does_not_reveal_account(client):
    client.post(reverse("signup"), SIGNUP)
    client.logout()
    ok = client.post(reverse("login"), {"username": "ANNA@example.com", "password": SIGNUP["password1"]})
    assert ok.status_code == 302
    client.logout()
    wrong_password = client.post(reverse("login"), {"username": "anna@example.com", "password": "nope"})
    unknown_user = client.post(reverse("login"), {"username": "nobody@example.com", "password": "nope"})
    assert wrong_password.status_code == unknown_user.status_code == 200
    assert "E-mail or password is not correct" in wrong_password.content.decode()
    assert "E-mail or password is not correct" in unknown_user.content.decode()


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
