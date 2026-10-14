import pytest
from django.contrib.auth import get_user_model

from accounts.models import Business, Membership, Role


@pytest.fixture(autouse=True)
def _test_settings(settings):
    # The production storage needs `collectstatic` first; tests do not run that step.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    # The test client speaks plain HTTP; HTTPS is checked by `manage.py check --deploy` in CI.
    settings.SECURE_SSL_REDIRECT = False
    # Fast hashing; password security itself is Django's and not under test here.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def make_member(db):
    """Create a user with a role in a business: make_member(role, business=None)."""
    counter = iter(range(1, 1000))

    def make(role=Role.OWNER, business=None):
        business = business or Business.objects.create(name="Café Linde")
        email = f"user{next(counter)}@example.com"
        user = get_user_model().objects.create_user(username=email, email=email, password="pw")
        Membership.objects.create(user=user, business=business, role=role)
        return user

    return make


@pytest.fixture
def owner(make_member):
    return make_member(Role.OWNER)


@pytest.fixture
def owner_client(client, owner):
    client.force_login(owner)
    return client
