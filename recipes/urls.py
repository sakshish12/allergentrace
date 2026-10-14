from django.urls import path

from recipes import views

urlpatterns = [
    path("recipes/", views.RecipeListView.as_view(), name="recipe_list"),
    path("recipes/new/", views.RecipeCreateView.as_view(), name="recipe_create"),
    path("recipes/<int:pk>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipes/<int:pk>/edit/", views.RecipeUpdateView.as_view(), name="recipe_update"),
    path("recipes/<int:pk>/delete/", views.RecipeDeleteView.as_view(), name="recipe_delete"),
    path(
        "recipes/<int:pk>/components/<int:component_pk>/remove/",
        views.ComponentRemoveView.as_view(),
        name="component_remove",
    ),
    path("example-data/", views.ExampleDataView.as_view(), name="example_data"),
]
