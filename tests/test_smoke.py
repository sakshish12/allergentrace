"""Smoke tests: the application starts, serves its start page and reaches the database."""

from pathlib import Path

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "AllergenTrace" in response.content.decode()


@pytest.mark.django_db
def test_german_browser_gets_one_consistent_language(client):
    # The back office is English only; Django's own German strings must not leak in (see US-14).
    html = client.get(reverse("signup"), HTTP_ACCEPT_LANGUAGE="de-DE,de;q=0.9").content.decode()
    assert "Password" in html and "Passwort" not in html


@pytest.mark.django_db
def test_health_reports_database_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_apps_only_depend_downwards():
    """Building block view: publication -> recipes -> catalog -> accounts, never the other way."""
    root = Path(__file__).resolve().parent.parent
    forbidden = {
        "accounts": ("catalog", "recipes", "publication"),
        "catalog": ("recipes", "publication"),
        "recipes": ("publication",),
    }
    for app, uppers in forbidden.items():
        for source in (root / app).rglob("*.py"):
            text = source.read_text(encoding="utf-8")
            for upper in uppers:
                assert f"from {upper}" not in text and f"import {upper}" not in text, (source, upper)
