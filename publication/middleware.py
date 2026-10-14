from allergen_engine.model import Allergen
from publication.services import sync
from recipes.models import Recipe

REDIRECTS = {301, 302, 303}


class PublicationSyncMiddleware:
    """After every successful change in the back office, recalculate and publish (US-10, US-11).

    Successful form posts end in a redirect, so a POST under /app/ answered with a redirect is a
    saved change. The impact is kept in the session and shown once on the next page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "POST"
            and response.status_code in REDIRECTS
            and request.path.startswith("/app/")
        ):
            membership = getattr(request.user, "membership", None) if request.user.is_authenticated else None
            if membership is not None:
                changes = sync(membership.business)
                if changes:
                    request.session["impact"] = describe(changes)
        return response


def describe(changes):
    """A JSON-friendly description of the impact, sorted by recipe name, for the session."""
    names = dict(Recipe.objects.filter(id__in=changes).values_list("id", "name"))
    return [
        {
            "recipe_id": rid,
            "recipe": names[rid],
            "added": _labels(change.added),
            "removed": _labels(change.removed),
            "ask_staff_added": change.ask_staff_added,
            "ask_staff_removed": change.ask_staff_removed,
        }
        for rid, change in sorted(changes.items(), key=lambda item: names[item[0]])
    ]


def _labels(allergens):
    return [a.label_en for a in Allergen if a in allergens]
