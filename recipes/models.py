from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from accounts.models import Business
from catalog.models import Equipment, Ingredient


class Recipe(models.Model):
    """A dish on the menu or a sub-recipe (sauce, dough, dressing) used inside other recipes."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="recipes")
    name = models.CharField(_("name"), max_length=120)
    is_dish = models.BooleanField(
        _("served as a dish"),
        default=True,
        help_text=_("Untick for sauces, doughs and other parts that are only used inside dishes."),
    )
    equipment = models.ManyToManyField(
        Equipment, blank=True, related_name="recipes", verbose_name=_("equipment")
    )

    history = HistoricalRecords(m2m_fields=[equipment])

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Component(models.Model):
    """One part of a recipe: either an ingredient or another recipe, never both."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="components")
    # PROTECT: an ingredient or sub-recipe that is still used cannot be deleted by accident.
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT, null=True, blank=True, related_name="uses"
    )
    sub_recipe = models.ForeignKey(
        Recipe, on_delete=models.PROTECT, null=True, blank=True, related_name="used_in"
    )
    quantity = models.DecimalField(_("quantity"), max_digits=8, decimal_places=2, null=True, blank=True)
    unit = models.CharField(_("unit"), max_length=20, blank=True)

    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ingredient__isnull=False, sub_recipe__isnull=True)
                | Q(ingredient__isnull=True, sub_recipe__isnull=False),
                name="component_is_ingredient_xor_recipe",
            ),
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_ingredient_per_recipe"),
            models.UniqueConstraint(fields=["recipe", "sub_recipe"], name="unique_sub_recipe_per_recipe"),
        ]

    def __str__(self):
        return str(self.ingredient or self.sub_recipe)

    @property
    def part(self):
        return self.ingredient or self.sub_recipe
