"""Calculation of declarations from the recipe graph (BR-1, BR-2, BR-3, BR-4)."""

from collections import defaultdict

from allergen_engine.cross_contact import direct_cross_contact
from allergen_engine.graph import topological_order
from allergen_engine.model import Allergen, Declaration, Path
from allergen_engine.repository import RecipeRepository

Paths = dict[Allergen, set[Path]]


def declare_all(repo: RecipeRepository) -> dict[int, Declaration]:
    """Declarations of all recipes. Each recipe is calculated once, after its sub-recipes."""
    ingredients, recipes = repo.ingredients(), repo.recipes()
    order = topological_order({rid: recipe.recipe_ids for rid, recipe in recipes.items()})

    # Pass 1: what each recipe contains or may contain through its ingredients (BR-1, BR-4).
    contains: dict[int, Paths] = {}
    may_contain: dict[int, Paths] = {}
    unknown: dict[int, set[Path]] = {}
    for rid in order:
        recipe = recipes[rid]
        contains[rid], may_contain[rid], unknown[rid] = defaultdict(set), defaultdict(set), set()
        for iid in recipe.ingredient_ids:
            ingredient = ingredients[iid]
            for allergen in ingredient.contains:
                contains[rid][allergen].add((ingredient.name,))
            for allergen in ingredient.may_contain:
                may_contain[rid][allergen].add((ingredient.name,))
            if not ingredient.known:
                unknown[rid].add((ingredient.name,))
        # shortcut: keeps every distinct path; fine for a café's recipes, would need a cap for
        # very deep shared sub-recipe trees.
        for sid in recipe.recipe_ids:
            name = recipes[sid].name
            _inherit(contains[rid], contains[sid], name)
            _inherit(may_contain[rid], may_contain[sid], name)
            unknown[rid].update((name, *p) for p in unknown[sid])
        if not recipe.ingredient_ids and not recipe.recipe_ids:
            # BR-4: a recipe without parts proves nothing, so it is never shown as allergen-free.
            unknown[rid].add(())

    # Pass 2: cross-contact needs the finished "contains" of every recipe (BR-3); dishes inherit
    # the cross-contact of their sub-recipes as well.
    cross = direct_cross_contact(recipes, repo.equipment(), {rid: set(c) for rid, c in contains.items()})
    for rid in order:
        for sid in recipes[rid].recipe_ids:
            _inherit(cross[rid], cross[sid], recipes[sid].name)

    return {
        rid: Declaration(
            contains=_freeze(contains[rid], set()),
            # BR-2: "contains" overrides "may contain" for the same allergen.
            may_contain=_freeze(may_contain[rid], contains[rid]),
            unknown=tuple(sorted(unknown[rid])),
            cross_contact=_freeze(cross[rid], contains[rid]),
        )
        for rid in order
    }


def _inherit(target: Paths, source: Paths, via: str) -> None:
    for allergen, paths in source.items():
        target[allergen].update((via, *p) for p in paths)


def _freeze(paths: Paths, exclude) -> dict[Allergen, tuple[Path, ...]]:
    """Sorted, immutable paths in Annex II order, leaving out allergens in `exclude`."""
    return {a: tuple(sorted(paths[a])) for a in Allergen if paths.get(a) and a not in exclude}
