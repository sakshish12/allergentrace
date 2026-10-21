from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def page(request, template):
    """Static information pages (privacy policy, terms of use)."""
    return render(request, template, {"contact_email": settings.CONTACT_EMAIL})


def health(request):
    """Used by the hosting platform and by us to check that app and database are up."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
