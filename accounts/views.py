from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.generic import FormView, ListView, TemplateView

from accounts.forms import SignupForm, StaffCreateForm, StaffUpdateForm
from accounts.models import Business, Membership, Role
from accounts.permissions import MemberRequiredMixin


class SignupView(FormView):
    """US-01: register a business together with its owner account."""

    template_name = "accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        user = form.create_user()
        business = Business.objects.create(name=form.cleaned_data["business_name"])
        Membership.objects.create(user=user, business=business, role=Role.OWNER)
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            self.request,
            _("Welcome! %(business)s is registered. Start with your suppliers and ingredients.")
            % {"business": business},
        )
        return super().form_valid(form)


class DashboardView(MemberRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        ingredients = self.request.business.ingredients
        return super().get_context_data(
            ingredient_count=ingredients.count(),
            unknown_count=ingredients.filter(status="unknown").count(),
            supplier_count=self.request.business.suppliers.count(),
            recipe_count=self.request.business.recipes.count(),
            equipment_count=self.request.business.equipment.count(),
            **kwargs,
        )


class StaffListView(MemberRequiredMixin, ListView):
    """US-02: the owner sees and manages the accounts of the business."""

    min_role = Role.OWNER
    template_name = "accounts/staff_list.html"

    def get_queryset(self):
        return (
            Membership.objects.filter(business=self.request.business)
            .select_related("user")
            .order_by("-role", "user__username")
        )


class StaffCreateView(MemberRequiredMixin, FormView):
    min_role = Role.OWNER
    template_name = "form.html"
    form_class = StaffCreateForm
    success_url = reverse_lazy("staff_list")
    extra_context = {"title": gettext_lazy("New staff account")}

    @transaction.atomic
    def form_valid(self, form):
        user = form.create_user()
        Membership.objects.create(user=user, business=self.request.business, role=form.cleaned_data["role"])
        messages.success(self.request, _("Account for %(email)s created.") % {"email": user.email})
        return super().form_valid(form)


class StaffUpdateView(MemberRequiredMixin, FormView):
    min_role = Role.OWNER
    template_name = "form.html"
    form_class = StaffUpdateForm
    success_url = reverse_lazy("staff_list")

    def get_membership(self):
        # Owners are excluded, so the owner cannot lock themselves out.
        return get_object_or_404(
            Membership.objects.select_related("user"),
            pk=self.kwargs["pk"],
            business=self.request.business,
            role__lt=Role.OWNER,
        )

    def get_initial(self):
        membership = self.get_membership()
        return {"role": membership.role, "is_active": membership.user.is_active}

    def get_context_data(self, **kwargs):
        return super().get_context_data(title=self.get_membership().user.email, **kwargs)

    def form_valid(self, form):
        membership = self.get_membership()
        membership.role = form.cleaned_data["role"]
        membership.save(update_fields=["role"])
        membership.user.is_active = form.cleaned_data["is_active"]
        membership.user.save(update_fields=["is_active"])
        messages.success(self.request, _("Account updated."))
        return super().form_valid(form)
