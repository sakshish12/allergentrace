from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, ListView, TemplateView

from accounts import security
from accounts.forms import EmailLoginForm, NewPasswordForm, SignupForm, StaffCreateForm, StaffUpdateForm
from accounts.models import Business, Membership, Role
from accounts.permissions import MemberRequiredMixin

User = get_user_model()


@method_decorator(security.rate_limit("login"), name="dispatch")
class LoginView(auth_views.LoginView):
    """At most 10 requests per IP and minute; delay and lockout per account live in EmailLoginForm."""

    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True  # someone already logged in goes straight to the app


class LogoutView(auth_views.LogoutView):
    """Logging out needs a POST (CSRF); typing /logout/ shows a button instead of an error page."""

    http_method_names = ["get", "post", "options"]

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("home")
        return render(request, "accounts/logout_confirm.html")


@method_decorator(sensitive_post_parameters("password1", "password2"), name="dispatch")
@method_decorator(security.rate_limit("signup", methods=("POST",)), name="dispatch")
class SignupView(FormView):
    """US-01: register a business; the owner account is activated through a link sent by e-mail.

    The answer is the same whether or not the e-mail already has an account, so the form cannot be
    used to find out who is registered. The address owner is told by e-mail instead.
    """

    template_name = "accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("signup_done")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "request": self.request}

    @transaction.atomic
    def form_valid(self, form):
        email = form.cleaned_data["email"]
        existing = User.objects.filter(username=email).select_related("membership").first()
        if existing is None:
            user = form.create_user(is_active=False)
            business = Business.objects.create(name=form.cleaned_data["business_name"])
            Membership.objects.create(user=user, business=business, role=Role.OWNER)
            self._send_activation(user)
        else:
            # Hash anyway: the same work as for a new account, so the response time tells nothing.
            make_password(form.cleaned_data["password1"])
            if _pending_owner(existing):
                self._send_activation(existing)
            else:
                send_mail(
                    _("AllergenTrace: someone tried to register with your address"),
                    _(
                        "Hello,\n\nsomeone tried to register a new business on AllergenTrace with this "
                        "e-mail address, which already has an account. If that was you, log in or set a new "
                        "password here:\n%(url)s\n\nIf it was not you, you can ignore this e-mail."
                        "\n\nAllergenTrace"
                    )
                    % {"url": self.request.build_absolute_uri(reverse("password_reset"))},
                    None,
                    [existing.email],
                    fail_silently=True,
                )
        return super().form_valid(form)

    def _send_activation(self, user):
        url = self.request.build_absolute_uri(
            reverse(
                "activate",
                args=[urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)],
            )
        )
        send_mail(
            _("AllergenTrace: confirm your registration"),
            _(
                "Hello,\n\nplease confirm your e-mail address to finish the registration of "
                "%(business)s:\n%(url)s\n\nThe link is valid for 3 days. If you did not register, "
                "you can ignore this e-mail.\n\nAllergenTrace"
            )
            % {"business": user.membership.business, "url": url},
            None,
            [user.email],
            fail_silently=True,
        )


def _pending_owner(user):
    """A registration that was never confirmed (deactivated staff accounts are not reactivated)."""
    membership = getattr(user, "membership", None)
    return not user.is_active and user.last_login is None and membership and membership.role == Role.OWNER


class ActivateView(View):
    """Confirms the e-mail address of a new owner, logs them in and opens the overview."""

    def get(self, request, uidb64, token):
        try:
            user = User.objects.select_related("membership__business").get(pk=urlsafe_base64_decode(uidb64))
        except (User.DoesNotExist, ValueError, OverflowError):
            user = None
        if user is None or not _pending_owner(user) or not default_token_generator.check_token(user, token):
            messages.error(
                request, _("This confirmation link is invalid or has expired. Please register again.")
            )
            return redirect("signup")
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            request,
            _("Welcome! %(business)s is registered. Start with your suppliers and ingredients.")
            % {"business": user.membership.business},
        )
        return redirect("dashboard")


@method_decorator(security.rate_limit("password-reset", methods=("POST",)), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "form.html"
    form_class = NewPasswordForm
    extra_context = {"title": gettext_lazy("Set a new password"), "cancel_url": False}

    def form_valid(self, form):
        security.clear_failures(form.user.username)  # a new password also ends a paused sign-in
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


@method_decorator(sensitive_post_parameters("password1", "password2"), name="dispatch")
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
