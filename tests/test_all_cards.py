"""Tum test kartlarinin Django odeme akisindan gecirilmesi.

36 test kartinin her biri icin hem Non-3D odeme hem de 3D odeme baslatma
ve callback dogrulama akisi calistirilir. Moka istemcisi sahte yanitlarla
taklit edilir; hash dogrulamasi gercek SHA-256 kuraliyla yapilir.
"""

import hashlib

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from moka.test_cards import TEST_CARDS

from moka_django.models import MokaPayment
from moka_django.payments import create_payment, start_threeds_payment
from tests.helpers import (
    SUCCESS_PAYMENT_RESPONSE,
    THREEDS_START_RESPONSE,
    FakeMokaClient,
)


def card_kwargs(card):
    return {
        "card_holder_full_name": "Test Kullanici",
        "card_number": card["card_number"],
        "exp_month": card["exp_month"],
        "exp_year": card["exp_year"],
        "cvc": card["cvc"],
    }


class AllCardsDirectPaymentTest(TestCase):
    def test_create_payment_with_every_card(self):
        fake = FakeMokaClient(SUCCESS_PAYMENT_RESPONSE)
        with patch("moka_django.payments.get_moka_client", return_value=fake):
            for card in TEST_CARDS:
                with self.subTest(bank=card["bank"], card_type=card["card_type"]):
                    payment, response = create_payment(
                        amount="0.01", card=card_kwargs(card), client_ip="127.0.0.1"
                    )
                    payment.refresh_from_db()
                    self.assertEqual(payment.status, MokaPayment.STATUS_SUCCESS)

                    sent = fake.last_request.to_dict()
                    self.assertEqual(sent["CardNumber"], card["card_number"])
                    self.assertEqual(sent["ExpMonth"], "12")
                    self.assertEqual(sent["ExpYear"], "2030")
                    self.assertEqual(sent["CvcNumber"], "000")
                    self.assertEqual(sent["OtherTrxCode"], payment.other_trx_code)

        # her kart icin ayri odeme kaydi olusmus olmali
        self.assertEqual(MokaPayment.objects.count(), len(TEST_CARDS))
        self.assertEqual(
            MokaPayment.objects.filter(status=MokaPayment.STATUS_SUCCESS).count(),
            len(TEST_CARDS),
        )


class AllCardsThreedsFlowTest(TestCase):
    """Her kart icin 3D baslatma + basarili callback donusu ucuca test edilir."""

    CODE_FOR_HASH = THREEDS_START_RESPONSE["Data"]["CodeForHash"]

    def _success_hash(self):
        return hashlib.sha256(
            (self.CODE_FOR_HASH + "T").encode("utf-8")
        ).hexdigest()

    def test_threeds_flow_with_every_card(self):
        fake = FakeMokaClient(THREEDS_START_RESPONSE)
        callback_url = reverse("moka_django:callback")

        for card in TEST_CARDS:
            with self.subTest(bank=card["bank"], card_type=card["card_type"]):
                with patch(
                    "moka_django.payments.get_moka_client", return_value=fake
                ):
                    payment, url, response = start_threeds_payment(
                        amount="0.01",
                        redirect_url="https://ornek.com" + callback_url,
                        card=card_kwargs(card),
                        client_ip="127.0.0.1",
                    )

                self.assertIsNotNone(url)
                payment.refresh_from_db()
                self.assertEqual(payment.status, MokaPayment.STATUS_REDIRECTED)
                self.assertEqual(payment.code_for_hash, self.CODE_FOR_HASH)

                sent = fake.last_request.to_dict()
                self.assertEqual(sent["CardNumber"], card["card_number"])

                # bankadan basarili donus simulasyonu
                callback = self.client.post(callback_url, {
                    "hashValue": self._success_hash(),
                    "resultCode": "",
                    "resultMessage": "",
                    "trxCode": "ORDER-{0}".format(card["card_number"][:6]),
                    "OtherTrxCode": payment.other_trx_code,
                })
                self.assertEqual(callback.status_code, 302)
                self.assertTrue(
                    callback["Location"].startswith("/odeme/basarili/")
                )

                payment.refresh_from_db()
                self.assertEqual(payment.status, MokaPayment.STATUS_SUCCESS)
                self.assertEqual(
                    payment.virtual_pos_order_id,
                    "ORDER-{0}".format(card["card_number"][:6]),
                )

        self.assertEqual(MokaPayment.objects.count(), len(TEST_CARDS))
