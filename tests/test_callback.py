"""3D Secure callback testleri."""

import hashlib

from django.test import TestCase
from django.urls import reverse

from moka_django.models import MokaPayment
from moka_django.signals import moka_payment_failed, moka_payment_succeeded

CODE_FOR_HASH = "9FDFBDFC-42C5-417E-AA93-E4D9D5312AAC"


def make_hash(suffix):
    return hashlib.sha256((CODE_FOR_HASH + suffix).encode("utf-8")).hexdigest()


class CallbackViewTest(TestCase):
    def setUp(self):
        self.payment = MokaPayment.objects.create(
            amount="100.00",
            is_three_d=True,
            status=MokaPayment.STATUS_REDIRECTED,
            code_for_hash=CODE_FOR_HASH,
        )
        self.url = reverse("moka_django:callback")
        self.succeeded = []
        self.failed = []
        moka_payment_succeeded.connect(self._on_success)
        moka_payment_failed.connect(self._on_failure)
        self.addCleanup(moka_payment_succeeded.disconnect, self._on_success)
        self.addCleanup(moka_payment_failed.disconnect, self._on_failure)

    def _on_success(self, sender, payment, **kwargs):
        self.succeeded.append(payment)

    def _on_failure(self, sender, payment, **kwargs):
        self.failed.append(payment)

    def _post_callback(self, hash_value, **overrides):
        data = {
            "hashValue": hash_value,
            "resultCode": "",
            "resultMessage": "",
            "trxCode": "ORDER-17131QQFG04026575",
            "OtherTrxCode": self.payment.other_trx_code,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_successful_callback(self):
        response = self._post_callback(make_hash("T"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/odeme/basarili/"))
        self.assertIn(self.payment.other_trx_code, response["Location"])

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, MokaPayment.STATUS_SUCCESS)
        self.assertEqual(
            self.payment.virtual_pos_order_id, "ORDER-17131QQFG04026575"
        )
        self.assertEqual(self.succeeded, [self.payment])

    def test_failed_callback(self):
        response = self._post_callback(
            make_hash("F"), resultCode="002", resultMessage="Limit Yetersiz"
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/odeme/basarisiz/"))

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, MokaPayment.STATUS_FAILED)
        self.assertEqual(self.payment.result_code, "002")
        self.assertEqual(self.failed, [self.payment])

    def test_tampered_hash_is_rejected(self):
        response = self._post_callback("gecersiz-hash-degeri")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/odeme/basarisiz/"))

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, MokaPayment.STATUS_FAILED)
        self.assertEqual(self.payment.result_code, "InvalidHash")

    def test_missing_hash_value(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    def test_unknown_payment(self):
        response = self._post_callback(make_hash("T"), OtherTrxCode="bilinmeyen")
        self.assertEqual(response.status_code, 400)

    def test_csrf_exempt(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.url, {
            "hashValue": make_hash("T"),
            "OtherTrxCode": self.payment.other_trx_code,
            "trxCode": "ORDER-1",
        })
        self.assertEqual(response.status_code, 302)
