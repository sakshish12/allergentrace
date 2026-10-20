"""US-18 unknown data list, US-19 copy a recipe, US-20 e-mail when an approval is needed."""

import json
from unittest import mock

import pytest
from django.core import mail
from django.core.mail import EmailMessage
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import Business, Role
from catalog.models import Ingredient
from config.mail import BrevoEmailBackend
from recipes.example_data import load_example_data
from recipes.models import Recipe
from recipes.views import dishes_by_ingredient

pytestmark = pytest.mark.django_db


@pytest.fixture
def cafe(owner):
    business = owner.membership.business
    load_example_data(business)
    return business


def cook_client(make_member, business):
    client = Client()
    client.force_login(make_member(Role.KITCHEN, business=business))
    return client


# US-18 ----------------------------------------------------------------------------------------


def test_unknown_list_shows_supplier_and_affected_dishes(client, cafe, make_member):
    Ingredient.objects.create(business=Business.objects.create(name="Other"), name="Foreign spice")
    client.force_login(make_member(Role.SERVICE, business=cafe))
    html = client.get(reverse("unknown_ingredients")).content.decode()
    assert "Chilli flakes" in html and "Avocado toast" in html
    assert "Mixed salad leaves" in html and "Frischehof Lindner" in html and "Smoked salmon sandwich" in html
    assert "Sourdough bread" not in html  # checked ingredients are not listed
    assert "Foreign spice" not in html


def test_dishes_are_found_through_sub_recipes(cafe):
    mayo = cafe.ingredients.get(name="Mayonnaise")
    assert [d.name for d in dishes_by_ingredient(cafe)[mayo.id]] == ["Smoked salmon sandwich"]


def test_unknown_list_is_empty_when_everything_is_checked(owner_client, owner):
    Ingredient.objects.create(business=owner.membership.business, name="Salt", status="complete")
    assert "All ingredients are checked" in owner_client.get(reverse("unknown_ingredients")).content.decode()


# US-19 ----------------------------------------------------------------------------------------


def parts(recipe):
    return sorted(recipe.components.values_list("ingredient__name", "sub_recipe__name", "quantity", "unit"))


def test_copy_has_same_parts_and_equipment_and_a_new_name(make_member, cafe):
    client = cook_client(make_member, cafe)
    cappuccino = cafe.recipes.get(name="Cappuccino")
    response = client.post(reverse("recipe_copy", args=[cappuccino.pk]))
    copy = cafe.recipes.get(name="Cappuccino (copy)")
    assert response.url == reverse("recipe_update", args=[copy.pk])
    assert parts(copy) == parts(cappuccino)
    assert set(copy.equipment.all()) == set(cappuccino.equipment.all())
    assert copy.publication.contains == cappuccino.publication.contains  # calculated after the copy
    client.post(reverse("recipe_copy", args=[cappuccino.pk]))
    assert cafe.recipes.filter(name="Cappuccino (copy 2)").exists()


def test_service_cannot_copy_and_nobody_copies_foreign_recipes(client, make_member, cafe, owner_client):
    toast = cafe.recipes.get(name="Avocado toast")
    service = Client()
    service.force_login(make_member(Role.SERVICE, business=cafe))
    assert service.post(reverse("recipe_copy", args=[toast.pk])).status_code == 403
    foreign = Recipe.objects.create(business=Business.objects.create(name="Other"), name="Secret")
    assert owner_client.post(reverse("recipe_copy", args=[foreign.pk])).status_code == 404
    assert owner_client.get(reverse("recipe_copy", args=[toast.pk])).status_code == 405


# US-20 ----------------------------------------------------------------------------------------


def remove_feta(client, business):
    toast = business.recipes.get(name="Avocado toast")
    feta = toast.components.get(ingredient__name="Feta")
    client.post(reverse("component_remove", args=[toast.pk, feta.pk]))


def test_owner_gets_one_mail_when_a_removal_waits(make_member, cafe, owner):
    client = cook_client(make_member, cafe)
    client.post(reverse("recipe_copy", args=[cafe.recipes.get(name="Cappuccino").pk]))  # sync once
    mail.outbox.clear()
    remove_feta(client, cafe)
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [owner.email]
    assert "Avocado toast" in message.subject
    assert "http://testserver" + reverse("approvals") in message.body


def test_no_mail_for_additions_or_for_the_owners_own_change(owner_client, make_member, cafe):
    owner_client.post(reverse("recipe_copy", args=[cafe.recipes.get(name="Cappuccino").pk]))
    mail.outbox.clear()
    remove_feta(owner_client, cafe)  # the owner sees the impact on the page
    toast = cafe.recipes.get(name="Avocado toast")
    egg = cafe.ingredients.get(name="Free-range eggs")
    cook_client(make_member, cafe).post(reverse("recipe_detail", args=[toast.pk]), {"part": f"i:{egg.pk}"})
    assert mail.outbox == []


@override_settings(BREVO_API_KEY="test-key")
def test_brevo_backend_posts_the_message():
    message = EmailMessage("Subject", "Body", "AllergenTrace <a@b.example>", ["owner@example.com"])
    with mock.patch("config.mail.urllib.request.urlopen") as urlopen:
        assert BrevoEmailBackend().send_messages([message]) == 1
    request = urlopen.call_args.args[0]
    assert request.headers["Api-key"] == "test-key"
    assert json.loads(request.data) == {
        "sender": {"name": "AllergenTrace", "email": "a@b.example"},
        "to": [{"email": "owner@example.com"}],
        "subject": "Subject",
        "textContent": "Body",
    }
    with mock.patch("config.mail.urllib.request.urlopen", side_effect=OSError):
        assert BrevoEmailBackend(fail_silently=True).send_messages([message]) == 0
        with pytest.raises(OSError):
            BrevoEmailBackend().send_messages([message])
