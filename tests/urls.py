from django.urls import include, path

urlpatterns = [
    path("moka/", include("moka_django.urls")),
]
