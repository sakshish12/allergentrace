import secrets

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from accounts.models import Business
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


def _new_token():
    # 72 random bits: the public link cannot be guessed from the business name or an id.
    return secrets.token_urlsafe(9)


class Menu(models.Model):
    """The public menu of a business (US-13, US-14). Guests reach it by the token in the QR code."""

    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="menu")
    qr_token = models.CharField(max_length=20, unique=True, default=_new_token, editable=False)
    dishes = models.ManyToManyField(Recipe, blank=True, related_name="menus")

    def __str__(self):
        return str(self.business)

    @classmethod
    def for_business(cls, business):
        menu, created = cls.objects.get_or_create(business=business)
        if created:  # a new menu starts with every dish; the owner switches off what is not served
            menu.dishes.set(business.recipes.filter(is_dish=True))
        return menu

    def entries(self):
        """Dishes on the menu with what guests may see. Reads only published declarations (BR-6)."""
        return [
            (dish, dish.publication.published() if hasattr(dish, "publication") else UNKNOWN)
            for dish in self.dishes.filter(is_dish=True).select_related("publication").order_by("name")
        ]


# A dish that was never calculated is shown as 'please ask staff', never as allergen-free.
UNKNOWN = Summary(frozenset(), frozenset(), ask_staff=True)
