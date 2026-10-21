from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from accounts import views

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("signup/sent/", TemplateView.as_view(template_name="accounts/signup_done.html"), name="signup_done"),
    path("activate/<uidb64>/<token>/", views.ActivateView.as_view(), name="activate"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("app/", views.DashboardView.as_view(), name="dashboard"),
    path("app/staff/", views.StaffListView.as_view(), name="staff_list"),
    path("app/staff/new/", views.StaffCreateView.as_view(), name="staff_create"),
    path("app/staff/<int:pk>/edit/", views.StaffUpdateView.as_view(), name="staff_update"),
]
