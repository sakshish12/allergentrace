from django.urls import path

from catalog import views

urlpatterns = [
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/new/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("suppliers/<int:pk>/delete/", views.SupplierDeleteView.as_view(), name="supplier_delete"),
    path("ingredients/", views.IngredientListView.as_view(), name="ingredient_list"),
    path("ingredients/new/", views.IngredientCreateView.as_view(), name="ingredient_create"),
    path("ingredients/<int:pk>/edit/", views.IngredientUpdateView.as_view(), name="ingredient_update"),
    path("ingredients/<int:pk>/delete/", views.IngredientDeleteView.as_view(), name="ingredient_delete"),
]
