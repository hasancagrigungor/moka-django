"""MokaPayment modeli testleri."""

from django.test import TestCase

from moka_django.models import MokaPayment


class MokaPaymentModelTest(TestCase):
    def test_defaults(self):
        payment = MokaPayment.objects.create(amount="100.50")
        self.assertEqual(payment.status, MokaPayment.STATUS_CREATED)
        self.assertEqual(payment.currency, "TL")
        self.assertEqual(payment.installment_number, 1)
        self.assertFalse(payment.is_three_d)
        self.assertEqual(len(payment.other_trx_code), 32)
        self.assertIsNone(payment.completed_at)

    def test_other_trx_code_is_unique(self):
        first = MokaPayment.objects.create(amount="1.00")
        second = MokaPayment.objects.create(amount="2.00")
        self.assertNotEqual(first.other_trx_code, second.other_trx_code)

    def test_mark_success(self):
        payment = MokaPayment.objects.create(amount="10.00")
        payment.mark_success("ORDER-123")
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_SUCCESS)
        self.assertEqual(payment.virtual_pos_order_id, "ORDER-123")
        self.assertIsNotNone(payment.completed_at)

    def test_mark_failed(self):
        payment = MokaPayment.objects.create(amount="10.00")
        payment.mark_failed("002", "Limit Yetersiz")
        payment.refresh_from_db()
        self.assertEqual(payment.status, MokaPayment.STATUS_FAILED)
        self.assertEqual(payment.result_code, "002")
        self.assertEqual(payment.result_message, "Limit Yetersiz")

    def test_str(self):
        payment = MokaPayment.objects.create(amount="10.00")
        self.assertIn(payment.other_trx_code, str(payment))
