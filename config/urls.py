from django.contrib import admin
from django.urls import include, path

from config import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("privacy/", views.page, {"template": "privacy.html"}, name="privacy"),
    path("terms/", views.page, {"template": "terms.html"}, name="terms"),
    path("", include("accounts.urls")),
    path("app/", include("catalog.urls")),
    path("app/", include("recipes.urls")),
    path("app/", include("publication.urls")),
    path("m/", include("publication.guest_urls")),
    path("admin/", admin.site.urls),
]
