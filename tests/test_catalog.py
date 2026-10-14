"""US-03 (suppliers) and US-04 (ingredients with allergens), including role and tenancy checks."""

import datetime

import pytest
from django.urls import reverse

from accounts.models import Role
from catalog.models import Ingredient, Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def business(owner):
    return owner.membership.business


def post_ingredient(client, url, **data):
    return client.post(url, {"name": "Pesto", "product_name": "", "supplier": "", **data})


def test_new_ingredient_is_unknown_by_default(owner_client, business):
    post_ingredient(owner_client, reverse("ingredient_create"), contains=["milk", "nuts"])
    ingredient = Ingredient.objects.get(business=business)
    assert ingredient.contains == ["milk", "nuts"]
    assert ingredient.status == Ingredient.Status.UNKNOWN
    assert ingredient.verified_on is None


def test_confirming_data_sets_status_and_date(owner_client, business):
    post_ingredient(owner_client, reverse("ingredient_create"), contains=["milk"], data_complete="on")
    ingredient = Ingredient.objects.get(business=business)
    assert ingredient.status == Ingredient.Status.COMPLETE
    assert ingredient.verified_on is not None


def test_resaving_unchanged_data_keeps_verification_date(owner_client, business):
    old = datetime.date(2026, 1, 15)
    ingredient = Ingredient.objects.create(
        business=business, name="Pesto", contains=["milk"], status="complete", verified_on=old
    )
    url = reverse("ingredient_update", args=[ingredient.pk])
    post_ingredient(owner_client, url, name="Pesto Genovese", contains=["milk"], data_complete="on")
    ingredient.refresh_from_db()
    assert ingredient.verified_on == old
    post_ingredient(owner_client, url, contains=["milk", "nuts"], data_complete="on")
    ingredient.refresh_from_db()
    assert ingredient.verified_on > old


def test_same_allergen_cannot_be_contains_and_may_contain(owner_client):
    response = post_ingredient(
        owner_client, reverse("ingredient_create"), contains=["milk"], may_contain=["milk"]
    )
    assert response.status_code == 200
    assert not Ingredient.objects.exists()


def test_supplier_of_other_business_is_rejected(owner_client, make_member):
    foreign = Supplier.objects.create(business=make_member().membership.business, name="Fremd GmbH")
    post_ingredient(owner_client, reverse("ingredient_create"), supplier=foreign.pk)
    assert not Ingredient.objects.exists()


def test_service_can_read_but_not_change(client, make_member, business):
    Ingredient.objects.create(business=business, name="Butter", contains=["milk"])
    client.force_login(make_member(Role.SERVICE, business=business))
    assert "Butter" in client.get(reverse("ingredient_list")).content.decode()
    assert client.get(reverse("ingredient_create")).status_code == 403
    assert client.post(reverse("supplier_create"), {"name": "X"}).status_code == 403
    assert not Supplier.objects.exists()


def test_kitchen_can_create_supplier(client, make_member, business):
    client.force_login(make_member(Role.KITCHEN, business=business))
    assert client.post(reverse("supplier_create"), {"name": "Bio-Hof Weber"}).status_code == 302
    assert Supplier.objects.get().business == business


def test_other_business_data_is_invisible(client, make_member, business):
    ingredient = Ingredient.objects.create(business=business, name="Geheimrezept-Soße")
    supplier = Supplier.objects.create(business=business, name="Hausmetzgerei")
    client.force_login(make_member(Role.OWNER))  # owner of another business
    assert "Geheimrezept" not in client.get(reverse("ingredient_list")).content.decode()
    for name in ("ingredient_update", "ingredient_delete"):
        assert client.get(reverse(name, args=[ingredient.pk])).status_code == 404
        assert client.post(reverse(name, args=[ingredient.pk]), {"name": "hacked"}).status_code == 404
    assert client.post(reverse("supplier_delete", args=[supplier.pk])).status_code == 404
    ingredient.refresh_from_db()
    assert ingredient.name == "Geheimrezept-Soße"
    assert Supplier.objects.filter(pk=supplier.pk).exists()


def test_ingredient_form_shows_all_14_allergens(owner_client):
    html = owner_client.get(reverse("ingredient_create")).content.decode()
    assert html.count('name="contains"') == 14
    assert html.count('name="may_contain"') == 14
