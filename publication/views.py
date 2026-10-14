from io import BytesIO

import segno
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from accounts.models import Role
from accounts.permissions import MemberRequiredMixin
from allergen_engine.model import Allergen
from publication.history import entries
from publication.models import Menu, PublishedDeclaration
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


def _guest_url(request, menu):
    return request.build_absolute_uri(reverse("guest_menu", args=[menu.qr_token]))


class MenuView(MemberRequiredMixin, TemplateView):
    """US-13: the owner chooses the dishes on the public menu; everyone finds link, QR code and PDF here."""

    template_name = "publication/menu.html"

    def get_context_data(self, **kwargs):
        menu = Menu.for_business(self.request.business)
        return super().get_context_data(
            menu=menu,
            dishes=self.request.business.recipes.filter(is_dish=True).order_by("name"),
            on_menu=set(menu.dishes.values_list("pk", flat=True)),
            guest_url=_guest_url(self.request, menu),
            **kwargs,
        )

    def post(self, request):
        if request.role < Role.OWNER:
            raise PermissionDenied
        menu = Menu.for_business(request.business)
        ids = [i for i in request.POST.getlist("dishes") if i.isdigit()]
        # Only dishes of this business can be put on its menu, whatever the form sends.
        menu.dishes.set(request.business.recipes.filter(is_dish=True, pk__in=ids))
        messages.success(request, _("Menu saved. Guests see the selected dishes."))
        return redirect("menu")


class MenuQrView(MemberRequiredMixin, View):
    """US-17: QR code with the public link, as PNG for print shops or SVG for any size."""

    def get(self, request, kind):
        menu = Menu.for_business(request.business)
        buffer = BytesIO()
        segno.make(_guest_url(request, menu), error="m").save(buffer, kind=kind, scale=10, border=4)
        response = HttpResponse(
            buffer.getvalue(), content_type="image/png" if kind == "png" else "image/svg+xml"
        )
        response["Content-Disposition"] = f'attachment; filename="menu-qr-code.{kind}"'
        return response


class MenuPdfView(MemberRequiredMixin, View):
    """US-16: written allergen list of all menu dishes, from the published declarations only."""

    def get(self, request):
        from weasyprint import HTML  # heavy import, only loaded when a PDF is requested

        menu = Menu.for_business(request.business)
        rows = [(dish, summary, [summary.rank(a) for a in Allergen]) for dish, summary in menu.entries()]
        html = render_to_string(
            "publication/menu_pdf.html",
            {
                "business": request.business,
                "rows": rows,
                "allergens": list(Allergen),
                "today": timezone.localdate(),
            },
        )
        pdf = HTML(string=html, base_url=str(settings.BASE_DIR / "static")).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="allergen-list.pdf"'
        return response


def guest_menu(request, token, lang=None):
    """US-14 and US-15: the public menu with the guest's allergen filter. No login, no cookies."""
    menu = get_object_or_404(Menu.objects.select_related("business"), qr_token=token)
    if lang is None:  # the QR code link: use the browser's language, German or English
        lang = "de" if translation.get_language_from_request(request) == "de" else "en"
    label = (lambda a: a.label_de) if lang == "de" else (lambda a: a.label_en)

    codes = {a.value for a in Allergen}
    avoid = frozenset(Allergen(c) for c in request.GET.getlist("avoid") if c in codes)
    show_traces = request.GET.get("traces") == "1"
    dishes, hidden = [], 0
    for dish, summary in menu.entries():
        if summary.hidden_for(avoid, show_traces):
            hidden += 1
            continue
        dishes.append(
            {
                "name": dish.name,
                "contains": [label(a) for a in Allergen if a in summary.contains],
                "traces": [label(a) for a in Allergen if a in summary.may_contain],
                "ask_staff": summary.ask_staff,
            }
        )
    with translation.override(lang):
        return render(
            request,
            "publication/guest_menu.html",
            {
                "menu": menu,
                "lang": lang,
                "dishes": dishes,
                "hidden": hidden,
                "avoid": avoid,
                "show_traces": show_traces,
                "allergens": [(a.value, label(a)) for a in Allergen],
                "query": request.GET.urlencode(),
            },
        )
