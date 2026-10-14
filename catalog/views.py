from django import forms
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.models import Role
from accounts.permissions import BusinessFormMixin, BusinessScopedMixin
from catalog.forms import IngredientForm, SupplierForm
from catalog.models import Ingredient, Supplier


class SavedMessageMixin:
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("“%(name)s” saved.") % {"name": self.object})
        return response


class DeleteConfirmView(BusinessScopedMixin, DeleteView):
    min_role = Role.KITCHEN
    template_name = "confirm_delete.html"
    form_class = forms.Form

    def form_valid(self, form):
        name = str(self.object)
        response = super().form_valid(form)
        messages.success(self.request, _("“%(name)s” deleted.") % {"name": name})
        return response


# US-03: suppliers


class SupplierListView(BusinessScopedMixin, ListView):
    model = Supplier
    template_name = "catalog/supplier_list.html"


class SupplierCreateView(SavedMessageMixin, BusinessFormMixin, CreateView):
    min_role = Role.KITCHEN
    model = Supplier
    form_class = SupplierForm
    template_name = "form.html"
    success_url = reverse_lazy("supplier_list")
    extra_context = {"title": _("New supplier")}


class SupplierUpdateView(SavedMessageMixin, BusinessFormMixin, UpdateView):
    min_role = Role.KITCHEN
    model = Supplier
    form_class = SupplierForm
    template_name = "form.html"
    success_url = reverse_lazy("supplier_list")


class SupplierDeleteView(DeleteConfirmView):
    model = Supplier
    success_url = reverse_lazy("supplier_list")


# US-04: ingredients


class IngredientListView(BusinessScopedMixin, ListView):
    model = Ingredient
    template_name = "catalog/ingredient_list.html"

    def get_queryset(self):
        return super().get_queryset().select_related("supplier")


class IngredientCreateView(SavedMessageMixin, BusinessFormMixin, CreateView):
    min_role = Role.KITCHEN
    model = Ingredient
    form_class = IngredientForm
    template_name = "catalog/ingredient_form.html"
    success_url = reverse_lazy("ingredient_list")
    extra_context = {"title": _("New ingredient")}


class IngredientUpdateView(SavedMessageMixin, BusinessFormMixin, UpdateView):
    min_role = Role.KITCHEN
    model = Ingredient
    form_class = IngredientForm
    template_name = "catalog/ingredient_form.html"
    success_url = reverse_lazy("ingredient_list")


class IngredientDeleteView(DeleteConfirmView):
    model = Ingredient
    success_url = reverse_lazy("ingredient_list")
