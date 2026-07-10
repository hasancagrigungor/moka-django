"""Yuksek seviyeli odeme akislari.

Bu modul, moka-python istemcisini MokaPayment kayitlariyla birlestirir:

- create_payment: Non-3D odeme yapar ve sonucu kaydeder.
- start_threeds_payment: 3D odeme baslatir, CodeForHash degerini saklar
  ve kullanicinin yonlendirilecegi banka dogrulama adresini dondurur.
- handle_callback: 3D donusunde hash dogrulamasi yapar, kaydi gunceller
  ve ilgili sinyali gonderir.
"""

from moka import models as moka_models
from moka.utils import verify_threeds_result

from moka_django.client import get_moka_client
from moka_django.conf import get_moka_setting
from moka_django.models import MokaPayment
from moka_django.signals import moka_payment_failed, moka_payment_succeeded


def get_client_ip(request):
    """Django request nesnesinden istemci IP adresini cikarir."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _build_payment_request(payment, card=None, card_token=None,
                           client_ip="", buyer=None, extra=None):
    request = moka_models.CreatePaymentRequest(
        Amount=float(payment.amount),
        Currency=payment.currency,
        InstallmentNumber=payment.installment_number,
        ClientIP=client_ip,
        OtherTrxCode=payment.other_trx_code,
        IsPoolPayment=0,
        IsTokenized=0,
        IntegratorId=0,
        Software=get_moka_setting("SOFTWARE"),
        Description=payment.description,
        IsPreAuth=0,
    )
    if card:
        request.CardHolderFullName = card.get("card_holder_full_name")
        request.CardNumber = card.get("card_number")
        request.ExpMonth = card.get("exp_month")
        request.ExpYear = card.get("exp_year")
        request.CvcNumber = card.get("cvc")
    if card_token:
        request.CardToken = card_token
    if buyer:
        request.BuyerInformation = buyer
    for field, value in (extra or {}).items():
        setattr(request, field, value)
    return request


def create_payment(amount, card=None, card_token=None, currency="TL",
                   installment_number=1, client_ip="", description="",
                   buyer=None, extra=None):
    """3D Secure olmadan (Non-3D) odeme yapar.

    card: {"card_holder_full_name", "card_number", "exp_month",
           "exp_year", "cvc"} anahtarlarini tasiyan sozluk.
    card_token: sakli kartla odeme icin kart token degeri.
    extra: CreatePaymentRequest uzerindeki diger alanlar
           (ornegin {"IsPoolPayment": 1}).

    Donus: (MokaPayment, ApiResponse)
    """
    payment = MokaPayment.objects.create(
        amount=amount,
        currency=currency,
        installment_number=installment_number,
        description=description,
        is_three_d=False,
    )

    request = _build_payment_request(
        payment, card=card, card_token=card_token,
        client_ip=client_ip, buyer=buyer, extra=extra,
    )

    response = get_moka_client().payments().create(request)

    if response.is_payment_successful:
        payment.mark_success(response.data.get("VirtualPosOrderId", ""))
        moka_payment_succeeded.send(sender=MokaPayment, payment=payment)
    else:
        data = response.data if isinstance(response.data, dict) else {}
        payment.mark_failed(
            data.get("ResultCode") or response.result_code or "",
            data.get("ResultMessage") or response.result_message or "",
        )
        moka_payment_failed.send(sender=MokaPayment, payment=payment)

    return payment, response


def start_threeds_payment(amount, redirect_url, card=None, card_token=None,
                          currency="TL", installment_number=1, client_ip="",
                          description="", buyer=None, extra=None):
    """3D Secure ile odeme baslatir.

    Basarili olursa donen URL'e kullanici yonlendirilmelidir. Odeme
    tamamlandiginda Moka United, redirect_url adresine sonucu POST eder;
    bu istek MokaCallbackView (veya handle_callback) ile islenir.

    Donus: (MokaPayment, yonlendirme_url veya None, ApiResponse)
    """
    payment = MokaPayment.objects.create(
        amount=amount,
        currency=currency,
        installment_number=installment_number,
        description=description,
        is_three_d=True,
    )

    request = _build_payment_request(
        payment, card=card, card_token=card_token,
        client_ip=client_ip, buyer=buyer, extra=extra,
    )
    request.ReturnHash = 1
    request.RedirectUrl = redirect_url
    request.RedirectType = (extra or {}).get("RedirectType", 0)

    response = get_moka_client().payments().create_threeds(request)

    if response.is_success and isinstance(response.data, dict):
        payment.code_for_hash = response.data.get("CodeForHash", "")
        payment.status = MokaPayment.STATUS_REDIRECTED
        payment.save(update_fields=["code_for_hash", "status", "updated_at"])
        return payment, response.data.get("Url"), response

    payment.mark_failed(response.result_code or "", response.result_message or "")
    moka_payment_failed.send(sender=MokaPayment, payment=payment)
    return payment, None, response


def handle_callback(data):
    """3D Secure donus verisini isler.

    data: Moka United'in RedirectUrl adresinize POST ettigi form verisi
    (hashValue, resultCode, resultMessage, trxCode, OtherTrxCode).

    hashValue su kurala gore dogrulanir:
    SHA256(CodeForHash + "T") -> basarili, SHA256(CodeForHash + "F") -> basarisiz.

    Donus: (MokaPayment, basarili_mi)
    MokaPayment.DoesNotExist: OtherTrxCode ile eslesen kayit yoksa.
    """
    other_trx_code = data.get("OtherTrxCode", "")
    payment = MokaPayment.objects.get(other_trx_code=other_trx_code)

    result = verify_threeds_result(payment.code_for_hash, data.get("hashValue", ""))

    if result is True:
        payment.mark_success(data.get("trxCode", ""))
        moka_payment_succeeded.send(sender=MokaPayment, payment=payment)
        return payment, True

    if result is False:
        payment.mark_failed(data.get("resultCode", ""), data.get("resultMessage", ""))
    else:
        payment.mark_failed("InvalidHash", "hashValue dogrulanamadi")
    moka_payment_failed.send(sender=MokaPayment, payment=payment)
    return payment, False
