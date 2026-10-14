from pathlib import Path

import allergen_engine
from allergen_engine.model import Allergen


def test_exactly_the_14_annex_ii_allergens_with_both_labels():
    assert len(Allergen) == 14
    for allergen in Allergen:
        assert allergen.label_en and allergen.label_de


def test_engine_does_not_depend_on_django():
    """NFR-08: the domain core stays plain Python."""
    package = Path(allergen_engine.__file__).parent
    for source in package.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "import django" not in text and "from django" not in text, source.name
