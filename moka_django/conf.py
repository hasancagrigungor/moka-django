"""Ayar yonetimi.

Tum ayarlar, projenin settings.py dosyasindaki MOKA sozlugunden okunur:

    MOKA = {
        "DEALER_CODE": "bayi kodunuz",
        "USERNAME": "api kullanici adiniz",
        "PASSWORD": "api sifreniz",
        "ENVIRONMENT": "test",  # "test" veya "production"
        "SOFTWARE": "yazilim adiniz",
        "CALLBACK_SUCCESS_URL": "/odeme/basarili/",
        "CALLBACK_FAIL_URL": "/odeme/basarisiz/",
    }
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEFAULTS = {
    "DEALER_CODE": None,
    "USERNAME": None,
    "PASSWORD": None,
    "ENVIRONMENT": "test",
    "BASE_URL": None,  # verilirse ENVIRONMENT ayarini ezer
    "SOFTWARE": "moka-django",
    "TIMEOUT": 30,
    "CALLBACK_SUCCESS_URL": "/",
    "CALLBACK_FAIL_URL": "/",
}

REQUIRED = ("DEALER_CODE", "USERNAME", "PASSWORD")


def get_moka_setting(name):
    """MOKA sozlugunden ayar okur; yoksa varsayilan degeri dondurur."""
    user_settings = getattr(settings, "MOKA", {})
    if name in user_settings:
        return user_settings[name]
    if name in DEFAULTS:
        return DEFAULTS[name]
    raise ImproperlyConfigured("Bilinmeyen MOKA ayari: {0}".format(name))


def validate_settings():
    """Zorunlu ayarlarin tanimli oldugunu dogrular."""
    for name in REQUIRED:
        if not get_moka_setting(name):
            raise ImproperlyConfigured(
                "MOKA ayarlarinda '{0}' tanimlanmalidir. settings.py dosyaniza "
                "MOKA sozlugunu ekleyiniz.".format(name)
            )
