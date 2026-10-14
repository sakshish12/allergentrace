from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Allergen(StrEnum):
    """The 14 allergens of Annex II of Regulation (EU) No 1169/2011, in the order of the Annex."""

    GLUTEN = "gluten"
    CRUSTACEANS = "crustaceans"
    EGGS = "eggs"
    FISH = "fish"
    PEANUTS = "peanuts"
    SOYBEANS = "soybeans"
    MILK = "milk"
    NUTS = "nuts"
    CELERY = "celery"
    MUSTARD = "mustard"
    SESAME = "sesame"
    SULPHITES = "sulphites"
    LUPIN = "lupin"
    MOLLUSCS = "molluscs"

    @property
    def label_en(self) -> str:
        return _LABELS[self][0]

    @property
    def label_de(self) -> str:
        return _LABELS[self][1]


_LABELS = {
    Allergen.GLUTEN: ("Cereals containing gluten", "Glutenhaltiges Getreide"),
    Allergen.CRUSTACEANS: ("Crustaceans", "Krebstiere"),
    Allergen.EGGS: ("Eggs", "Eier"),
    Allergen.FISH: ("Fish", "Fisch"),
    Allergen.PEANUTS: ("Peanuts", "Erdnüsse"),
    Allergen.SOYBEANS: ("Soybeans", "Sojabohnen"),
    Allergen.MILK: ("Milk", "Milch"),
    Allergen.NUTS: ("Nuts", "Schalenfrüchte"),
    Allergen.CELERY: ("Celery", "Sellerie"),
    Allergen.MUSTARD: ("Mustard", "Senf"),
    Allergen.SESAME: ("Sesame seeds", "Sesamsamen"),
    Allergen.SULPHITES: ("Sulphur dioxide and sulphites", "Schwefeldioxid und Sulphite"),
    Allergen.LUPIN: ("Lupin", "Lupinen"),
    Allergen.MOLLUSCS: ("Molluscs", "Weichtiere"),
}


class Status(StrEnum):
    """What a guest is told about one allergen in one dish."""

    CONTAINS = "contains"
    MAY_CONTAIN = "may_contain"
    ASK_STAFF = "ask_staff"  # BR-4: the dish uses an ingredient with unknown data
    FREE = "free"


# An explanation path: the names from a dish's direct component down to the source
# ingredient, e.g. ("Pesto", "Cashews") for "Pasta al pesto contains nuts".
Path = tuple[str, ...]


@dataclass(frozen=True)
class IngredientNode:
    id: int
    name: str
    contains: frozenset[Allergen]
    may_contain: frozenset[Allergen]
    known: bool  # False while nobody has checked the data against the label


@dataclass(frozen=True)
class EquipmentNode:
    id: int
    name: str
    dedicated: bool  # dedicated equipment is used for one recipe only and causes no cross-contact


@dataclass(frozen=True)
class RecipeNode:
    id: int
    name: str
    ingredient_ids: tuple[int, ...]
    recipe_ids: tuple[int, ...]  # sub-recipes such as sauces or doughs
    equipment_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class Declaration:
    """The calculated allergen declaration of a recipe, with the reason for every entry."""

    contains: Mapping[Allergen, tuple[Path, ...]]
    may_contain: Mapping[Allergen, tuple[Path, ...]]
    unknown: tuple[Path, ...]  # paths to ingredients whose data is not checked yet
    # BR-3: paths ending in (equipment, other recipe), e.g. ("Fryer", "Schnitzel")
    cross_contact: Mapping[Allergen, tuple[Path, ...]] = field(default_factory=dict)

    @property
    def needs_staff(self) -> bool:
        return bool(self.unknown)

    def status(self, allergen: Allergen) -> Status:
        return self.summary().status(allergen)

    def summary(self) -> "Summary":
        contains = frozenset(self.contains)
        traces = (frozenset(self.may_contain) | frozenset(self.cross_contact)) - contains
        return Summary(contains, traces, self.needs_staff)


@dataclass(frozen=True)
class Summary:
    """What a declaration says, without the reasons: this is what gets published to guests."""

    contains: frozenset[Allergen]
    may_contain: frozenset[Allergen]
    ask_staff: bool

    def rank(self, allergen: Allergen) -> int:
        """How strongly the allergen is declared: 2 contains, 1 may contain, 0 not declared."""
        return 2 if allergen in self.contains else 1 if allergen in self.may_contain else 0

    def status(self, allergen: Allergen) -> Status:
        if allergen in self.contains:
            return Status.CONTAINS
        if allergen in self.may_contain:
            return Status.MAY_CONTAIN
        return Status.ASK_STAFF if self.ask_staff else Status.FREE
