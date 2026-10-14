from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from allergen_engine.model import Allergen
from catalog.models import ALLERGEN_CHOICES, Ingredient, Supplier
from config.forms import BootstrapFormMixin


class SupplierForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "phone", "email"]
        widgets = {"phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"})}

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)


class IngredientForm(BootstrapFormMixin, forms.ModelForm):
    contains = forms.MultipleChoiceField(
        label=_("Contains"), choices=ALLERGEN_CHOICES, widget=forms.CheckboxSelectMultiple, required=False
    )
    may_contain = forms.MultipleChoiceField(
        label=_("May contain (traces)"),
        choices=ALLERGEN_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    data_complete = forms.BooleanField(
        label=_("I have checked these allergens against the product specification or label."), required=False
    )

    class Meta:
        model = Ingredient
        fields = ["name", "product_name", "supplier", "contains", "may_contain"]

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.business = business  # needed by Ingredient.clean() for the supplier check
        self.fields["supplier"].queryset = Supplier.objects.filter(business=business)
        self.fields["supplier"].empty_label = _("No supplier")
        self.has_suppliers = self.fields["supplier"].queryset.exists()
        self.initial["data_complete"] = self.instance.status == Ingredient.Status.COMPLETE

    def allergen_rows(self):
        """One row per allergen with its two checkboxes, for the table in the template."""
        return zip(Allergen, self["contains"], self["may_contain"], strict=True)

    def save(self, commit=True):
        ingredient = super().save(commit=False)
        if not self.cleaned_data["data_complete"]:
            ingredient.status, ingredient.verified_on = Ingredient.Status.UNKNOWN, None
        elif ingredient.status == Ingredient.Status.UNKNOWN or {"contains", "may_contain"} & set(
            self.changed_data
        ):
            # The verification date moves only when someone actually (re)checks the data.
            ingredient.status, ingredient.verified_on = Ingredient.Status.COMPLETE, timezone.localdate()
        if commit:
            ingredient.save()
        return ingredient
