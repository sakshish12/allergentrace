from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import Role
from accounts.permissions import BusinessFormMixin, BusinessScopedMixin, MemberRequiredMixin
from catalog.views import DeleteConfirmView, SavedMessageMixin
from recipes.example_data import load_example_data
from recipes.forms import ComponentForm, RecipeForm
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
        if self.request.role >= Role.KITCHEN:
            context["component_form"] = component_form or ComponentForm(recipe=recipe)
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
