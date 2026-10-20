"""Keeps the published declarations in line with the recipes (US-10, US-11)."""

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from simple_history.utils import bulk_create_with_history, bulk_update_with_history

from accounts.models import Role
from allergen_engine.impact import impact
from allergen_engine.policy import merge
from publication.models import PublishedDeclaration
from recipes.repository import declarations_for


@transaction.atomic
def sync(business):
    """Recalculate every recipe, publish additions at once and keep removals until approved (BR-6).

    Returns the impact: {recipe id: Change} for recipes whose calculation changed.
    """
    calculated = {rid: d.summary() for rid, d in declarations_for(business).items()}
    rows = {
        p.recipe_id: p
        for p in PublishedDeclaration.objects.select_for_update().filter(recipe__business=business)
    }
    before = {rid: row.calculated() for rid, row in rows.items()}

    to_create, to_update = [], []
    for rid, summary in calculated.items():
        row = rows.get(rid)
        published = merge(row.published() if row else None, summary)
        if row is None:
            row = PublishedDeclaration(recipe_id=rid)
            to_create.append(row)
        elif (row.published(), row.calculated()) != (published, summary):
            to_update.append(row)
        row.set_published(published)
        row.set_calculated(summary)
    # The *_with_history variants also write the change history (US-12).
    bulk_create_with_history(to_create, PublishedDeclaration)
    bulk_update_with_history(
        to_update,
        PublishedDeclaration,
        ["contains", "may_contain", "ask_staff", "calc_contains", "calc_may_contain", "calc_ask_staff"],
    )
    return impact(before, calculated)


def approve(publication: PublishedDeclaration, user):
    """The owner accepts the calculated declaration, including the removals."""
    publication.set_published(publication.calculated())
    publication.approved_at, publication.approved_by = timezone.now(), user
    publication.save()


def pending_for(business):
    """Declarations whose removals wait for the owner's approval, by recipe name."""
    rows = PublishedDeclaration.objects.filter(recipe__business=business).select_related("recipe")
    return [row for row in rows.order_by("recipe__name") if row.has_pending]


def notify_approval_needed(business, changes, approvals_url, actor):
    """US-20: one e-mail per change that leaves removals waiting for approval.

    Sent to the owners of the business, except the person who made the change: they already see
    the impact on the next page.
    """
    waiting = [rid for rid, change in changes.items() if change.removed or change.ask_staff_removed]
    if not waiting:
        return
    owners = [
        m.user.email
        for m in business.memberships.filter(role=Role.OWNER, user__is_active=True).select_related("user")
        if m.user.email and m.user != actor
    ]
    if not owners:
        return
    names = sorted(business.recipes.filter(id__in=waiting).values_list("name", flat=True))
    body = (
        f"Hello,\n\n{actor.email} changed recipes or ingredients of {business.name}. "
        "Guests still see the old allergen information for these recipes until you approve the removal:\n\n"
        + "".join(f"- {name}\n" for name in names)
        + f"\nReview and approve: {approvals_url}\n\nAllergenTrace"
    )
    send_mail(f"Approval needed: {', '.join(names)}"[:150], body, None, owners, fail_silently=True)
