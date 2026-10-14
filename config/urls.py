from django.contrib import admin
from django.urls import include, path

from config import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("", include("accounts.urls")),
    path("app/", include("catalog.urls")),
    path("app/", include("recipes.urls")),
    path("app/", include("publication.urls")),
    path("admin/", admin.site.urls),
]
