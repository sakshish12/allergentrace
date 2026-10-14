"""US-15: which dishes the guest filter hides."""

import pytest

from allergen_engine.model import Allergen as A
from allergen_engine.model import Summary

TOAST = Summary(frozenset({A.GLUTEN, A.MILK}), frozenset({A.SESAME}), ask_staff=True)


@pytest.mark.parametrize(
    ("avoid", "show_may", "hidden"),
    [
        (set(), False, False),  # no filter: everything is visible
        ({A.MILK}, False, True),  # contains the allergen
        ({A.SESAME}, False, True),  # traces are hidden by default ...
        ({A.SESAME}, True, False),  # ... and shown when the guest asks for them
        ({A.MILK}, True, True),  # showing traces never shows a dish that contains it
        ({A.FISH}, False, False),  # 'please ask staff' alone never hides the dish
    ],
)
def test_guest_filter(avoid, show_may, hidden):
    assert TOAST.hidden_for(frozenset(avoid), show_may) is hidden
