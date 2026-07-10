"""Test ayarlari."""

SECRET_KEY = "test-anahtari"

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "moka_django",
]

ROOT_URLCONF = "tests.urls"

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MOKA = {
    "DEALER_CODE": "1234",
    "USERNAME": "apiuser",
    "PASSWORD": "apipass",
    "ENVIRONMENT": "test",
    "SOFTWARE": "moka-django-test",
    "CALLBACK_SUCCESS_URL": "/odeme/basarili/",
    "CALLBACK_FAIL_URL": "/odeme/basarisiz/",
}
