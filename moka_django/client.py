"""Django ayarlarindan MokaClient olusturma."""

from moka import DEFAULT_API_BASE, TEST_API_BASE, MokaClient

from moka_django.conf import get_moka_setting, validate_settings


def get_base_url():
    """Ayarlara gore kullanilacak ortam adresini dondurur."""
    base_url = get_moka_setting("BASE_URL")
    if base_url:
        return base_url
    if get_moka_setting("ENVIRONMENT") == "production":
        return DEFAULT_API_BASE
    return TEST_API_BASE


def get_moka_client():
    """Ayarlarla yapilandirilmis MokaClient dondurur."""
    validate_settings()
    return MokaClient(
        dealer_code=get_moka_setting("DEALER_CODE"),
        username=get_moka_setting("USERNAME"),
        password=get_moka_setting("PASSWORD"),
        base_url=get_base_url(),
        timeout=get_moka_setting("TIMEOUT"),
    )
