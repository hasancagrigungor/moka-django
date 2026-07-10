from django.contrib import admin

from moka_django.models import MokaPayment


@admin.register(MokaPayment)
class MokaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "other_trx_code",
        "amount",
        "currency",
        "installment_number",
        "is_three_d",
        "status",
        "virtual_pos_order_id",
        "created_at",
    )
    list_filter = ("status", "is_three_d", "currency")
    search_fields = ("other_trx_code", "virtual_pos_order_id")
    readonly_fields = (
        "other_trx_code",
        "code_for_hash",
        "created_at",
        "updated_at",
        "completed_at",
    )
