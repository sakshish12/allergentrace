"""BR-3 (cross-contact), US-10 (impact) and BR-6 (fail-safe publication) with concrete examples."""

from allergen_engine.impact import diff, impact
from allergen_engine.model import Allergen as A
from allergen_engine.model import EquipmentNode, IngredientNode, RecipeNode, Status, Summary
from allergen_engine.policy import merge, pending_removals
from allergen_engine.propagation import declare_all
from allergen_engine.repository import InMemoryRepository


def ing(id, name, contains=(), may=(), known=True):
    return IngredientNode(id, name, frozenset(contains), frozenset(may), known)


def kitchen(dedicated=False):
    """Schnitzel (breaded: wheat, egg) and fries share one fryer; fries are used in a burger menu."""
    return InMemoryRepository(
        {
            1: ing(1, "Breadcrumbs", [A.GLUTEN]),
            2: ing(2, "Egg", [A.EGGS]),
            3: ing(3, "Potatoes"),
            4: ing(4, "Bun", [A.GLUTEN, A.SESAME]),
        },
        {
            10: RecipeNode(10, "Schnitzel", (1, 2), (), (100,)),
            11: RecipeNode(11, "Fries", (3,), (), (100,)),
            12: RecipeNode(12, "Burger menu", (4,), (11,)),
        },
        {100: EquipmentNode(100, "Fryer", dedicated)},
    )


def test_br3_shared_fryer_gives_may_contain_with_reason():
    d = declare_all(kitchen())
    fries = d[11]
    assert fries.status(A.GLUTEN) is Status.MAY_CONTAIN and fries.status(A.EGGS) is Status.MAY_CONTAIN
    assert fries.cross_contact[A.EGGS] == (("Fryer", "Schnitzel"),)
    assert d[10].cross_contact == {}  # fries contain nothing the schnitzel could pick up


def test_br3_dish_inherits_cross_contact_of_its_sub_recipe():
    menu = declare_all(kitchen())[12]
    assert menu.cross_contact[A.EGGS] == (("Fries", "Fryer", "Schnitzel"),)
    assert A.GLUTEN not in menu.cross_contact  # BR-2: the bun already contains gluten
    assert menu.status(A.GLUTEN) is Status.CONTAINS


def test_br3_dedicated_equipment_causes_no_cross_contact():
    fries = declare_all(kitchen(dedicated=True))[11]
    assert fries.cross_contact == {} and fries.status(A.EGGS) is Status.FREE


def S(contains=(), may=(), ask=False):
    return Summary(frozenset(contains), frozenset(may), ask)


def test_impact_lists_only_changed_existing_recipes():
    before = {1: S([A.MILK]), 2: S([A.GLUTEN]), 3: S(ask=True)}
    after = {1: S([A.MILK, A.NUTS]), 2: S([A.GLUTEN]), 3: S(), 4: S([A.EGGS])}
    changes = impact(before, after)
    assert set(changes) == {1, 3}  # 2 is unchanged, 4 is new
    assert changes[1].added == {A.NUTS} and not changes[1].removed
    assert changes[3].ask_staff_removed and not changes[3].ask_staff_added


def test_impact_counts_contains_to_may_contain_as_removal():
    change = diff(S([A.MILK]), S(may=[A.MILK], ask=True))
    assert change.removed == {A.MILK} and not change.added and change.ask_staff_added


def test_br6_additions_are_published_at_once():
    published = merge(S([A.MILK]), S([A.MILK, A.NUTS]))
    assert published.contains == {A.MILK, A.NUTS}


def test_br6_removals_wait_for_approval():
    calculated = S(may=[A.MILK])
    published = merge(S([A.MILK, A.EGGS], ask=True), calculated)
    assert published.status(A.MILK) is Status.CONTAINS  # still published until approved
    assert published.ask_staff
    assert pending_removals(published, calculated) == (frozenset({A.MILK, A.EGGS}), True)
    # Approval means: publish exactly what was calculated; then nothing is pending.
    assert pending_removals(calculated, calculated) == (frozenset(), False)


def test_br6_new_recipe_is_published_as_calculated():
    assert merge(None, S([A.FISH])) == S([A.FISH])
