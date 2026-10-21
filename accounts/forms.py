"""Forms of the accounts app. All validation here runs on the server, whatever the browser checks.

Login and registration answer every problem with one generic message, so an attacker cannot learn
which field was wrong or whether an e-mail address has an account. The field names that failed
are logged for monitoring; the submitted values never are.
"""

import logging
import re

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.validators import EmailValidator
from django.forms.utils import ErrorDict, ErrorList
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from accounts import security
from accounts.models import Role
from config.forms import BootstrapFormMixin

User = get_user_model()
log = logging.getLogger("accounts.security")

LOGIN_ERROR = _("Incorrect email or password")
SIGNUP_ERROR = _(
    "We could not register you with these details. Please check them and try again: a valid e-mail "
    "address, the name of your business, and a password as described below."
)
EMAIL_MAX = 150  # the e-mail is stored as Django username, which holds 150 characters
PASSWORD_MAX = 128  # long enough for any passphrase, short enough to keep hashing cheap
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
# Letters of any language, digits, spaces and the punctuation used in business names.
NAME_PATTERN = re.compile(r"^[\w .,&'’()\-/+!#]+$")


def clean_text(value):
    """Remove HTML (including <script> blocks), control characters and extra spaces."""
    value = re.sub(r"(?is)<(script|style)\b.*?</\1\s*>", "", value)
    return " ".join(CONTROL_CHARS.sub(" ", strip_tags(value)).split())


class EmailField(forms.EmailField):
    """E-mail as login name: trimmed, lower case, at most EMAIL_MAX characters."""

    def __init__(self, **kwargs):
        super().__init__(max_length=EMAIL_MAX, **kwargs)

    def to_python(self, value):
        return super().to_python(value).lower()


class PasswordField(forms.CharField):
    """Passwords are checked for length only and never changed: stripping characters would alter them."""

    def __init__(self, **kwargs):
        super().__init__(max_length=PASSWORD_MAX, strip=False, widget=forms.PasswordInput, **kwargs)


class GenericErrorsMixin:
    """Replace all field errors with one message and log which fields failed."""

    generic_error = SIGNUP_ERROR
    log_event = "signup"

    def full_clean(self):
        super().full_clean()
        if self._errors:
            ip = security.client_ip(self.request) if getattr(self, "request", None) else "-"
            log.warning("%s rejected fields=%s ip=%s", self.log_event, ",".join(sorted(self._errors)), ip)
            self._errors = ErrorDict({forms.forms.NON_FIELD_ERRORS: ErrorList([self.generic_error])})


class NewUserForm(BootstrapFormMixin, forms.Form):
    """E-mail and password of a new user; the e-mail is also the login name."""

    email = EmailField(label=_("E-mail"))
    password1 = PasswordField(
        label=_("Password"),
        help_text=_(
            "At least 8 characters, not only numbers, not a common password and not similar to the e-mail."
        ),
    )
    password2 = PasswordField(label=_("Repeat password"))

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

    def create_user(self, **extra):
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email, email=email, password=self.cleaned_data["password1"], **extra
        )


class SignupForm(GenericErrorsMixin, NewUserForm):
    """US-01. Does not check whether the e-mail is taken: the view handles that without telling."""

    business_name = forms.CharField(label=_("Name of your business"), max_length=120)
    field_order = ["business_name", "email", "password1", "password2"]

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_business_name(self):
        name = clean_text(self.cleaned_data["business_name"])
        if not name or not NAME_PATTERN.fullmatch(name):
            raise forms.ValidationError(_("Invalid business name."))
        return name


class EmailLoginForm(AuthenticationForm):
    """Login with server-side validation, progressive delay and lockout (see accounts.security)."""

    error_messages = {"invalid_login": LOGIN_ERROR, "inactive": LOGIN_ERROR}

    def clean(self):
        email = (self.cleaned_data.get("username") or "").strip().lower()
        password = self.cleaned_data.get("password") or ""
        if not _valid_email(email) or not password or len(password) > PASSWORD_MAX:
            self._fail("invalid format")
        if security.login_blocked(email):
            self._fail("account paused")  # same message as a wrong password, by design
        self.cleaned_data["username"] = email
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            security.record_failure(email, self.request)
            self._fail("wrong credentials")
        security.clear_failures(email)
        return cleaned

    def full_clean(self):
        super().full_clean()
        if self._errors and set(self._errors) != {forms.forms.NON_FIELD_ERRORS}:
            log.warning("login rejected fields=%s ip=%s", ",".join(sorted(self._errors)), self._ip())
            self._errors = ErrorDict({forms.forms.NON_FIELD_ERRORS: ErrorList([LOGIN_ERROR])})

    def _fail(self, reason):
        log.warning("login rejected reason=%s ip=%s", reason, self._ip())
        raise forms.ValidationError(LOGIN_ERROR, code="invalid_login")

    def _ip(self):
        return security.client_ip(self.request) if self.request else "-"


def _valid_email(value):
    try:
        EmailValidator()(value)
    except forms.ValidationError:
        return False
    return len(value) <= EMAIL_MAX


class StaffCreateForm(NewUserForm):
    role = forms.TypedChoiceField(
        label=_("Role"),
        coerce=int,
        choices=[(Role.KITCHEN, Role.KITCHEN.label), (Role.SERVICE, Role.SERVICE.label)],
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            # The owner is logged in, but the message still does not say why the address is refused.
            raise forms.ValidationError(_("An account cannot be created for this e-mail address."))
        return email


class StaffUpdateForm(BootstrapFormMixin, forms.Form):
    role = StaffCreateForm.base_fields["role"]
    is_active = forms.BooleanField(label=_("Account active"), required=False)


class NewPasswordForm(BootstrapFormMixin, SetPasswordForm):
    """Password reset: Django's own checks, hashed with the configured hasher (bcrypt)."""
