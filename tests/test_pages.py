"""Site-wide page quality: titles, descriptions, error pages, messages and contact links."""

import re

import pytest
from django.urls import reverse

from accounts.models import Role
from catalog.models import Ingredient, Supplier

pytestmark = pytest.mark.django_db


def title_of(html):
    return re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()


@pytest.mark.parametrize("name", ["home", "login", "signup"])
def test_public_pages_have_title_and_description(client, name):
    html = client.get(reverse(name)).content.decode()
    assert "AllergenTrace" in title_of(html) and len(title_of(html)) > len("AllergenTrace – ")
    description = re.search(r'<meta name="description" content="([^"]+)"', html)
    assert description and len(description.group(1)) > 40


def test_back_office_pages_have_distinct_titles(owner_client, owner):
    supplier = Supplier.objects.create(business=owner.membership.business, name="Feinkost Rossi")
    urls = [
        "dashboard",
        "ingredient_list",
        "supplier_list",
        "staff_list",
        "ingredient_create",
        "supplier_create",
    ]
    titles = {title_of(owner_client.get(reverse(u)).content.decode()) for u in urls}
    titles.add(title_of(owner_client.get(reverse("supplier_update", args=[supplier.pk])).content.decode()))
    assert len(titles) == len(urls) + 1
    assert "Feinkost Rossi – AllergenTrace" in titles


def test_unknown_page_uses_custom_404(client, settings):
    settings.DEBUG = False
    response = client.get("/does-not-exist/")
    assert response.status_code == 404
    assert "This page does not exist" in response.content.decode()


def test_forbidden_page_explains_role(client, make_member):
    client.force_login(make_member(Role.SERVICE))
    response = client.get(reverse("ingredient_create"))
    assert response.status_code == 403
    assert "Your role does not allow this" in response.content.decode()


def test_footer_shows_current_year(client):
    from django.utils import timezone

    assert f"© {timezone.now().year} Sakshi Sharma" in client.get(reverse("home")).content.decode()


def test_delete_shows_success_message(owner_client, owner):
    ingredient = Ingredient.objects.create(business=owner.membership.business, name="Butter")
    response = owner_client.post(reverse("ingredient_delete", args=[ingredient.pk]), follow=True)
    assert "“Butter” deleted." in response.content.decode()


def test_logout_shows_message(owner_client):
    response = owner_client.post(reverse("logout"), follow=True)
    assert "You are logged out." in response.content.decode()


def test_supplier_phone_and_email_are_links(owner_client, owner):
    Supplier.objects.create(
        business=owner.membership.business, name="Rossi", phone="+49 30 123 45-6", email="info@rossi.de"
    )
    html = owner_client.get(reverse("supplier_list")).content.decode()
    assert 'href="tel:+4930123456"' in html
    assert 'href="mailto:info@rossi.de"' in html


def test_ingredient_form_hints_when_no_suppliers(owner_client, owner):
    html = owner_client.get(reverse("ingredient_create")).content.decode()
    assert "You have not added any suppliers yet." in html and "No supplier" in html
    Supplier.objects.create(business=owner.membership.business, name="Rossi")
    html = owner_client.get(reverse("ingredient_create")).content.decode()
    assert "You have not added any suppliers yet." not in html


def test_form_errors_are_summarised(owner_client):
    response = owner_client.post(reverse("supplier_create"), {"name": "", "email": "not-an-email"})
    html = response.content.decode()
    assert "Please correct the fields marked below." in html
    assert html.count('class="errorlist') >= 2


def test_success_messages_close_themselves_and_can_be_closed(owner_client):
    html = owner_client.post(reverse("supplier_create"), {"name": "Rossi"}, follow=True).content.decode()
    alert = re.search(r'<div class="alert alert-success[^>]*>', html).group(0)
    assert "data-autohide" in alert
    assert 'data-bs-dismiss="alert"' in html and "js/app.js" in html


def test_privacy_and_terms_pages_are_linked_in_the_footer(client, settings):
    settings.CONTACT_EMAIL = "kontakt@example.com"
    home = client.get(reverse("home")).content.decode()
    for name, text in (("privacy", "Privacy policy"), ("terms", "Terms of use")):
        assert reverse(name) in home
        page = client.get(reverse(name)).content.decode()
        assert text in page and "mailto:kontakt@example.com" in page
