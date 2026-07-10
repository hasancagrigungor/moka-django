"""Odeme sonucu sinyalleri.

Kullanim:

    from django.dispatch import receiver
    from moka_django.signals import moka_payment_succeeded

    @receiver(moka_payment_succeeded)
    def odeme_basarili(sender, payment, **kwargs):
        # siparisi onayla, fatura kes, e-posta gonder...
        ...

Her iki sinyal de "payment" (MokaPayment) argumaniyla gonderilir.
"""

from django.dispatch import Signal

# 3D Secure callback dogrulamasi basarili oldugunda gonderilir
moka_payment_succeeded = Signal()

# Odeme basarisiz oldugunda veya hash dogrulanamadiginda gonderilir
moka_payment_failed = Signal()
