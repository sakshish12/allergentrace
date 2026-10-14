from django import forms
from django.utils.translation import gettext_lazy as _

from allergen_engine.graph import would_create_cycle
from catalog.models import Equipment, Ingredient
from config.forms import BootstrapFormMixin
from recipes.models import Component, Recipe
from recipes.repository import DjangoRecipeRepository


class RecipeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ["name", "is_dish"]

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)


class ComponentForm(BootstrapFormMixin, forms.Form):
    """Adds an ingredient ("i:<id>") or a sub-recipe ("r:<id>") to a recipe."""

    part = forms.ChoiceField(label=_("Ingredient or recipe"))
    quantity = forms.DecimalField(
        label=_("Quantity"), required=False, min_value=0, max_digits=8, decimal_places=2
    )
    unit = forms.CharField(label=_("Unit (g, ml, pieces …)"), required=False, max_length=20)

    def __init__(self, *args, recipe, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipe = recipe
        used = set(recipe.components.values_list("ingredient_id", "sub_recipe_id"))
        used_ingredients = {i for i, _ in used if i}
        used_recipes = {r for _, r in used if r}
        ingredients = Ingredient.objects.filter(business=recipe.business).exclude(id__in=used_ingredients)
        recipes = Recipe.objects.filter(business=recipe.business).exclude(id__in=used_recipes | {recipe.id})
        self.fields["part"].choices = [
            ("", _("Choose …")),
            (_("Ingredients"), [(f"i:{i.id}", i.name) for i in ingredients]),
            (_("Recipes (sauces, doughs …)"), [(f"r:{r.id}", r.name) for r in recipes]),
        ]

    def clean_part(self):
        kind, _sep, pk = self.cleaned_data["part"].partition(":")
        if kind == "r":
            # BR-5: a recipe must never contain itself, directly or through other recipes.
            edges = DjangoRecipeRepository(self.recipe.business).edges()
            if would_create_cycle(edges, self.recipe.id, int(pk)):
                sub = Recipe.objects.get(pk=pk)
                raise forms.ValidationError(
                    _("“%(sub)s” already uses “%(recipe)s”, so it cannot also be a part of it.")
                    % {"sub": sub, "recipe": self.recipe}
                )
        return kind, int(pk)

    def save(self):
        kind, pk = self.cleaned_data["part"]
        return Component.objects.create(
            recipe=self.recipe,
            ingredient_id=pk if kind == "i" else None,
            sub_recipe_id=pk if kind == "r" else None,
            quantity=self.cleaned_data["quantity"],
            unit=self.cleaned_data["unit"],
        )


class RecipeEquipmentForm(forms.ModelForm):
    """US-05/US-09: the equipment a recipe is prepared with."""

    class Meta:
        model = Recipe
        fields = ["equipment"]
        widgets = {"equipment": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipment"].queryset = Equipment.objects.filter(business=self.instance.business)
        self.fields["equipment"].label = _("Prepared with")
