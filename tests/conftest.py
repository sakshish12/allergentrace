import pytest


@pytest.fixture(autouse=True)
def _test_settings(settings):
    # The production storage needs `collectstatic` first; tests do not run that step.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    # The test client speaks plain HTTP; HTTPS is checked by `manage.py check --deploy` in CI.
    settings.SECURE_SSL_REDIRECT = False
