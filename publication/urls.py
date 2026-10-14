from django.urls import path, re_path

from publication import views

urlpatterns = [
    path("approvals/", views.ApprovalListView.as_view(), name="approvals"),
    path("approvals/approve-all/", views.ApproveView.as_view(), name="approve_all"),
    path("approvals/<int:pk>/approve/", views.ApproveView.as_view(), name="approve"),
    path("history/", views.HistoryView.as_view(), name="history"),
    path("menu/", views.MenuView.as_view(), name="menu"),
    path("menu/allergen-list.pdf", views.MenuPdfView.as_view(), name="menu_pdf"),
    re_path(r"^menu/qr\.(?P<kind>png|svg)$", views.MenuQrView.as_view(), name="menu_qr"),
]
