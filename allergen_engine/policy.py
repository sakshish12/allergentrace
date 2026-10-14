"""BR-6 fail-safe publication: the published declaration may say more than the calculated one, never less.

Additions are published at once; removals wait until the owner approves them.
"""

from allergen_engine.model import Allergen, Summary


def merge(published: Summary | None, calculated: Summary) -> Summary:
    """The new published declaration after a recalculation, before any approval."""
    if published is None:  # first publication of a new recipe
        return calculated
    contains = published.contains | calculated.contains
    return Summary(
        contains=contains,
        may_contain=(published.may_contain | calculated.may_contain) - contains,
        ask_staff=published.ask_staff or calculated.ask_staff,
    )


def pending_removals(published: Summary, calculated: Summary) -> tuple[frozenset[Allergen], bool]:
    """What the owner still has to approve: weaker allergens, and dropping 'please ask staff'."""
    weaker = frozenset(a for a in Allergen if published.rank(a) > calculated.rank(a))
    return weaker, published.ask_staff and not calculated.ask_staff
