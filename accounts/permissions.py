"""Access control used by every back-office view.

Two rules are enforced here and nowhere else:
1. A user only works with data of their own business (tenancy, NFR-02).
2. A user only does what their role allows (Owner ⊃ Kitchen ⊃ Service).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from accounts.models import Role


class MemberRequiredMixin(LoginRequiredMixin):
    min_role = Role.SERVICE

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        membership = getattr(request.user, "membership", None)
        if membership is None or membership.role < self.min_role:
            raise PermissionDenied
        request.business = membership.business
        request.role = membership.role
        return super().dispatch(request, *args, **kwargs)


class BusinessScopedMixin(MemberRequiredMixin):
    """For views of models that have a `business` field."""

    def get_queryset(self):
        # Objects of other businesses are invisible, so their URLs answer 404.
        return super().get_queryset().filter(business=self.request.business)


class BusinessFormMixin(BusinessScopedMixin):
    """For create and update views: the form gets the business, the new object is assigned to it."""

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "business": self.request.business}

    def form_valid(self, form):
        form.instance.business = self.request.business
        return super().form_valid(form)
