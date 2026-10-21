"""Example-based tests: one or more per business rule (docs/requirements/business-rules.md)."""

import pytest

from allergen_engine.graph import CycleError, topological_order, would_create_cycle
from allergen_engine.model import Allergen as A
from allergen_engine.model import IngredientNode, RecipeNode, Status
from allergen_engine.propagation import declare_all
from allergen_engine.repository import InMemoryRepository


def ing(id, name, contains=(), may=(), known=True):
    return IngredientNode(id, name, frozenset(contains), frozenset(may), known)


def rec(id, name, ingredients=(), recipes=()):
    return RecipeNode(id, name, tuple(ingredients), tuple(recipes))


@pytest.fixture
def pasta_al_pesto():
    """Pasta al pesto = pasta + pesto (sub-recipe: cashews, parmesan, oil)."""
    return InMemoryRepository(
        {
            1: ing(1, "Durum wheat pasta", [A.GLUTEN]),
            2: ing(2, "Cashews", [A.NUTS], may=[A.PEANUTS]),
            3: ing(3, "Parmesan", [A.MILK]),
            4: ing(4, "Olive oil"),
        },
        {
            10: rec(10, "Pesto", ingredients=[2, 3, 4]),
            11: rec(11, "Pasta al pesto", ingredients=[1], recipes=[10]),
        },
    )


def test_br1_dish_inherits_allergens_of_sub_recipe_with_path(pasta_al_pesto):
    dish = declare_all(pasta_al_pesto)[11]
    assert set(dish.contains) == {A.GLUTEN, A.NUTS, A.MILK}
    assert dish.contains[A.NUTS] == (("Pesto", "Cashews"),)
    assert dish.contains[A.GLUTEN] == (("Durum wheat pasta",),)
    assert dish.may_contain == {A.PEANUTS: (("Pesto", "Cashews"),)}
    assert dish.status(A.EGGS) is Status.FREE


def test_br1_change_in_sub_recipe_reaches_every_dish():
    repo = InMemoryRepository(
        {1: ing(1, "Pine nuts"), 2: ing(2, "Bread", [A.GLUTEN])},
        {10: rec(10, "Pesto", [1]), 11: rec(11, "Pasta", recipes=[10]), 12: rec(12, "Bruschetta", [2], [10])},
    )
    assert A.NUTS not in declare_all(repo)[11].contains  # pine nuts are not an Annex II nut
    repo.ingredient_nodes[1] = ing(1, "Cashews", [A.NUTS])  # the supplier changes the pesto
    after = declare_all(repo)
    assert A.NUTS in after[11].contains and A.NUTS in after[12].contains


def test_br2_contains_overrides_may_contain():
    repo = InMemoryRepository(
        {1: ing(1, "Chocolate", may=[A.MILK]), 2: ing(2, "Cream", [A.MILK])},
        {10: rec(10, "Mousse", [1, 2])},
    )
    dish = declare_all(repo)[10]
    assert dish.status(A.MILK) is Status.CONTAINS
    assert A.MILK not in dish.may_contain


def test_br4_unknown_ingredient_means_ask_staff_never_free(pasta_al_pesto):
    pasta_al_pesto.ingredient_nodes[4] = ing(4, "Olive oil", known=False)
    dish = declare_all(pasta_al_pesto)[11]
    assert dish.needs_staff and dish.unknown == (("Pesto", "Olive oil"),)
    assert dish.status(A.EGGS) is Status.ASK_STAFF
    assert dish.status(A.MILK) is Status.CONTAINS  # known allergens are still declared
    assert dish.status(A.PEANUTS) is Status.MAY_CONTAIN


def test_br4_recipe_without_parts_means_ask_staff(pasta_al_pesto):
    pasta_al_pesto.recipe_nodes[20] = rec(20, "Soup of the day", [])
    pasta_al_pesto.recipe_nodes[21] = rec(21, "Lunch menu", [], recipes=[20])
    declarations = declare_all(pasta_al_pesto)
    assert declarations[20].unknown == ((),) and declarations[20].status(A.EGGS) is Status.ASK_STAFF
    assert declarations[21].unknown == (("Soup of the day",),)


def test_br5_cycle_is_detected():
    with pytest.raises(CycleError) as error:
        topological_order({1: [2], 2: [3], 3: [1]})
    assert error.value.cycle in ([1, 2, 3, 1], [2, 3, 1, 2], [3, 1, 2, 3])


def test_br5_self_reference_is_a_cycle():
    with pytest.raises(CycleError):
        topological_order({1: [1]})


def test_br5_would_create_cycle():
    edges = {1: [2], 2: [3], 3: []}  # dish 1 uses sauce 2, which uses base 3
    assert would_create_cycle(edges, 3, 1)  # base 3 must not contain the dish
    assert would_create_cycle(edges, 2, 2)  # nothing may contain itself
    assert not would_create_cycle(edges, 1, 3)  # the dish may also use the base directly


def test_sub_recipe_used_twice_is_calculated_once_and_paths_are_unique():
    repo = InMemoryRepository(
        {1: ing(1, "Egg", [A.EGGS])},
        {
            10: rec(10, "Mayo", [1]),
            11: rec(11, "Herb mayo", recipes=[10]),
            12: rec(12, "Sandwich", recipes=[10, 11]),
        },
    )
    dish = declare_all(repo)[12]
    assert dish.contains[A.EGGS] == (("Herb mayo", "Mayo", "Egg"), ("Mayo", "Egg"))
    assert topological_order({12: [10, 11], 11: [10], 10: []}).index(10) == 0


def test_br5_shared_base_is_visited_once():
    # Two sauces share the same base; the base is reached twice but checked once.
    edges = {1: [2, 3], 2: [4], 3: [4], 4: []}
    assert not would_create_cycle(edges, 9, 1)
    assert would_create_cycle(edges, 4, 1)
