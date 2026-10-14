"""Impact of a change: which dishes now declare more or less than before (US-10)."""

from collections.abc import Mapping
from dataclasses import dataclass

from allergen_engine.model import Allergen, Summary


@dataclass(frozen=True)
class Change:
    added: frozenset[Allergen]  # declared more strongly than before (new, or "may contain" → "contains")
    removed: frozenset[Allergen]  # declared less strongly than before
    ask_staff_added: bool
    ask_staff_removed: bool

    def __bool__(self) -> bool:
        return bool(self.added or self.removed or self.ask_staff_added or self.ask_staff_removed)


def diff(before: Summary, after: Summary) -> Change:
    return Change(
        added=frozenset(a for a in Allergen if after.rank(a) > before.rank(a)),
        removed=frozenset(a for a in Allergen if after.rank(a) < before.rank(a)),
        ask_staff_added=after.ask_staff and not before.ask_staff,
        ask_staff_removed=before.ask_staff and not after.ask_staff,
    )


def impact(before: Mapping[int, Summary], after: Mapping[int, Summary]) -> dict[int, Change]:
    """Changes of recipes that existed before and after; new or deleted recipes are not 'affected'."""
    changes = {rid: diff(before[rid], after[rid]) for rid in before.keys() & after.keys()}
    return {rid: change for rid, change in changes.items() if change}
