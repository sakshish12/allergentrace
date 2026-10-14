"""Smoke tests: the application starts, serves its start page and reaches the database."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "AllergenTrace" in response.content.decode()


@pytest.mark.django_db
def test_health_reports_database_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
