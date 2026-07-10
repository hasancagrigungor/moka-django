"""URL tanimlari.

Projenizin urls.py dosyasina soyle eklenir:

    path("moka/", include("moka_django.urls")),

Bu durumda 3D Secure donus adresi:
https://www.siteniz.com/moka/callback/
"""

from django.urls import path

from moka_django.views import MokaCallbackView

app_name = "moka_django"

urlpatterns = [
    path("callback/", MokaCallbackView.as_view(), name="callback"),
]
