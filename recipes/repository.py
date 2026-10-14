"""Django implementation of the engine's RecipeRepository port, plus the calls the views use."""

from allergen_engine.model import Allergen, Declaration, EquipmentNode, IngredientNode, RecipeNode
from allergen_engine.propagation import declare_all
from catalog.models import Equipment, Ingredient
from recipes.models import Component, Recipe


class DjangoRecipeRepository:
    """Loads all ingredients, recipes and equipment of one business with five queries."""

    def __init__(self, business):
        self._ingredients = {
            i.id: IngredientNode(
                i.id,
                i.name,
                frozenset(map(Allergen, i.contains)),
                frozenset(map(Allergen, i.may_contain)),
                known=i.status == Ingredient.Status.COMPLETE,
            )
            for i in Ingredient.objects.filter(business=business)
        }
        parts: dict[int, tuple[list[int], list[int]]] = {}
        for c in Component.objects.filter(recipe__business=business).values_list(
            "recipe_id", "ingredient_id", "sub_recipe_id"
        ):
            ingredient_ids, recipe_ids = parts.setdefault(c[0], ([], []))
            (ingredient_ids if c[1] else recipe_ids).append(c[1] or c[2])
        tools: dict[int, list[int]] = {}
        for rid, eid in Recipe.equipment.through.objects.filter(recipe__business=business).values_list(
            "recipe_id", "equipment_id"
        ):
            tools.setdefault(rid, []).append(eid)
        self._recipes = {
            rid: RecipeNode(rid, name, *map(tuple, parts.get(rid, ([], []))), tuple(tools.get(rid, ())))
            for rid, name in Recipe.objects.filter(business=business).values_list("id", "name")
        }
        self._equipment = {
            e.id: EquipmentNode(e.id, e.name, e.dedicated)
            for e in Equipment.objects.filter(business=business)
        }

    def ingredients(self):
        return self._ingredients

    def recipes(self):
        return self._recipes

    def equipment(self):
        return self._equipment

    def edges(self):
        return {rid: r.recipe_ids for rid, r in self._recipes.items()}


def declarations_for(business) -> dict[int, Declaration]:
    return declare_all(DjangoRecipeRepository(business))
