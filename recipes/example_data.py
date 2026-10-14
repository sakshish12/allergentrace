"""Realistic example data for a small café, so a new business can see the app working at once.

The allergen information reflects what these products typically declare. It is example data:
the message after loading tells the owner to check it against their own product labels.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from catalog.models import Ingredient, Supplier
from recipes.models import Component, Recipe

SUPPLIERS = [
    # name, contact person, phone, e-mail (reserved .example domain, numbers are fictitious)
    ("Bäckerei Kornfeld", "Jana Kornfeld", "+49 30 5550 1201", "bestellung@kornfeld.example"),
    ("Frischehof Lindner", "Tobias Lindner", "+49 33 2055 5014", "hof@lindner.example"),
    ("Feinkost Rossi", "Marco Rossi", "+49 30 5550 3377", "info@feinkost-rossi.example"),
    ("Molkerei Havelland", "", "+49 33 2155 5090", "service@molkerei-havelland.example"),
]

# name, product name, supplier, contains, may contain, data checked against the label?
INGREDIENTS = [
    ("Sourdough bread", "Rye-wheat sourdough loaf, 1 kg", "Bäckerei Kornfeld", ["gluten"], ["sesame"], True),
    (
        "Butter croissant",
        "Frozen butter croissant, 70 g",
        "Bäckerei Kornfeld",
        ["gluten", "milk", "eggs"],
        ["soybeans", "sesame"],
        True,
    ),
    ("Avocado", "Hass avocado, fresh", "Frischehof Lindner", [], [], True),
    ("Free-range eggs", "Eggs, size M", "Frischehof Lindner", ["eggs"], [], True),
    ("Mixed salad leaves", "Salad mix, washed", "Frischehof Lindner", [], [], False),
    ("Lemon", "Lemons, untreated", "Frischehof Lindner", [], [], True),
    ("Whole milk", "Fresh milk 3.5 % fat", "Molkerei Havelland", ["milk"], [], True),
    ("Butter", "Sweet cream butter", "Molkerei Havelland", ["milk"], [], True),
    ("Feta", "Feta cheese, sheep and goat milk", "Molkerei Havelland", ["milk"], [], True),
    ("Greek yogurt", "Greek-style yogurt 10 % fat", "Molkerei Havelland", ["milk"], [], True),
    ("Oat drink", "Oat drink barista edition", "Feinkost Rossi", ["gluten"], [], True),
    ("Smoked salmon", "Cold-smoked salmon, sliced", "Feinkost Rossi", ["fish"], [], True),
    (
        "Basil pesto",
        "Pesto with cashews and Grana Padano",
        "Feinkost Rossi",
        ["milk", "nuts"],
        ["peanuts"],
        True,
    ),
    ("Hummus", "Chickpea hummus with tahini", "Feinkost Rossi", ["sesame"], [], True),
    ("Dijon mustard", "Dijon mustard, 200 g", "Feinkost Rossi", ["mustard", "sulphites"], [], True),
    ("Mayonnaise", "Mayonnaise 80 % fat", "Feinkost Rossi", ["eggs", "mustard"], [], True),
    (
        "Granola",
        "Oat granola with hazelnuts",
        "Feinkost Rossi",
        ["gluten", "nuts"],
        ["peanuts", "soybeans"],
        True,
    ),
    ("Chilli flakes", "Chilli flakes, loose", "", [], [], False),
    ("Espresso beans", "Espresso blend, 1 kg", "", [], [], True),
    ("Olive oil", "Extra virgin olive oil", "Feinkost Rossi", [], [], True),
]

# name, served as a dish?, parts: (name, "i" for ingredient or "r" for recipe, quantity, unit).
# Sub-recipes come before the dishes that use them.
RECIPES = [
    (
        "Herb mayo",
        False,
        [("Mayonnaise", "i", 200, "g"), ("Dijon mustard", "i", 10, "g"), ("Lemon", "i", 0.25, "pieces")],
    ),
    (
        "Pesto dressing",
        False,
        [("Basil pesto", "i", 60, "g"), ("Olive oil", "i", 40, "ml"), ("Lemon", "i", 0.5, "pieces")],
    ),
    (
        "Avocado toast",
        True,
        [
            ("Sourdough bread", "i", 2, "slices"),
            ("Avocado", "i", 0.5, "pieces"),
            ("Feta", "i", 30, "g"),
            ("Lemon", "i", 0.1, "pieces"),
            ("Chilli flakes", "i", 1, "g"),
        ],
    ),
    (
        "Smoked salmon sandwich",
        True,
        [
            ("Sourdough bread", "i", 2, "slices"),
            ("Smoked salmon", "i", 60, "g"),
            ("Herb mayo", "r", 20, "g"),
            ("Mixed salad leaves", "i", 15, "g"),
        ],
    ),
    (
        "Green salad with pesto dressing",
        True,
        [("Mixed salad leaves", "i", 80, "g"), ("Feta", "i", 40, "g"), ("Pesto dressing", "r", 30, "ml")],
    ),
    ("Yogurt bowl with granola", True, [("Greek yogurt", "i", 150, "g"), ("Granola", "i", 50, "g")]),
    (
        "Hummus plate",
        True,
        [("Hummus", "i", 120, "g"), ("Sourdough bread", "i", 2, "slices"), ("Olive oil", "i", 10, "ml")],
    ),
    ("Butter croissant", True, [("Butter croissant", "i", 1, "pieces"), ("Butter", "i", 10, "g")]),
    ("Cappuccino", True, [("Espresso beans", "i", 18, "g"), ("Whole milk", "i", 150, "ml")]),
    ("Oat flat white", True, [("Espresso beans", "i", 18, "g"), ("Oat drink", "i", 120, "ml")]),
]


@transaction.atomic
def load_example_data(business):
    """Add the example suppliers, ingredients and recipes that the business does not have yet.

    Safe to run twice: existing names are never changed or duplicated, and recipes use the
    business's own ingredient if it has the same name. Returns (ingredients added, recipes added).
    """
    suppliers = {s.name: s for s in business.suppliers.all()}
    for name, person, phone, email in SUPPLIERS:
        if name not in suppliers:
            suppliers[name] = Supplier.objects.create(
                business=business, name=name, contact_person=person, phone=phone, email=email
            )

    existing = set(business.ingredients.values_list("name", flat=True))
    today = timezone.localdate()
    new = [
        Ingredient(
            business=business,
            name=name,
            product_name=product,
            supplier=suppliers.get(supplier),
            contains=contains,
            may_contain=may,
            status=Ingredient.Status.COMPLETE if checked else Ingredient.Status.UNKNOWN,
            verified_on=today if checked else None,
        )
        for name, product, supplier, contains, may, checked in INGREDIENTS
        if name not in existing
    ]
    Ingredient.objects.bulk_create(new)

    ingredients = {i.name: i for i in business.ingredients.all()}
    recipes = {r.name: r for r in business.recipes.all()}
    added_recipes = 0
    for name, is_dish, parts in RECIPES:
        if name in recipes:
            continue
        recipe = recipes[name] = Recipe.objects.create(business=business, name=name, is_dish=is_dish)
        added_recipes += 1
        Component.objects.bulk_create(
            Component(
                recipe=recipe,
                ingredient=ingredients[part] if kind == "i" else None,
                sub_recipe=recipes[part] if kind == "r" else None,
                quantity=Decimal(str(quantity)),
                unit=unit,
            )
            for part, kind, quantity, unit in parts
        )
    return len(new), added_recipes
