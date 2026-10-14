from publication.services import pending_for


def impact(request):
    """The impact of the last change, shown once at the top of the next page (US-10)."""
    if not hasattr(request, "session"):
        return {}
    return {"impact": request.session.pop("impact", None)}


def pending_approvals(request):
    """Number of declarations waiting for the owner, for the navigation badge."""
    user = getattr(request, "user", None)
    membership = getattr(user, "membership", None) if user is not None and user.is_authenticated else None
    if membership is None:
        return {}
    return {"pending_count": len(pending_for(membership.business))}
