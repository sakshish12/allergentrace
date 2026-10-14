"""The port through which the engine reads data (Phase 1, Figure 4).

The Django app provides the real implementation; tests use InMemoryRepository.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from allergen_engine.model import IngredientNode, RecipeNode


class RecipeRepository(Protocol):
    def ingredients(self) -> Mapping[int, IngredientNode]: ...

    def recipes(self) -> Mapping[int, RecipeNode]: ...


@dataclass
class InMemoryRepository:
    ingredient_nodes: dict[int, IngredientNode] = field(default_factory=dict)
    recipe_nodes: dict[int, RecipeNode] = field(default_factory=dict)

    def ingredients(self) -> Mapping[int, IngredientNode]:
        return self.ingredient_nodes

    def recipes(self) -> Mapping[int, RecipeNode]:
        return self.recipe_nodes
