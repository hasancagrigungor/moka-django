"""Odeme akisi testleri."""

from unittest.mock import patch

from django.test import TestCase

from moka.test_cards import TEST_CARDS

from moka_django.models import MokaPayment
from moka_django.payments import create_payment, start_threeds_payment
from moka_django.signals import moka_payment_failed, moka_payment_succeeded
from tests.helpers import (
    BANK_DECLINED_RESPONSE,
    INVALID_ACCOUNT_RESPONSE,
    SUCCESS_PAYMENT_RESPONSE,
    THREEDS_START_RESPONSE,
    FakeMokaClient,
)

TEST_CARD = {
    "card_holder_full_name": "Test Kullanici",
    "card_number": TEST_CARDS[0]["card_number"],
    "exp_month": TEST_CARDS[0]["exp_month"],
    "exp_year": TEST_CARDS[0]["exp_year"],
    "cvc": TEST_CARDS[0]["cvc"],
}


class SignalRecorder:
    def __init__(self):
        self.succeeded = []
        self.failed = []
        moka_payment_succeeded.connect(self._on_success)
        moka_payment_failed.connect(self._on_failure)

    def _on_success(self, sender, payment, **kwargs):
        self.succeeded.append(payment)

    def _on_failure(self, sender, payment, **kwargs):
        self.failed.append(payment)

    def disconnect(self):
        moka_payment_succeeded.disconnect(self._on_success)
        moka_payment_failed.disconnect(self._on_failure)


class PaymentFlowTestCase(TestCase):
    def setUp(self):
        self.signals = SignalRecorder()
        self.addCleanup(self.signals.disconnect)

    def _patch_client(self, payload):
        fake = FakeMokaClient(payload)
        patcher = patch("moka_django.payments.get_moka_client", return_value=fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake


class CreatePaymentTest(PaymentFlowTestCase):
    def test_successful_payment(self):
        fake = self._patch_client(SUCCESS_PAYMENT_RESPONSE)
        payment, response = create_payment(
            amount="100.50", card=TEST_CARD, client_ip="1.2.3.4"
        )
        self.assertTrue(response.is_payment_successful)
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_SUCCESS)
        self.assertEqual(payment.virtual_pos_order_id, "ORDER-TEST-123")
        self.assertEqual(self.signals.succeeded, [payment])
        self.assertEqual(self.signals.failed, [])

        sent = fake.last_request.to_dict()
        self.assertEqual(sent["CardNumber"], TEST_CARD["card_number"])
        self.assertEqual(sent["Amount"], 100.5)
        self.assertEqual(sent["ClientIP"], "1.2.3.4")
        self.assertEqual(sent["OtherTrxCode"], payment.other_trx_code)
        self.assertEqual(sent["Software"], "moka-django-test")

    def test_bank_declined_payment(self):
        self._patch_client(BANK_DECLINED_RESPONSE)
        payment, response = create_payment(amount="100.50", card=TEST_CARD)
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_FAILED)
        self.assertEqual(payment.result_code, "002")
        self.assertEqual(payment.result_message, "Limit Yetersiz")
        self.assertEqual(self.signals.failed, [payment])

    def test_invalid_account(self):
        self._patch_client(INVALID_ACCOUNT_RESPONSE)
        payment, response = create_payment(amount="1.00", card=TEST_CARD)
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_FAILED)
        self.assertIn("InvalidAccount", payment.result_code)

    def test_card_token_and_extra_fields(self):
        fake = self._patch_client(SUCCESS_PAYMENT_RESPONSE)
        create_payment(
            amount="10.00",
            card_token="token-123",
            extra={"IsPoolPayment": 1, "SubMerchantName": "Alt Bayi"},
        )
        sent = fake.last_request.to_dict()
        self.assertEqual(sent["CardToken"], "token-123")
        self.assertEqual(sent["IsPoolPayment"], 1)
        self.assertEqual(sent["SubMerchantName"], "Alt Bayi")


class StartThreedsPaymentTest(PaymentFlowTestCase):
    def test_successful_start(self):
        fake = self._patch_client(THREEDS_START_RESPONSE)
        payment, url, response = start_threeds_payment(
            amount="250.00",
            redirect_url="https://ornek.com/moka/callback/",
            card=TEST_CARD,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_REDIRECTED)
        self.assertEqual(payment.code_for_hash, "9FDFBDFC-42C5-417E-AA93-E4D9D5312AAC")
        self.assertTrue(payment.is_three_d)
        self.assertIn("PaymentDealerThreeDProcess", url)

        sent = fake.last_request.to_dict()
        self.assertEqual(sent["ReturnHash"], 1)
        self.assertEqual(sent["RedirectUrl"], "https://ornek.com/moka/callback/")
        # 3D baslatma odeme sonucu degildir; sinyal gonderilmemeli
        self.assertEqual(self.signals.succeeded, [])
        self.assertEqual(self.signals.failed, [])

    def test_failed_start(self):
        self._patch_client(INVALID_ACCOUNT_RESPONSE)
        payment, url, response = start_threeds_payment(
            amount="250.00",
            redirect_url="https://ornek.com/moka/callback/",
            card=TEST_CARD,
        )
        payment.refresh_from_db()
        self.assertIsNone(url)
        self.assertEqual(payment.status, MokaPayment.STATUS_FAILED)
        self.assertEqual(self.signals.failed, [payment])
