from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.IntegerChoices):
    """Higher values include the rights of lower ones: Owner ⊃ Kitchen ⊃ Service."""

    SERVICE = 1, _("Service")
    KITCHEN = 2, _("Kitchen")
    OWNER = 3, _("Owner")


class Business(models.Model):
    """A food business (tenant). All business data hangs off this model."""

    name = models.CharField(_("name"), max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    # shortcut: one business per user (OneToOne instead of the 1..* in the class diagram);
    # small businesses do not share staff accounts. Change to a ForeignKey if that is needed.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membership")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    role = models.PositiveSmallIntegerField(_("role"), choices=Role.choices)

    def __str__(self):
        return f"{self.user} ({self.get_role_display()}, {self.business})"

    @property
    def is_owner(self):
        return self.role == Role.OWNER

    @property
    def can_edit(self):
        return self.role >= Role.KITCHEN
