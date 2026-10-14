from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from accounts.models import Role
from config.forms import BootstrapFormMixin

User = get_user_model()


class NewUserForm(BootstrapFormMixin, forms.Form):
    """E-mail and password of a new user; the e-mail is also the login name."""

    email = forms.EmailField(label=_("E-mail"))
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label=_("Repeat password"), widget=forms.PasswordInput, strip=False)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(_("An account with this e-mail already exists."))
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", _("The passwords do not match."))
            else:
                try:
                    password_validation.validate_password(p1, User(username=cleaned.get("email")))
                except forms.ValidationError as error:
                    self.add_error("password1", error)
        return cleaned

    def create_user(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(username=email, email=email, password=self.cleaned_data["password1"])


class EmailLoginForm(AuthenticationForm):
    def clean_username(self):
        # E-mails are stored in lower case (see NewUserForm.clean_email).
        return self.cleaned_data["username"].lower()


class SignupForm(NewUserForm):
    business_name = forms.CharField(label=_("Name of your business"), max_length=120)
    field_order = ["business_name", "email", "password1", "password2"]


class StaffCreateForm(NewUserForm):
    role = forms.TypedChoiceField(
        label=_("Role"),
        coerce=int,
        choices=[(Role.KITCHEN, Role.KITCHEN.label), (Role.SERVICE, Role.SERVICE.label)],
    )


class StaffUpdateForm(BootstrapFormMixin, forms.Form):
    role = StaffCreateForm.base_fields["role"]
    is_active = forms.BooleanField(label=_("Account active"), required=False)
