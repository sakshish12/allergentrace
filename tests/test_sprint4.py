"""US-13 menu selection, US-14 public guest menu, US-15 guest filter, US-16 PDF list, US-17 QR code."""

from io import BytesIO

import pytest
import segno
from django.test import Client
from django.urls import reverse

from accounts.models import Business, Role
from publication.models import Menu
from publication.services import sync
from recipes.example_data import load_example_data
from recipes.models import Recipe

pytestmark = pytest.mark.django_db


@pytest.fixture
def cafe(owner):
    business = owner.membership.business
    load_example_data(business)
    sync(business)
    return business


@pytest.fixture
def menu(cafe):
    return Menu.for_business(cafe)


def guest(menu, lang="en", **query):
    url = reverse("guest_menu_lang", args=[menu.qr_token, lang])
    return Client().get(url, query).content.decode()


def test_new_menu_has_every_dish_and_the_owner_chooses(owner_client, cafe, menu):
    dishes = cafe.recipes.filter(is_dish=True)
    assert set(menu.dishes.all()) == set(dishes)
    assert not menu.dishes.filter(name="Herb mayo").exists()  # sub-recipes are not dishes

    other = Recipe.objects.create(business=Business.objects.create(name="Other"), name="Foreign dish")
    toast = dishes.get(name="Avocado toast")
    response = owner_client.post(reverse("menu"), {"dishes": [toast.pk, other.pk, "x"]}, follow=True)
    assert "Menu saved" in response.content.decode()
    assert list(menu.dishes.all()) == [toast]  # another business's dish is ignored


def test_staff_see_the_menu_page_but_only_the_owner_changes_it(client, cafe, make_member, menu):
    client.force_login(make_member(Role.SERVICE, business=cafe))
    page = client.get(reverse("menu")).content.decode()
    assert menu.qr_token in page and "Only the owner" in page
    assert client.post(reverse("menu"), {"dishes": []}).status_code == 403
    assert menu.dishes.count() == cafe.recipes.filter(is_dish=True).count()


def test_guest_menu_is_public_and_shows_only_menu_dishes(menu):
    menu.dishes.set(menu.business.recipes.filter(name__in=["Avocado toast", "Cappuccino"]))
    html = guest(menu)
    assert "Avocado toast" in html and "Cappuccino" in html
    assert "Hummus plate" not in html
    assert "Please ask our staff." in html  # the chilli flakes are unchecked (BR-4)
    assert Client().get("/m/not-a-token/").status_code == 404
    assert Client().get(f"/m/{menu.qr_token}/fr/").status_code == 404


def test_guest_menu_shows_published_not_calculated_data(owner_client, menu):
    # Removing the feta takes milk out of the calculation, but guests keep seeing it until approved (BR-6).
    toast = menu.business.recipes.get(name="Avocado toast")
    feta = toast.components.get(ingredient__name="Feta")
    owner_client.post(reverse("component_remove", args=[toast.pk, feta.pk]))
    toast.publication.refresh_from_db()
    assert "milk" not in toast.publication.calc_contains
    assert "milk" in toast.publication.contains
    menu.dishes.set([toast])
    assert ">Milk<" in guest(menu)


def test_guest_filter_hides_contains_and_traces_but_keeps_ask_staff(menu):
    # Avocado toast: gluten, milk, may contain sesame, ask staff. Oat flat white: gluten, may contain milk.
    html = guest(menu, avoid=["milk"])
    assert "Avocado toast" not in html and "Cappuccino" not in html
    assert "Oat flat white" not in html  # traces of milk are hidden by default
    html = guest(menu, avoid=["milk"], traces="1")
    assert "Oat flat white" in html and "Cappuccino" not in html

    html = guest(menu, avoid=["fish", "bogus"])
    assert "Smoked salmon sandwich" not in html
    assert "Avocado toast" in html and "may contain one of your allergens" in html
    assert "1 dish is hidden" in html


def test_guest_menu_in_german(menu):
    html = guest(menu, "de", avoid=["gluten"], traces="1")
    assert 'lang="de"' in html and "Ich vertrage nicht:" in html
    assert "Milch" in html and "Gerichte sind wegen Ihrer Allergene ausgeblendet" in html
    assert "Password" not in html
    # the QR link follows the browser language
    bare = Client().get(reverse("guest_menu", args=[menu.qr_token]), HTTP_ACCEPT_LANGUAGE="de-DE,de;q=0.9")
    assert "Speisekarte mit Allergenen" in bare.content.decode()
    assert "Menu with allergens" in Client().get(reverse("guest_menu", args=[menu.qr_token])).content.decode()


def test_back_office_stays_english_after_a_german_guest_page(owner_client, menu):
    guest(menu, "de")
    assert "Recipes" in owner_client.get(reverse("recipe_list")).content.decode()


def test_pdf_allergen_list(owner_client, menu):
    response = owner_client.get(reverse("menu_pdf"))
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response["Content-Disposition"]


def test_pdf_template_lists_menu_dishes_with_marks(owner, menu):
    from django.template.loader import render_to_string

    from allergen_engine.model import Allergen

    menu.dishes.set(menu.business.recipes.filter(name="Oat flat white"))
    rows = [(d, s, [s.rank(a) for a in Allergen]) for d, s in menu.entries()]
    html = render_to_string(
        "publication/menu_pdf.html", {"business": menu.business, "rows": rows, "allergens": list(Allergen)}
    )
    assert "Oat flat white" in html and "Cappuccino" not in html
    assert "<td>X</td>" in html and "<td>(X)</td>" in html  # gluten contained, milk as a trace


@pytest.mark.parametrize(("kind", "start"), [("png", b"\x89PNG"), ("svg", b"<?xml")])
def test_qr_code_opens_the_public_menu(owner_client, menu, kind, start):
    response = owner_client.get(reverse("menu_qr", args=[kind]))
    assert response.content.startswith(start)
    # byte for byte the QR code of the public link
    expected = BytesIO()
    url = "http://testserver" + reverse("guest_menu", args=[menu.qr_token])
    segno.make(url, error="m").save(expected, kind=kind, scale=10, border=4)
    assert response.content == expected.getvalue()


def test_menu_pages_need_a_login(client):
    for name, args in [("menu", []), ("menu_pdf", []), ("menu_qr", ["png"])]:
        assert client.get(reverse(name, args=args)).status_code == 302
