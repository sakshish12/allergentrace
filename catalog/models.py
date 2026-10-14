import re

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Business
from allergen_engine.model import Allergen

ALLERGEN_CHOICES = [(a.value, a.label_en) for a in Allergen]


class Supplier(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="suppliers")
    name = models.CharField(_("name"), max_length=120)
    contact_person = models.CharField(_("contact person"), max_length=120, blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def phone_href(self):
        """tel: link for phones; keeps only digits and a leading plus."""
        digits = re.sub(r"[^\d+]", "", self.phone)
        return f"tel:{digits}" if digits else ""


class Ingredient(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = "unknown", _("Unknown")
        COMPLETE = "complete", _("Complete")

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="ingredients")
    name = models.CharField(_("name"), max_length=120)
    product_name = models.CharField(_("product name"), max_length=200, blank=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingredients",
        verbose_name=_("supplier"),
    )
    contains = ArrayField(models.CharField(max_length=20, choices=ALLERGEN_CHOICES), default=list, blank=True)
    may_contain = ArrayField(
        models.CharField(max_length=20, choices=ALLERGEN_CHOICES), default=list, blank=True
    )
    # BR-4: new ingredients are "unknown" until a person confirms the data.
    status = models.CharField(_("data status"), max_length=10, choices=Status.choices, default=Status.UNKNOWN)
    verified_on = models.DateField(_("verified on"), null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def contains_labels(self):
        return [Allergen(code).label_en for code in self.contains]

    def may_contain_labels(self):
        return [Allergen(code).label_en for code in self.may_contain]

    def clean(self):
        overlap = set(self.contains) & set(self.may_contain)
        if overlap:
            names = ", ".join(Allergen(code).label_en for code in sorted(overlap))
            raise ValidationError(_("An allergen cannot be both 'contains' and 'may contain': %s") % names)
        if self.supplier_id and self.supplier.business_id != self.business_id:
            raise ValidationError(_("The supplier belongs to another business."))
