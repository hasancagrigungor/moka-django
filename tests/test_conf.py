"""Ayar ve istemci yapilandirma testleri."""

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from moka_django.client import get_base_url, get_moka_client
from moka_django.conf import get_moka_setting


class ConfTest(TestCase):
    def test_reads_user_setting(self):
        self.assertEqual(get_moka_setting("DEALER_CODE"), "1234")

    def test_falls_back_to_default(self):
        self.assertEqual(get_moka_setting("TIMEOUT"), 30)

    def test_unknown_setting_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            get_moka_setting("OLMAYAN_AYAR")

    @override_settings(MOKA={"USERNAME": "u", "PASSWORD": "p"})
    def test_missing_required_setting_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            get_moka_client()


class ClientTest(TestCase):
    def test_test_environment_url(self):
        self.assertEqual(get_base_url(), "https://service.refmokaunited.com")

    @override_settings(MOKA={
        "DEALER_CODE": "1", "USERNAME": "u", "PASSWORD": "p",
        "ENVIRONMENT": "production",
    })
    def test_production_environment_url(self):
        self.assertEqual(get_base_url(), "https://service.mokaunited.com")

    @override_settings(MOKA={
        "DEALER_CODE": "1", "USERNAME": "u", "PASSWORD": "p",
        "BASE_URL": "https://service.refmoka.com",
    })
    def test_base_url_override(self):
        self.assertEqual(get_base_url(), "https://service.refmoka.com")

    def test_client_is_configured_from_settings(self):
        client = get_moka_client()
        self.assertEqual(client.dealer_code, "1234")
        self.assertEqual(client.username, "apiuser")
        self.assertEqual(client.get_base_url(), "https://service.refmokaunited.com")
