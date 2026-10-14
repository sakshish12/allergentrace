from django.urls import path

from publication import views

urlpatterns = [
    path("approvals/", views.ApprovalListView.as_view(), name="approvals"),
    path("approvals/approve-all/", views.ApproveView.as_view(), name="approve_all"),
    path("approvals/<int:pk>/approve/", views.ApproveView.as_view(), name="approve"),
    path("history/", views.HistoryView.as_view(), name="history"),
]
