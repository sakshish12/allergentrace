"""BR-3: cross-contact through shared equipment."""

from collections import defaultdict
from collections.abc import Mapping

from allergen_engine.model import Allergen, EquipmentNode, Path, RecipeNode


def direct_cross_contact(
    recipes: Mapping[int, RecipeNode],
    equipment: Mapping[int, EquipmentNode],
    contains: Mapping[int, set[Allergen]],
) -> dict[int, dict[Allergen, set[Path]]]:
    """For every recipe, the allergens it may pick up from other recipes on the same equipment.

    If two recipes use the same non-dedicated equipment, each receives the allergens the other
    contains as "may contain". The path names the equipment and the other recipe.
    """
    users: dict[int, list[int]] = defaultdict(list)
    for rid, recipe in recipes.items():
        for eid in recipe.equipment_ids:
            if not equipment[eid].dedicated:
                users[eid].append(rid)

    result: dict[int, dict[Allergen, set[Path]]] = {rid: defaultdict(set) for rid in recipes}
    for eid, rids in users.items():
        for rid in rids:
            for other in rids:
                if other != rid:
                    for allergen in contains[other]:
                        result[rid][allergen].add((equipment[eid].name, recipes[other].name))
    return result
