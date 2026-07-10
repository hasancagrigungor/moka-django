# moka-django

> **Bu kütüphane bağımsız olarak geliştirilmiştir; Moka United'ın resmi ürünü değildir, Moka United tarafından geliştirilmemiş, onaylanmamış ve desteklenmemektedir.**

Moka United sanal POS entegrasyonu icin Django uygulamasi.

Bu paket, [moka-python](https://pypi.org/project/moka-python/) kutuphanesinin ustune Django projelerinde ihtiyac duyulan katmani ekler: odeme kaydi tutan model, 3D Secure callback dogrulama gorunumu, odeme baslatma fonksiyonlari, sinyaller ve admin entegrasyonu. Moka United API'sinin tamamina (kart saklama, tekrarlayan odeme, raporlama vb.) moka-python istemcisi uzerinden erisilebilir.

## Ozellikler

- settings.py uzerinden yapilandirma (test / canli ortam secimi)
- Non-3D odeme akisi: tek fonksiyonla odeme yap, sonucu veritabanina isle
- 3D Secure odeme akisi: odeme baslat, CodeForHash degerini sakla, kullaniciyi bankaya yonlendir
- Hazir callback gorunumu: hashValue dogrulamasi (SHA-256, T/F kurali), kayit guncelleme ve yonlendirme
- moka_payment_succeeded ve moka_payment_failed sinyalleri
- MokaPayment modeli ve Django admin kaydi
- Sakli kartla (CardToken) odeme destegi
- Moka United API'sinin tum servislerine get_moka_client ile dogrudan erisim
- Test kartlariyla calisan kapsamli test paketi

## Gereksinimler

- Python 3.8 ve uzeri
- Django 3.2 ve uzeri
- moka-python

## Kurulum

```bash
pip install moka-django
```

settings.py dosyaniza uygulamayi ve ayarlari ekleyin:

```python
INSTALLED_APPS = [
    # ...
    "moka_django",
]

MOKA = {
    "DEALER_CODE": "bayi kodunuz",
    "USERNAME": "api kullanici adiniz",
    "PASSWORD": "api sifreniz",
    "ENVIRONMENT": "test",  # canli ortam icin "production"
    "SOFTWARE": "yazilim adiniz",
    "CALLBACK_SUCCESS_URL": "/odeme/basarili/",
    "CALLBACK_FAIL_URL": "/odeme/basarisiz/",
}
```

Ana urls.py dosyaniza callback adresini ekleyin:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("moka/", include("moka_django.urls")),
]
```

Veritabani tablosunu olusturun:

```bash
python manage.py migrate moka_django
```

### Ayarlar

| Ayar | Zorunlu | Varsayilan | Aciklama |
| --- | --- | --- | --- |
| DEALER_CODE | Evet | - | Moka United bayi kodu |
| USERNAME | Evet | - | API kullanici adi |
| PASSWORD | Evet | - | API sifresi |
| ENVIRONMENT | Hayir | "test" | "test": service.refmokaunited.com, "production": service.mokaunited.com |
| BASE_URL | Hayir | None | Verilirse ENVIRONMENT ayarini ezer (ornegin eski service.refmoka.com adresi icin) |
| SOFTWARE | Hayir | "moka-django" | Isteklerde gonderilen yazilim adi |
| TIMEOUT | Hayir | 30 | HTTP istek zaman asimi (saniye) |
| CALLBACK_SUCCESS_URL | Hayir | "/" | Basarili 3D odemede yonlendirilecek adres |
| CALLBACK_FAIL_URL | Hayir | "/" | Basarisiz 3D odemede yonlendirilecek adres |

CheckKey degeri (DealerCode + "MK" + Username + "PD" + Password bilgisinin SHA-256 ozeti) her istekte otomatik uretilir.

## 3D Secure ile Odeme

Onerilen akis 3D Secure'dur. Odeme baslatilir, kullanici bankanin dogrulama sayfasina yonlendirilir, sonuc callback adresinize POST edilir:

```python
from django.shortcuts import redirect, render
from django.urls import reverse

from moka_django.payments import get_client_ip, start_threeds_payment


def odeme_yap(request):
    payment, url, response = start_threeds_payment(
        amount="250.00",
        redirect_url=request.build_absolute_uri(reverse("moka_django:callback")),
        card={
            "card_holder_full_name": request.POST["kart_sahibi"],
            "card_number": request.POST["kart_no"],
            "exp_month": request.POST["ay"],
            "exp_year": request.POST["yil"],
            "cvc": request.POST["cvc"],
        },
        client_ip=get_client_ip(request),
        description="Siparis No: 1453",
    )

    if url:
        # payment.other_trx_code degerini siparisinizle iliskilendirin
        return redirect(url)

    return render(request, "odeme_hata.html", {
        "hata": response.result_code,
    })
```

Kart dogrulamasi tamamlandiginda Moka United, callback adresinize hashValue, resultCode, resultMessage, trxCode ve OtherTrxCode alanlarini POST eder. Paketin hazir MokaCallbackView gorunumu bu istegi alir, hashValue degerini SHA-256 kuraliyla dogrular (CodeForHash + "T" basarili, CodeForHash + "F" basarisiz), MokaPayment kaydini gunceller, ilgili sinyali gonderir ve kullaniciyi CALLBACK_SUCCESS_URL veya CALLBACK_FAIL_URL adresine `?payment=<other_trx_code>` parametresiyle yonlendirir.

### Sinyaller

Odeme sonucuna gore is mantiginizi sinyallerle baglayin:

```python
from django.dispatch import receiver

from moka_django.signals import moka_payment_failed, moka_payment_succeeded


@receiver(moka_payment_succeeded)
def odeme_basarili(sender, payment, **kwargs):
    # siparisi onayla, stok dus, e-posta gonder...
    ...


@receiver(moka_payment_failed)
def odeme_basarisiz(sender, payment, **kwargs):
    # payment.result_code ve payment.result_message alanlarina bakin
    ...
```

### Callback davranisini ozellestirme

```python
from django.shortcuts import render

from moka_django.views import MokaCallbackView


class OzelCallbackView(MokaCallbackView):
    def on_success(self, request, payment):
        return render(request, "tesekkurler.html", {"payment": payment})

    def on_failure(self, request, payment):
        return render(request, "odeme_hata.html", {"payment": payment})
```

Bu durumda urls.py dosyanizda hazir `moka_django.urls` yerine kendi gorunumunuzu baglayin:

```python
path("moka/callback/", OzelCallbackView.as_view(), name="moka-callback"),
```

## 3D Secure Olmadan Odeme (Non-3D)

Bayinizin Non-3D islem yetkisi varsa tek adimda odeme alabilirsiniz:

```python
from moka_django.payments import create_payment, get_client_ip

payment, response = create_payment(
    amount="100.50",
    card={
        "card_holder_full_name": "Ali Yilmaz",
        "card_number": "5127541122223332",
        "exp_month": "12",
        "exp_year": "2030",
        "cvc": "000",
    },
    installment_number=1,
    client_ip=get_client_ip(request),
)

if payment.status == payment.STATUS_SUCCESS:
    # payment.virtual_pos_order_id iptal/iade icin saklanir
    ...
```

### Sakli kartla odeme

```python
payment, response = create_payment(amount="100.50", card_token="kart tokeni")
```

### Ek API alanlari

CreatePaymentRequest uzerindeki diger alanlar `extra` sozluguyle gonderilir:

```python
payment, response = create_payment(
    amount="100.50",
    card=kart_bilgisi,
    extra={
        "IsPoolPayment": 1,     # havuz odemesi
        "IsPreAuth": 1,         # on provizyon
        "IsTokenized": 1,       # karti sakla
        "SubMerchantName": "Alt Bayi",
    },
)
```

## MokaPayment Modeli

Her odeme girisimi veritabanina kaydedilir:

| Alan | Aciklama |
| --- | --- |
| other_trx_code | Moka United'a gonderilen benzersiz islem kodu (OtherTrxCode) |
| code_for_hash | 3D odemede saklanan dogrulama kodu (CodeForHash) |
| virtual_pos_order_id | Basarili islemde donen siparis numarasi; iptal ve iade islemlerinde kullanilir |
| amount, currency, installment_number | Tutar, para birimi, taksit sayisi |
| is_three_d | 3D Secure odeme olup olmadigi |
| status | created, redirected, success, failed, cancelled, refunded |
| result_code, result_message | Basarisiz islemde hata kodu ve mesaji |
| completed_at, created_at, updated_at | Zaman bilgileri |

## Diger Moka United Servisleri

Iptal, iade, kart saklama, tekrarlayan odeme, raporlama gibi tum servislere ayarlarinizla yapilandirilmis istemci uzerinden erisebilirsiniz:

```python
from moka import models
from moka_django.client import get_moka_client

client = get_moka_client()

# Iade talebi
yanit = client.refunds().create(
    models.CreateRefundRequest(
        VirtualPosOrderId=payment.virtual_pos_order_id,
        Amount=50.25,
    )
)

# Odeme iptali
yanit = client.payments().cancel(
    models.CancelPaymentRequest(VirtualPosOrderId=payment.virtual_pos_order_id)
)

# Taksit tablosu
yanit = client.payments().retrieve_installment_info(
    models.RetrieveInstallmentInfoRequest(
        BinNumber="512754", Currency="TL", OrderAmount=1000, IsThreeD=1,
    )
)
```

Servislerin tam listesi ve ornekleri icin moka-python dokumantasyonuna bakiniz.

## Test Kartlari

Test ortaminda (ENVIRONMENT = "test") Moka United test kartlari kullanilabilir. Bu kartlarla yapilan odemeler bankaya gonderilmez; cevap Moka United sisteminden doner. Guncel test karti listesi icin resmi dokumantasyona bakiniz (liste zaman icinde degisebilir):

https://developer.mokaunited.com/home.php?page=test-kartlari

Gelistirme kolayligi icin kartlara moka-python icinden de erisilebilir:

```python
from moka import get_test_card

kart = get_test_card(bank="Garanti Bankasi")
```

## Testler

```bash
pip install Django moka-python
python runtests.py
```

Testler ag baglantisi gerektirmez; Moka istemcisi sahte yanitlarla taklit edilir ve callback dogrulamasi gercek hash kuraliyla test edilir.

## PyPI Yayinlama (twine)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Lisans

MIT lisansi ile dagitilmaktadir. Ayrintilar icin LICENSE dosyasina bakiniz.
