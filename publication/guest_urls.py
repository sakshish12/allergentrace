from django.urls import path, re_path

from publication import views

# Public pages for guests; everything else lives under /app/ and needs a login.
urlpatterns = [
    path("<str:token>/", views.guest_menu, name="guest_menu"),
    re_path(r"^(?P<token>[\w-]+)/(?P<lang>de|en)/$", views.guest_menu, name="guest_menu_lang"),
]
