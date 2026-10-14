import pytest
from django.urls import reverse

from accounts.models import Role
from allergen_engine.model import Allergen, Status
from catalog.models import Ingredient, Supplier
from recipes.example_data import EQUIPMENT, INGREDIENTS, RECIPES, SUPPLIERS, load_example_data
from recipes.models import Recipe
from recipes.repository import declarations_for

pytestmark = pytest.mark.django_db


def test_example_data_is_consistent():
    codes = {a.value for a in Allergen}
    suppliers = {s[0] for s in SUPPLIERS}
    ingredients = {i[0] for i in INGREDIENTS}
    for name, _product, supplier, contains, may, _checked in INGREDIENTS:
        assert set(contains) <= codes and set(may) <= codes, name
        assert not set(contains) & set(may), name
        assert supplier == "" or supplier in suppliers, name
    defined = set()
    for name, _is_dish, parts in RECIPES:
        for part, kind, _qty, _unit in parts:
            assert part in (ingredients if kind == "i" else defined), (name, part)
        defined.add(name)
    for _name, _dedicated, used_by in EQUIPMENT:
        assert set(used_by) <= defined


def test_owner_loads_example_data_once_without_touching_own_entries(owner_client, owner):
    business = owner.membership.business
    mine = Ingredient.objects.create(business=business, name="Avocado", contains=["milk"])
    response = owner_client.post(reverse("example_data"), follow=True)
    assert f"{len(INGREDIENTS) - 1} ingredients and {len(RECIPES)} recipes" in response.content.decode()
    assert business.ingredients.count() == len(INGREDIENTS)  # "Avocado" was not duplicated
    assert Supplier.objects.filter(business=business).count() == len(SUPPLIERS)
    mine.refresh_from_db()
    assert mine.contains == ["milk"]
    # the owner's own avocado (with milk) is the one used in the avocado toast
    toast = Recipe.objects.get(business=business, name="Avocado toast")
    assert toast.components.filter(ingredient=mine).exists()

    response = owner_client.post(reverse("example_data"), follow=True)
    assert "already there" in response.content.decode()
    assert business.ingredients.count() == len(INGREDIENTS)
    assert business.recipes.count() == len(RECIPES)


def test_example_recipes_show_the_rules(owner):
    business = owner.membership.business
    load_example_data(business)
    d = {r.name: declarations_for(business)[r.id] for r in business.recipes.all()}
    toast = d["Avocado toast"]
    assert {Allergen.GLUTEN, Allergen.MILK} <= set(toast.contains)
    assert toast.status(Allergen.SESAME) is Status.MAY_CONTAIN  # from the sourdough bread
    assert toast.needs_staff  # chilli flakes are unchecked
    sandwich = d["Smoked salmon sandwich"]
    assert (("Herb mayo", "Mayonnaise"),) == sandwich.contains[Allergen.EGGS]
    assert d["Cappuccino"].status(Allergen.MILK) is Status.CONTAINS
    # BR-3: the shared steam wand carries milk into the oat flat white, and gluten the other way
    assert d["Oat flat white"].status(Allergen.MILK) is Status.MAY_CONTAIN
    assert d["Oat flat white"].cross_contact[Allergen.MILK] == (
        ("Steam wand (espresso machine)", "Cappuccino"),
    )
    assert d["Cappuccino"].status(Allergen.GLUTEN) is Status.MAY_CONTAIN


def test_example_data_only_for_owner_and_only_by_post(client, owner_client, make_member, owner):
    assert owner_client.get(reverse("example_data")).status_code == 405
    client.force_login(make_member(Role.KITCHEN, business=owner.membership.business))
    assert client.post(reverse("example_data")).status_code == 403
    assert not Ingredient.objects.exists()


def test_edits_of_example_data_show_their_changes_in_history(owner_client, owner):
    business = owner.membership.business
    load_example_data(business)
    pesto = business.ingredients.get(name="Basil pesto")
    owner_client.post(
        reverse("ingredient_update", args=[pesto.pk]),
        {"name": "Basil pesto", "contains": ["milk"], "may_contain": ["peanuts"], "data_complete": "on"},
    )
    assert "Milk, Nuts → Milk" in owner_client.get(reverse("history")).content.decode()
