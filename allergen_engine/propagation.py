"""Calculation of declarations from the recipe graph (BR-1, BR-2, BR-4)."""

from collections import defaultdict

from allergen_engine.graph import topological_order
from allergen_engine.model import Allergen, Declaration, Path
from allergen_engine.repository import RecipeRepository


def declare_all(repo: RecipeRepository) -> dict[int, Declaration]:
    """Declarations of all recipes. Each recipe is calculated once, after its sub-recipes."""
    ingredients, recipes = repo.ingredients(), repo.recipes()
    order = topological_order({rid: recipe.recipe_ids for rid, recipe in recipes.items()})
    result: dict[int, Declaration] = {}
    for rid in order:
        recipe = recipes[rid]
        contains: dict[Allergen, set[Path]] = defaultdict(set)
        may_contain: dict[Allergen, set[Path]] = defaultdict(set)
        unknown: set[Path] = set()

        for iid in recipe.ingredient_ids:
            ingredient = ingredients[iid]
            for allergen in ingredient.contains:
                contains[allergen].add((ingredient.name,))
            for allergen in ingredient.may_contain:
                may_contain[allergen].add((ingredient.name,))
            if not ingredient.known:
                unknown.add((ingredient.name,))

        # BR-1: a recipe inherits everything its sub-recipes declare, with the path behind it.
        # shortcut: keeps every distinct path; fine for a café's recipes, would need a cap for
        # very deep shared sub-recipe trees.
        for sid in recipe.recipe_ids:
            name, sub = recipes[sid].name, result[sid]
            for allergen, paths in sub.contains.items():
                contains[allergen].update((name, *p) for p in paths)
            for allergen, paths in sub.may_contain.items():
                may_contain[allergen].update((name, *p) for p in paths)
            unknown.update((name, *p) for p in sub.unknown)

        result[rid] = Declaration(
            contains={a: tuple(sorted(contains[a])) for a in Allergen if a in contains},
            # BR-2: "contains" overrides "may contain" for the same allergen.
            may_contain={
                a: tuple(sorted(may_contain[a])) for a in Allergen if a in may_contain and a not in contains
            },
            unknown=tuple(sorted(unknown)),
        )
    return result
