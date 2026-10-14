from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from accounts.models import Role
from accounts.permissions import MemberRequiredMixin
from publication.history import entries
from publication.models import PublishedDeclaration
from publication.services import approve, pending_for


class ApprovalListView(MemberRequiredMixin, TemplateView):
    """US-11: removals that wait for the owner. Kitchen and service staff can see, not approve."""

    template_name = "publication/approvals.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(rows=pending_for(self.request.business), **kwargs)


class ApproveView(MemberRequiredMixin, View):
    min_role = Role.OWNER
    http_method_names = ["post"]

    def post(self, request, pk=None):
        if pk is None:  # "approve all"
            rows = pending_for(request.business)
        else:
            rows = [get_object_or_404(PublishedDeclaration, pk=pk, recipe__business=request.business)]
        for row in rows:
            approve(row, request.user)
        if rows:
            messages.success(request, _("Approved. Guests now see the updated declaration."))
        next_url = request.POST.get("next", "")
        # Only return to pages of this site (no open redirect).
        if url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect("approvals")


class HistoryView(MemberRequiredMixin, TemplateView):
    """US-12: who changed what and when. Read-only by design."""

    template_name = "publication/history.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(entries=entries(self.request.business), **kwargs)
