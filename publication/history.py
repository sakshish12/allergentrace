"""Read-only change log of one business (US-12), built from the django-simple-history tables."""

from heapq import nlargest
from itertools import chain

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from allergen_engine.model import Allergen
from catalog.models import Equipment, Ingredient, Supplier
from publication.models import PublishedDeclaration
from recipes.models import Component, Recipe

ACTIONS = {"+": _("created"), "~": _("changed"), "-": _("deleted")}
LIMIT = 150
HIDDEN_FIELDS = {"updated_at", "approved_at"}
CODES = {a.value: a.label_en for a in Allergen}


def entries(business):
    """The latest changes of the business, newest first."""
    recipe_ids = set(Recipe.history.filter(business_id=business.id).values_list("id", flat=True))
    sources = [
        (_("Supplier"), Supplier.history.filter(business_id=business.id)),
        (_("Ingredient"), Ingredient.history.filter(business_id=business.id)),
        (_("Equipment"), Equipment.history.filter(business_id=business.id)),
        (_("Recipe"), Recipe.history.filter(business_id=business.id)),
        (_("Recipe part"), Component.history.filter(recipe_id__in=recipe_ids)),
        (_("Published declaration"), PublishedDeclaration.history.filter(recipe_id__in=recipe_ids)),
    ]
    latest = chain.from_iterable(
        ((kind, record) for record in qs.select_related("history_user").order_by("-history_date")[:LIMIT])
        for kind, qs in sources
    )
    return [
        _describe(kind, record)
        for kind, record in nlargest(LIMIT, latest, key=lambda item: item[1].history_date)
    ]


def _describe(kind, record):
    return {
        "date": record.history_date,
        "user": record.history_user.email if record.history_user else _("system"),
        "kind": kind,
        "name": _name(record),
        "action": ACTIONS[record.history_type],
        "changes": _changes(record) if record.history_type == "~" else [],
    }


def _name(record):
    try:
        if isinstance(record.instance, Component):
            return f"{record.instance.part} → {record.instance.recipe}"
        return str(record.instance)
    except ObjectDoesNotExist:  # the related recipe or ingredient was deleted later
        return _("(deleted)")


def _changes(record):
    previous = record.prev_record
    if previous is None:
        return []
    rows = []
    for c in record.diff_against(previous).changes:
        if c.field in HIDDEN_FIELDS:
            continue
        field = record.instance._meta.get_field(c.field)
        old, new = (_related(field, c.old), _related(field, c.new)) if field.many_to_one else (c.old, c.new)
        rows.append({"field": field.verbose_name, "old": _value(old), "new": _value(new)})
    return rows


def _related(field, pk):
    """A foreign key is stored as an id; the history shows the name (e.g. the approving user's e-mail)."""
    if pk is None:
        return None
    obj = field.related_model._default_manager.filter(pk=pk).first()
    return str(obj) if obj else _("(deleted)")


def _value(value):
    if isinstance(value, list):
        if value and isinstance(value[0], dict):  # many-to-many, e.g. equipment of a recipe
            ids = [v.get("equipment") for v in value]
            return ", ".join(Equipment.objects.filter(id__in=ids).values_list("name", flat=True)) or "–"
        return ", ".join(CODES.get(v, str(v)) for v in value) or "–"
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    return value if value not in (None, "") else "–"
