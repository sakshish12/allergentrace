from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views
from accounts.forms import EmailLoginForm

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html", authentication_form=EmailLoginForm),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("app/", views.DashboardView.as_view(), name="dashboard"),
    path("app/staff/", views.StaffListView.as_view(), name="staff_list"),
    path("app/staff/new/", views.StaffCreateView.as_view(), name="staff_create"),
    path("app/staff/<int:pk>/edit/", views.StaffUpdateView.as_view(), name="staff_update"),
]
