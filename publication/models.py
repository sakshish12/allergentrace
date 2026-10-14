from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from allergen_engine.model import Allergen, Summary
from allergen_engine.policy import pending_removals
from recipes.models import Recipe


def _codes(label):
    return ArrayField(models.CharField(max_length=20), default=list, blank=True, verbose_name=label)


class PublishedDeclaration(models.Model):
    """What guests may see for a recipe, next to what was calculated last (BR-6).

    'published' only ever loses an allergen through an owner's approval; 'calculated' is
    overwritten after every change.
    """

    recipe = models.OneToOneField(Recipe, on_delete=models.CASCADE, related_name="publication")
    contains = _codes(_("published: contains"))
    may_contain = _codes(_("published: may contain"))
    ask_staff = models.BooleanField(_("published: please ask staff"), default=False)
    calc_contains = _codes(_("calculated: contains"))
    calc_may_contain = _codes(_("calculated: may contain"))
    calc_ask_staff = models.BooleanField(_("calculated: please ask staff"), default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    def __str__(self):
        return str(self.recipe)

    def published(self) -> Summary:
        return Summary(
            frozenset(map(Allergen, self.contains)),
            frozenset(map(Allergen, self.may_contain)),
            self.ask_staff,
        )

    def calculated(self) -> Summary:
        return Summary(
            frozenset(map(Allergen, self.calc_contains)),
            frozenset(map(Allergen, self.calc_may_contain)),
            self.calc_ask_staff,
        )

    def set_published(self, summary: Summary):
        self.contains, self.may_contain, self.ask_staff = (
            _sorted(summary.contains),
            _sorted(summary.may_contain),
            summary.ask_staff,
        )

    def set_calculated(self, summary: Summary):
        self.calc_contains = _sorted(summary.contains)
        self.calc_may_contain = _sorted(summary.may_contain)
        self.calc_ask_staff = summary.ask_staff

    def pending(self):
        """(allergens waiting for removal, 'please ask staff' waiting for removal)."""
        return pending_removals(self.published(), self.calculated())

    def pending_labels(self) -> list[str]:
        """Readable list of what waits for approval, in Annex II order."""
        weaker, ask = self.pending()
        return [a.label_en for a in Allergen if a in weaker] + (["please ask staff"] if ask else [])

    @property
    def has_pending(self) -> bool:
        weaker, ask = self.pending()
        return bool(weaker) or ask


def _sorted(allergens) -> list[str]:
    """Allergen codes in Annex II order, so stored lists compare equal when the content does."""
    return [a.value for a in Allergen if a in allergens]
