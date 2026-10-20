from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from simple_history.utils import bulk_create_with_history

from accounts.models import Role
from accounts.permissions import BusinessFormMixin, BusinessScopedMixin, MemberRequiredMixin
from catalog.views import DeleteConfirmView, SavedMessageMixin
from recipes.example_data import load_example_data
from recipes.forms import ComponentForm, RecipeEquipmentForm, RecipeForm
from recipes.models import Component, Recipe
from recipes.repository import declarations_for


class RecipeListView(BusinessScopedMixin, ListView):
    """Dishes and sub-recipes with their calculated allergens (US-07)."""

    model = Recipe
    template_name = "recipes/recipe_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        declarations = declarations_for(self.request.business)
        rows = [(recipe, declarations[recipe.id]) for recipe in context["object_list"]]
        context["dishes"] = [row for row in rows if row[0].is_dish]
        context["parts"] = [row for row in rows if not row[0].is_dish]
        return context


class RecipeDetailView(BusinessScopedMixin, DetailView):
    """Components and the declaration with an explanation for every allergen (US-06, US-08).

    A POST to this page adds a component (kitchen staff and owners only).
    """

    model = Recipe
    template_name = "recipes/recipe_detail.html"

    def get_context_data(self, component_form=None, **kwargs):
        recipe = self.object
        context = super().get_context_data(**kwargs)
        context["declaration"] = declarations_for(self.request.business)[recipe.id]
        context["components"] = recipe.components.select_related("ingredient", "sub_recipe").order_by(
            "sub_recipe__name", "ingredient__name"
        )
        context["used_in"] = Recipe.objects.filter(components__sub_recipe=recipe).distinct()
        context["equipment"] = recipe.equipment.all()
        context["publication"] = getattr(recipe, "publication", None)
        if self.request.role >= Role.KITCHEN:
            context["component_form"] = component_form or ComponentForm(recipe=recipe)
            context["equipment_form"] = RecipeEquipmentForm(instance=recipe)
        return context

    def post(self, request, pk):
        if request.role < Role.KITCHEN:
            raise PermissionDenied
        self.object = self.get_object()
        form = ComponentForm(request.POST, recipe=self.object)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(component_form=form))
        component = form.save()
        messages.success(request, _("“%(part)s” added.") % {"part": component})
        return redirect("recipe_detail", pk=pk)


class RecipeCreateView(SavedMessageMixin, BusinessFormMixin, CreateView):
    min_role = Role.KITCHEN
    model = Recipe
    form_class = RecipeForm
    template_name = "form.html"
    success_url = reverse_lazy("recipe_list")  # used by Cancel; after saving we go to the recipe
    extra_context = {"title": gettext_lazy("New recipe")}

    def get_success_url(self):
        return reverse("recipe_detail", args=[self.object.pk])


class RecipeUpdateView(SavedMessageMixin, BusinessFormMixin, UpdateView):
    min_role = Role.KITCHEN
    model = Recipe
    form_class = RecipeForm
    template_name = "form.html"
    success_url = reverse_lazy("recipe_list")

    def get_success_url(self):
        return reverse("recipe_detail", args=[self.object.pk])


class RecipeDeleteView(DeleteConfirmView):
    model = Recipe
    success_url = reverse_lazy("recipe_list")


class ComponentRemoveView(MemberRequiredMixin, View):
    min_role = Role.KITCHEN
    http_method_names = ["post"]

    def post(self, request, pk, component_pk):
        component = get_object_or_404(
            Component, pk=component_pk, recipe_id=pk, recipe__business=request.business
        )
        name = str(component)
        component.delete()
        messages.success(request, _("“%(part)s” removed.") % {"part": name})
        return redirect("recipe_detail", pk=pk)


class RecipeEquipmentView(MemberRequiredMixin, View):
    min_role = Role.KITCHEN
    http_method_names = ["post"]

    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, business=request.business)
        form = RecipeEquipmentForm(request.POST, instance=recipe)
        if form.is_valid():  # the choices only contain the business's own equipment
            form.save()
            messages.success(request, _("Equipment saved."))
        else:
            messages.error(request, _("The equipment could not be saved."))
        return redirect("recipe_detail", pk=pk)


class ExampleDataView(MemberRequiredMixin, View):
    """Fills the business with example suppliers, ingredients and recipes (POST only, owner only)."""

    min_role = Role.OWNER
    http_method_names = ["post"]

    def post(self, request):
        ingredients, recipes = load_example_data(request.business)
        if ingredients or recipes:
            messages.success(
                request,
                _(
                    "Example data added: %(ingredients)d ingredients and %(recipes)d recipes. Check the "
                    "ingredients against your own product labels before you use them for guests."
                )
                % {"ingredients": ingredients, "recipes": recipes},
            )
        else:
            messages.info(request, _("The example data is already there."))
        return redirect("recipe_list")


class RecipeCopyView(MemberRequiredMixin, View):
    """US-19: a copy with the same parts and equipment, opened for renaming."""

    min_role = Role.KITCHEN
    http_method_names = ["post"]

    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk, business=request.business)
        taken = set(request.business.recipes.values_list("name", flat=True))
        name, n = _("%(name)s (copy)") % {"name": recipe.name[:100]}, 2
        while name in taken:
            name, n = _("%(name)s (copy %(n)d)") % {"name": recipe.name[:100], "n": n}, n + 1
        copy = Recipe.objects.create(business=request.business, name=name, is_dish=recipe.is_dish)
        bulk_create_with_history(
            [
                Component(
                    recipe=copy,
                    ingredient_id=c.ingredient_id,
                    sub_recipe_id=c.sub_recipe_id,
                    quantity=c.quantity,
                    unit=c.unit,
                )
                for c in recipe.components.all()
            ],
            Component,
        )
        copy.equipment.set(recipe.equipment.all())
        messages.success(request, _("Copy created. Give it a new name."))
        return redirect("recipe_update", pk=copy.pk)


def dishes_by_ingredient(business):
    """{ingredient id: dishes that use it at any depth}, following sub-recipes (no cycles, BR-5)."""
    parts = {}
    for recipe_id, ingredient_id, sub_id in Component.objects.filter(recipe__business=business).values_list(
        "recipe_id", "ingredient_id", "sub_recipe_id"
    ):
        parts.setdefault(recipe_id, []).append((ingredient_id, sub_id))

    def ingredients(recipe_id):
        found = set()
        for ingredient_id, sub_id in parts.get(recipe_id, ()):
            found |= {ingredient_id} if ingredient_id else ingredients(sub_id)
        return found

    result = {}
    for dish in business.recipes.filter(is_dish=True).order_by("name"):
        for ingredient_id in ingredients(dish.id):
            result.setdefault(ingredient_id, []).append(dish)
    return result


class UnknownIngredientsView(MemberRequiredMixin, TemplateView):
    """US-18: ingredients whose allergen data is not checked yet, with whom to ask and what it affects."""

    template_name = "recipes/unknown_ingredients.html"

    def get_context_data(self, **kwargs):
        business = self.request.business
        dishes = dishes_by_ingredient(business)
        unknown = business.ingredients.filter(status="unknown").select_related("supplier").order_by("name")
        return super().get_context_data(rows=[(i, dishes.get(i.id, [])) for i in unknown], **kwargs)
