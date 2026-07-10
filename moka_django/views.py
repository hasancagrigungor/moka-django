"""3D Secure callback gorunumu."""

from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from moka_django.conf import get_moka_setting
from moka_django.models import MokaPayment
from moka_django.payments import handle_callback


@method_decorator(csrf_exempt, name="dispatch")
class MokaCallbackView(View):
    """Moka United'in 3D Secure sonucunu POST ettigi gorunum.

    Hash dogrulamasi yapar, odeme kaydini gunceller ve kullaniciyi
    MOKA ayarlarindaki CALLBACK_SUCCESS_URL veya CALLBACK_FAIL_URL
    adresine yonlendirir. Farkli davranis icin get_success_url,
    get_fail_url veya on_success / on_failure metotlari ezilebilir.
    """

    def post(self, request, *args, **kwargs):
        if not request.POST.get("hashValue"):
            return HttpResponseBadRequest("hashValue bulunamadi")

        try:
            payment, success = handle_callback(request.POST)
        except MokaPayment.DoesNotExist:
            return HttpResponseBadRequest("Odeme kaydi bulunamadi")

        if success:
            return self.on_success(request, payment)
        return self.on_failure(request, payment)

    def on_success(self, request, payment):
        return redirect(self.get_success_url(payment))

    def on_failure(self, request, payment):
        return redirect(self.get_fail_url(payment))

    def get_success_url(self, payment):
        return "{0}?payment={1}".format(
            get_moka_setting("CALLBACK_SUCCESS_URL"), payment.other_trx_code
        )

    def get_fail_url(self, payment):
        return "{0}?payment={1}".format(
            get_moka_setting("CALLBACK_FAIL_URL"), payment.other_trx_code
        )
