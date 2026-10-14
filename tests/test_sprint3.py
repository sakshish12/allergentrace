"""US-05 equipment, US-09 cross-contact, US-10 impact, US-11 fail-safe publication, US-12 history."""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Role
from catalog.models import Equipment, Ingredient
from publication.models import PublishedDeclaration
from recipes.models import Component, Recipe

pytestmark = pytest.mark.django_db


@pytest.fixture
def cafe(owner):
    """Pesto pasta (pasta + cashew pesto) and schnitzel; schnitzel and fries share a fryer."""
    b = owner.membership.business
    i = {
        name: Ingredient.objects.create(business=b, name=name, contains=c, status="complete")
        for name, c in [
            ("Pasta", ["gluten"]),
            ("Cashews", ["nuts"]),
            ("Breadcrumbs", ["gluten"]),
            ("Egg", ["eggs"]),
            ("Potatoes", []),
        ]
    }
    pasta = Recipe.objects.create(business=b, name="Pesto pasta")
    schnitzel = Recipe.objects.create(business=b, name="Schnitzel")
    fries = Recipe.objects.create(business=b, name="Fries")
    for recipe, parts in [
        (pasta, ["Pasta", "Cashews"]),
        (schnitzel, ["Breadcrumbs", "Egg"]),
        (fries, ["Potatoes"]),
    ]:
        for part in parts:
            Component.objects.create(recipe=recipe, ingredient=i[part])
    fryer = Equipment.objects.create(business=b, name="Fryer")
    return {"business": b, "pasta": pasta, "schnitzel": schnitzel, "fries": fries, "fryer": fryer, **i}


def publication(recipe):
    return PublishedDeclaration.objects.get(recipe=recipe)


def test_equipment_crud_and_role(client, owner_client, make_member, owner):
    owner_client.post(reverse("equipment_create"), {"name": "Fryer"})
    fryer = Equipment.objects.get(business=owner.membership.business)
    assert not fryer.dedicated
    assert "Fryer" in owner_client.get(reverse("equipment_list")).content.decode()
    client.force_login(make_member(Role.SERVICE, business=owner.membership.business))
    assert client.get(reverse("equipment_create")).status_code == 403
    client.force_login(make_member(Role.OWNER))  # other business
    assert client.get(reverse("equipment_update", args=[fryer.pk])).status_code == 404


def test_shared_fryer_adds_may_contain_and_explains_it(owner_client, cafe):
    for recipe in ("schnitzel", "fries"):
        owner_client.post(
            reverse("recipe_equipment", args=[cafe[recipe].pk]), {"equipment": [cafe["fryer"].pk]}
        )
    html = owner_client.get(reverse("recipe_detail", args=[cafe["fries"].pk])).content.decode()
    assert "shared Fryer, also used for Schnitzel" in html
    assert publication(cafe["fries"]).may_contain == ["gluten", "eggs"]


def test_dedicated_equipment_adds_nothing(owner_client, cafe):
    Equipment.objects.filter(pk=cafe["fryer"].pk).update(dedicated=True)
    for recipe in ("schnitzel", "fries"):
        owner_client.post(
            reverse("recipe_equipment", args=[cafe[recipe].pk]), {"equipment": [cafe["fryer"].pk]}
        )
    assert publication(cafe["fries"]).may_contain == []


def test_equipment_of_other_business_cannot_be_used(client, make_member, cafe):
    stranger = make_member(Role.OWNER)
    own = Recipe.objects.create(business=stranger.membership.business, name="Own")
    client.force_login(stranger)
    client.post(reverse("recipe_equipment", args=[own.pk]), {"equipment": [cafe["fryer"].pk]})
    assert not own.equipment.exists()


def test_addition_is_published_at_once_and_impact_is_shown(owner_client, cafe):
    owner_client.post(reverse("recipe_create"), {"name": "Starter"})  # first sync: everything published
    assert publication(cafe["pasta"]).contains == ["gluten", "nuts"]
    owner_client.post(
        reverse("ingredient_update", args=[cafe["Pasta"].pk]),
        {"name": "Pasta", "contains": ["gluten", "eggs"], "data_complete": "on"},
    )
    html = owner_client.get(reverse("ingredient_list")).content.decode()
    assert "This change affects 1 recipe" in html and "now declares Eggs" in html
    assert publication(cafe["pasta"]).contains == ["gluten", "eggs", "nuts"]
    assert (
        "This change affects" not in owner_client.get(reverse("ingredient_list")).content.decode()
    )  # shown once


def test_removal_waits_for_owner_approval(owner_client, make_member, cafe):
    owner_client.post(reverse("recipe_create"), {"name": "Starter"})
    cashews = cafe["pasta"].components.get(ingredient=cafe["Cashews"])
    owner_client.post(reverse("component_remove", args=[cafe["pasta"].pk, cashews.pk]))
    row = publication(cafe["pasta"])
    assert "nuts" in row.contains and row.calc_contains == ["gluten"]  # guests still see nuts
    assert row.pending_labels() == ["Nuts"]
    detail = owner_client.get(reverse("recipe_detail", args=[cafe["pasta"].pk])).content.decode()
    assert "Waiting for approval" in detail and "Guests still see: Nuts" in detail

    cook = Client()  # a second browser, so the owner stays logged in
    cook.force_login(make_member(Role.KITCHEN, business=cafe["business"]))
    assert "Pesto pasta" in cook.get(reverse("approvals")).content.decode()
    assert cook.post(reverse("approve", args=[row.pk])).status_code == 403

    response = owner_client.post(reverse("approve", args=[row.pk]), follow=True)
    assert "Approved." in response.content.decode()
    row.refresh_from_db()
    assert row.contains == ["gluten"] and not row.has_pending and row.approved_by.membership.is_owner


def test_approve_all_and_no_open_redirect(owner_client, cafe):
    owner_client.post(reverse("recipe_create"), {"name": "Starter"})
    for recipe, ingredient in [("pasta", "Cashews"), ("schnitzel", "Egg")]:
        part = cafe[recipe].components.get(ingredient=cafe[ingredient])
        owner_client.post(reverse("component_remove", args=[cafe[recipe].pk, part.pk]))
    response = owner_client.post(reverse("approve_all"), {"next": "https://evil.example/"})
    assert response.url == reverse("approvals")
    assert not any(row.has_pending for row in PublishedDeclaration.objects.all())


def test_history_records_who_changed_what(owner_client, owner, client, make_member, cafe):
    owner_client.post(
        reverse("ingredient_update", args=[cafe["Egg"].pk]),
        {"name": "Free-range egg", "contains": ["eggs"], "data_complete": "on"},
    )
    html = owner_client.get(reverse("history")).content.decode()
    assert "Free-range egg" in html and owner.email in html and "Egg → Free-range egg" in html
    client.force_login(make_member(Role.OWNER))  # another business sees nothing of this
    assert "Free-range egg" not in client.get(reverse("history")).content.decode()


def test_failed_form_does_not_recalculate(owner_client, cafe):
    owner_client.post(reverse("ingredient_create"), {"name": ""})  # invalid: answered with 200
    assert not PublishedDeclaration.objects.exists()
