"""Problems found by clicking through the site like a first-time user, kept fixed by these tests."""

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Ingredient, Supplier
from publication.models import Menu
from publication.services import sync
from recipes.models import Recipe

pytestmark = pytest.mark.django_db


@pytest.fixture
def business(owner):
    return owner.membership.business


def test_names_are_unique_per_business_ignoring_case(owner_client, business, make_member):
    data = {"product_name": "", "supplier": ""}
    owner_client.post(reverse("ingredient_create"), {"name": "Tomatoes", **data})
    response = owner_client.post(reverse("ingredient_create"), {"name": "tomatoes", **data})
    assert "already exists" in response.content.decode()
    assert Ingredient.objects.filter(business=business).count() == 1
    # Saving an entry under its own name is fine, and another business may use the same name.
    tomatoes = Ingredient.objects.get(business=business)
    response = owner_client.post(
        reverse("ingredient_update", args=[tomatoes.pk]), {"name": "Tomatoes", **data}
    )
    assert response.status_code == 302
    other = Client()
    other.force_login(make_member())
    other.post(reverse("ingredient_create"), {"name": "Tomatoes", **data})
    assert Ingredient.objects.filter(name="Tomatoes").count() == 2
    # The same rule holds for recipes.
    owner_client.post(reverse("recipe_create"), {"name": "Soup", "is_dish": "on"})
    response = owner_client.post(reverse("recipe_create"), {"name": "SOUP", "is_dish": "on"})
    assert "already exists" in response.content.decode()


def test_quantity_accepts_a_decimal_comma(owner_client, business):
    soup = Recipe.objects.create(business=business, name="Soup", is_dish=True)
    salt = Ingredient.objects.create(business=business, name="Salt")
    owner_client.post(
        reverse("recipe_detail", args=[soup.pk]), {"part": f"i:{salt.pk}", "quantity": "0,5", "unit": "g"}
    )
    assert str(soup.components.get().quantity) == "0.50"


def test_phone_number_rejects_letters(owner_client, business):
    data = {"contact_person": "", "email": ""}
    response = owner_client.post(reverse("supplier_create"), {"name": "Farm", "phone": "call me", **data})
    assert "Use only digits" in response.content.decode()
    owner_client.post(reverse("supplier_create"), {"name": "Farm", "phone": "+49 (30) 123-45/6", **data})
    assert Supplier.objects.filter(business=business).count() == 1


def test_logged_in_user_skips_the_login_page(owner_client):
    assert owner_client.get(reverse("login")).url == reverse("dashboard")


def test_typing_logout_in_the_address_bar_asks_instead_of_failing(owner_client):
    response = owner_client.get(reverse("logout"))
    assert response.status_code == 200 and "Log out of AllergenTrace?" in response.content.decode()
    assert Client().get(reverse("logout")).url == reverse("home")
    owner_client.post(reverse("logout"))
    assert owner_client.get(reverse("dashboard")).status_code == 302


def test_dish_without_parts_is_never_shown_as_allergen_free(owner_client, business):
    Recipe.objects.create(business=business, name="Soup of the day", is_dish=True)
    sync(business)
    menu = Menu.for_business(business)
    html = Client().get(reverse("guest_menu_lang", args=[menu.qr_token, "en"])).content.decode()
    assert "Please ask our staff." in html and "None of the 14 main allergens" not in html
    detail = owner_client.get(reverse("recipe_detail", args=[menu.dishes.get().pk])).content.decode()
    assert "No ingredients or recipes added yet" in detail


def test_deleting_a_supplier_or_equipment_in_use_warns_first(owner_client, business):
    from catalog.models import Equipment

    farm = Supplier.objects.create(business=business, name="Farm")
    Ingredient.objects.create(business=business, name="Milk", supplier=farm)
    page = owner_client.get(reverse("supplier_delete", args=[farm.pk])).content.decode()
    assert "will have no supplier: Milk" in page
    fryer = Equipment.objects.create(business=business, name="Fryer")
    Recipe.objects.create(business=business, name="Fries").equipment.add(fryer)
    page = owner_client.get(reverse("equipment_delete", args=[fryer.pk])).content.decode()
    assert "Used for: Fries" in page


def test_history_shows_names_not_ids_for_linked_entries(owner_client, business, owner):
    farm = Supplier.objects.create(business=business, name="Farm")
    milk = Ingredient.objects.create(business=business, name="Milk")
    milk.supplier = farm
    milk.save()
    page = owner_client.get(reverse("history")).content.decode()
    assert "– → Farm" in page or "&ndash; → Farm" in page


def test_new_dish_is_published_without_approval_once_it_has_parts(owner_client, business):
    from publication.models import PublishedDeclaration

    soup = Recipe.objects.create(business=business, name="Soup", is_dish=True)
    sync(business)
    assert not PublishedDeclaration.objects.filter(recipe=soup).exists()
    cream = Ingredient.objects.create(business=business, name="Cream", contains=["milk"], status="complete")
    soup.components.create(ingredient=cream)
    sync(business)
    published = PublishedDeclaration.objects.get(recipe=soup).published()
    assert not published.ask_staff and {a.value for a in published.contains} == {"milk"}
