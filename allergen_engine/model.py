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
