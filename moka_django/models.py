"""Odeme kayit modeli."""

import uuid

from django.db import models
from django.utils import timezone


def generate_other_trx_code():
    """Tahmin edilemez, benzersiz islem kodu uretir."""
    return uuid.uuid4().hex


class MokaPayment(models.Model):
    """Moka United uzerinden gecen her odemenin yerel kaydi.

    OtherTrxCode degeri Moka United'a gonderilir; 3D Secure callback
    geldiginde odeme bu kodla bulunur. CodeForHash degeri 3D odeme
    baslatildiginda saklanir ve callback dogrulamasinda kullanilir.
    """

    STATUS_CREATED = "created"
    STATUS_REDIRECTED = "redirected"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Olusturuldu"),
        (STATUS_REDIRECTED, "3D dogrulamaya yonlendirildi"),
        (STATUS_SUCCESS, "Basarili"),
        (STATUS_FAILED, "Basarisiz"),
        (STATUS_CANCELLED, "Iptal edildi"),
        (STATUS_REFUNDED, "Iade edildi"),
    ]

    other_trx_code = models.CharField(
        "Islem kodu (OtherTrxCode)",
        max_length=64,
        unique=True,
        default=generate_other_trx_code,
        editable=False,
    )
    code_for_hash = models.CharField(
        "3D dogrulama kodu (CodeForHash)", max_length=64, blank=True, default=""
    )
    virtual_pos_order_id = models.CharField(
        "Sanal POS siparis no (VirtualPosOrderId)",
        max_length=64,
        blank=True,
        default="",
    )
    amount = models.DecimalField("Tutar", max_digits=12, decimal_places=2)
    currency = models.CharField("Para birimi", max_length=3, default="TL")
    installment_number = models.PositiveSmallIntegerField("Taksit sayisi", default=1)
    is_three_d = models.BooleanField("3D Secure odeme mi", default=False)
    status = models.CharField(
        "Durum", max_length=16, choices=STATUS_CHOICES, default=STATUS_CREATED
    )
    result_code = models.CharField("Sonuc kodu", max_length=128, blank=True, default="")
    result_message = models.CharField(
        "Sonuc mesaji", max_length=255, blank=True, default=""
    )
    description = models.CharField("Aciklama", max_length=200, blank=True, default="")
    completed_at = models.DateTimeField("Sonuclanma zamani", null=True, blank=True)
    created_at = models.DateTimeField("Olusturulma zamani", auto_now_add=True)
    updated_at = models.DateTimeField("Guncellenme zamani", auto_now=True)

    class Meta:
        verbose_name = "Moka odemesi"
        verbose_name_plural = "Moka odemeleri"
        ordering = ["-created_at"]

    def __str__(self):
        return "{0} - {1} {2} ({3})".format(
            self.other_trx_code, self.amount, self.currency, self.status
        )

    def mark_success(self, virtual_pos_order_id=""):
        self.status = self.STATUS_SUCCESS
        if virtual_pos_order_id:
            self.virtual_pos_order_id = virtual_pos_order_id
        self.completed_at = timezone.now()
        self.save(update_fields=[
            "status", "virtual_pos_order_id", "completed_at", "updated_at",
        ])

    def mark_failed(self, result_code="", result_message=""):
        self.status = self.STATUS_FAILED
        self.result_code = result_code or ""
        self.result_message = result_message or ""
        self.completed_at = timezone.now()
        self.save(update_fields=[
            "status", "result_code", "result_message", "completed_at", "updated_at",
        ])
