"""US-06 (recipes and sub-recipes), US-07 (calculation) and US-08 (explanation) through the web app."""

import pytest
from django.urls import reverse

from accounts.models import Role
from allergen_engine.model import Allergen, Status
from catalog.models import Ingredient
from recipes.models import Component, Recipe
from recipes.repository import DjangoRecipeRepository, declarations_for

pytestmark = pytest.mark.django_db


@pytest.fixture
def kitchen(owner):
    """Pesto (cashews, parmesan, oil) used in Pasta al pesto (pasta)."""
    b = owner.membership.business
    ing = {
        name: Ingredient.objects.create(business=b, name=name, contains=c, may_contain=m, status="complete")
        for name, c, m in [
            ("Cashews", ["nuts"], ["peanuts"]),
            ("Parmesan", ["milk"], []),
            ("Olive oil", [], []),
            ("Pasta", ["gluten"], []),
        ]
    }
    pesto = Recipe.objects.create(business=b, name="Pesto", is_dish=False)
    dish = Recipe.objects.create(business=b, name="Pasta al pesto")
    for name in ("Cashews", "Parmesan", "Olive oil"):
        Component.objects.create(recipe=pesto, ingredient=ing[name])
    Component.objects.create(recipe=dish, ingredient=ing["Pasta"])
    Component.objects.create(recipe=dish, sub_recipe=pesto)
    return {"business": b, "pesto": pesto, "dish": dish, **ing}


def test_declaration_is_calculated_through_sub_recipe(kitchen):
    dish = declarations_for(kitchen["business"])[kitchen["dish"].id]
    assert dish.status(Allergen.NUTS) is Status.CONTAINS
    assert dish.contains[Allergen.NUTS] == (("Pesto", "Cashews"),)
    assert dish.status(Allergen.PEANUTS) is Status.MAY_CONTAIN
    assert dish.status(Allergen.EGGS) is Status.FREE


def test_detail_page_explains_each_allergen(owner_client, kitchen):
    html = owner_client.get(reverse("recipe_detail", args=[kitchen["dish"].pk])).content.decode()
    assert "Pesto → Cashews" in html and "Pesto → Parmesan" in html
    assert "Please ask staff" not in html


def test_unchecked_ingredient_turns_dish_into_please_ask_staff(owner_client, kitchen):
    Ingredient.objects.filter(pk=kitchen["Olive oil"].pk).update(status="unknown")
    html = owner_client.get(reverse("recipe_detail", args=[kitchen["dish"].pk])).content.decode()
    assert "Please ask staff" in html and "Pesto → Olive oil" in html
    list_html = owner_client.get(reverse("recipe_list")).content.decode()
    assert "Please ask staff" in list_html


def test_change_to_ingredient_reaches_dish(owner_client, kitchen):
    Ingredient.objects.filter(pk=kitchen["Olive oil"].pk).update(contains=["sesame"])
    assert Allergen.SESAME in declarations_for(kitchen["business"])[kitchen["dish"].id].contains


def test_add_ingredient_and_sub_recipe(owner_client, owner):
    b = owner.membership.business
    egg = Ingredient.objects.create(business=b, name="Egg", contains=["eggs"], status="complete")
    mayo = Recipe.objects.create(business=b, name="Mayo", is_dish=False)
    sandwich = Recipe.objects.create(business=b, name="Sandwich")
    owner_client.post(
        reverse("recipe_detail", args=[mayo.pk]), {"part": f"i:{egg.pk}", "quantity": "2", "unit": "pieces"}
    )
    response = owner_client.post(
        reverse("recipe_detail", args=[sandwich.pk]), {"part": f"r:{mayo.pk}"}, follow=True
    )
    assert "“Mayo” added." in response.content.decode()
    assert declarations_for(b)[sandwich.id].contains[Allergen.EGGS] == (("Mayo", "Egg"),)


def test_cycle_is_rejected_with_explanation(owner_client, kitchen):
    response = owner_client.post(
        reverse("recipe_detail", args=[kitchen["pesto"].pk]), {"part": f"r:{kitchen['dish'].pk}"}
    )
    assert response.status_code == 200
    assert "already uses “Pesto”" in response.content.decode()
    assert not Component.objects.filter(recipe=kitchen["pesto"], sub_recipe=kitchen["dish"]).exists()


def test_same_part_cannot_be_added_twice(owner_client, kitchen):
    response = owner_client.post(
        reverse("recipe_detail", args=[kitchen["pesto"].pk]), {"part": f"i:{kitchen['Cashews'].pk}"}
    )
    assert response.status_code == 200
    assert kitchen["pesto"].components.filter(ingredient=kitchen["Cashews"]).count() == 1


def test_remove_component(owner_client, kitchen):
    component = kitchen["pesto"].components.get(ingredient=kitchen["Cashews"])
    owner_client.post(reverse("component_remove", args=[kitchen["pesto"].pk, component.pk]))
    assert Allergen.NUTS not in declarations_for(kitchen["business"])[kitchen["dish"].id].contains


def test_used_ingredient_and_sub_recipe_cannot_be_deleted(owner_client, kitchen):
    response = owner_client.post(reverse("ingredient_delete", args=[kitchen["Cashews"].pk]), follow=True)
    assert "still used in: Pesto" in response.content.decode()
    assert Ingredient.objects.filter(pk=kitchen["Cashews"].pk).exists()
    response = owner_client.post(reverse("recipe_delete", args=[kitchen["pesto"].pk]), follow=True)
    assert "still used in: Pasta al pesto" in response.content.decode()
    assert Recipe.objects.filter(pk=kitchen["pesto"].pk).exists()


def test_service_reads_recipes_but_cannot_change_them(client, make_member, kitchen):
    client.force_login(make_member(Role.SERVICE, business=kitchen["business"]))
    html = client.get(reverse("recipe_detail", args=[kitchen["dish"].pk])).content.decode()
    assert "Pesto → Cashews" in html and "Add a part" not in html
    assert client.post(reverse("recipe_detail", args=[kitchen["dish"].pk]), {"part": "x"}).status_code == 403
    component = kitchen["dish"].components.first()
    assert (
        client.post(reverse("component_remove", args=[kitchen["dish"].pk, component.pk])).status_code == 403
    )
    assert client.get(reverse("recipe_create")).status_code == 403


def test_other_business_cannot_see_or_use_recipes(client, make_member, kitchen):
    stranger = make_member(Role.OWNER)
    own = Recipe.objects.create(business=stranger.membership.business, name="Own dish")
    client.force_login(stranger)
    assert client.get(reverse("recipe_detail", args=[kitchen["dish"].pk])).status_code == 404
    assert "Pasta al pesto" not in client.get(reverse("recipe_list")).content.decode()
    # Their form does not offer, and does not accept, our ingredients or recipes.
    for part in (f"i:{kitchen['Cashews'].pk}", f"r:{kitchen['pesto'].pk}"):
        assert client.post(reverse("recipe_detail", args=[own.pk]), {"part": part}).status_code == 200
    assert not own.components.exists()
    component = kitchen["dish"].components.first()
    assert (
        client.post(reverse("component_remove", args=[kitchen["dish"].pk, component.pk])).status_code == 404
    )


def test_repository_needs_five_queries(django_assert_num_queries, kitchen):
    with django_assert_num_queries(5):
        DjangoRecipeRepository(kitchen["business"])


def test_new_recipe_goes_to_its_page(owner_client):
    response = owner_client.post(reverse("recipe_create"), {"name": "Avocado toast", "is_dish": "on"})
    assert response.url == reverse("recipe_detail", args=[Recipe.objects.get().pk])
