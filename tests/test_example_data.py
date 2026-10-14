import pytest
from django.urls import reverse

from accounts.models import Role
from allergen_engine.model import Allergen
from catalog.example_data import INGREDIENTS, SUPPLIERS
from catalog.models import Ingredient, Supplier

pytestmark = pytest.mark.django_db


def test_example_data_is_consistent():
    codes = {a.value for a in Allergen}
    suppliers = {s[0] for s in SUPPLIERS}
    for name, _product, supplier, contains, may, _checked in INGREDIENTS:
        assert set(contains) <= codes and set(may) <= codes, name
        assert not set(contains) & set(may), name
        assert supplier == "" or supplier in suppliers, name


def test_owner_loads_example_data_once_without_touching_own_entries(owner_client, owner):
    business = owner.membership.business
    mine = Ingredient.objects.create(
        business=business, name="Avocado", contains=["milk"]
    )  # owner's own entry
    response = owner_client.post(reverse("example_data"), follow=True)
    assert "example ingredients added" in response.content.decode()
    assert business.ingredients.count() == len(INGREDIENTS)  # "Avocado" was not duplicated
    assert Supplier.objects.filter(business=business).count() == len(SUPPLIERS)
    mine.refresh_from_db()
    assert mine.contains == ["milk"]
    assert business.ingredients.filter(status="unknown").exists()  # shows the unknown state too

    response = owner_client.post(reverse("example_data"), follow=True)
    assert "already there" in response.content.decode()
    assert business.ingredients.count() == len(INGREDIENTS)


def test_example_data_only_for_owner_and_only_by_post(client, owner_client, make_member, owner):
    assert owner_client.get(reverse("example_data")).status_code == 405
    client.force_login(make_member(Role.KITCHEN, business=owner.membership.business))
    assert client.post(reverse("example_data")).status_code == 403
    assert not Ingredient.objects.exists()
