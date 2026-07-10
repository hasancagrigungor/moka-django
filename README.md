# moka-django

> **Bu kütüphane bağımsız olarak geliştirilmiştir; Moka United'ın resmi ürünü değildir, Moka United tarafından geliştirilmemiş, onaylanmamış ve desteklenmemektedir.**

Moka United sanal POS entegrasyonu için Django uygulaması.

Bu paket, [moka-python](https://pypi.org/project/moka-python/) kütüphanesinin üstüne Django projelerinde ihtiyaç duyulan katmanı ekler: ödeme kaydı tutan model, 3D Secure callback doğrulama görünümü, ödeme başlatma fonksiyonları, sinyaller ve admin entegrasyonu. Moka United API'sinin tamamına (kart saklama, tekrarlayan ödeme, raporlama vb.) moka-python istemcisi üzerinden erişilebilir.

## Özellikler

- settings.py üzerinden yapılandırma (test / canlı ortam seçimi)
- Non-3D ödeme akışı: tek fonksiyonla ödeme yap, sonucu veritabanına işle
- 3D Secure ödeme akışı: ödeme başlat, CodeForHash değerini sakla, kullanıcıyı bankaya yönlendir
- Hazır callback görünümü: hashValue doğrulaması (SHA-256, T/F kuralı), kayıt güncelleme ve yönlendirme
- moka_payment_succeeded ve moka_payment_failed sinyalleri
- MokaPayment modeli ve Django admin kaydı
- Saklı kartla (CardToken) ödeme desteği
- Moka United API'sinin tüm servislerine get_moka_client ile doğrudan erişim
- Test kartlarıyla çalışan kapsamlı test paketi

## Gereksinimler

- Python 3.8 ve üzeri
- Django 3.2 ve üzeri
- moka-python

## Kurulum

```bash
pip install moka-django
```

settings.py dosyanıza uygulamayı ve ayarları ekleyin:

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

Ana urls.py dosyanıza callback adresini ekleyin:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("moka/", include("moka_django.urls")),
]
```

Veritabanı tablosunu oluşturun:

```bash
python manage.py migrate moka_django
```

### Ayarlar

| Ayar | Zorunlu | Varsayılan | Açıklama |
| --- | --- | --- | --- |
| DEALER_CODE | Evet | - | Moka United bayi kodu |
| USERNAME | Evet | - | API kullanıcı adı |
| PASSWORD | Evet | - | API şifresi |
| ENVIRONMENT | Hayır | "test" | "test": service.refmokaunited.com, "production": service.mokaunited.com |
| BASE_URL | Hayır | None | Verilirse ENVIRONMENT ayarını ezer (örneğin eski service.refmoka.com adresi için) |
| SOFTWARE | Hayır | "moka-django" | İsteklerde gönderilen yazılım adı |
| TIMEOUT | Hayır | 30 | HTTP istek zaman aşımı (saniye) |
| CALLBACK_SUCCESS_URL | Hayır | "/" | Başarılı 3D ödemede yönlendirilecek adres |
| CALLBACK_FAIL_URL | Hayır | "/" | Başarısız 3D ödemede yönlendirilecek adres |

CheckKey değeri (DealerCode + "MK" + Username + "PD" + Password bilgisinin SHA-256 özeti) her istekte otomatik üretilir.

## 3D Secure ile Ödeme

Önerilen akış 3D Secure'dur. Ödeme başlatılır, kullanıcı bankanın doğrulama sayfasına yönlendirilir, sonuç callback adresinize POST edilir:

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

Kart doğrulaması tamamlandığında Moka United, callback adresinize hashValue, resultCode, resultMessage, trxCode ve OtherTrxCode alanlarını POST eder. Paketin hazır MokaCallbackView görünümü bu isteği alır, hashValue değerini SHA-256 kuralıyla doğrular (CodeForHash + "T" başarılı, CodeForHash + "F" başarısız), MokaPayment kaydını günceller, ilgili sinyali gönderir ve kullanıcıyı CALLBACK_SUCCESS_URL veya CALLBACK_FAIL_URL adresine `?payment=<other_trx_code>` parametresiyle yönlendirir.

### Sinyaller

Ödeme sonucuna göre is mantığınızı sinyallerle bağlayın:

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

### Callback davranışını özelleştirme

```python
from django.shortcuts import render

from moka_django.views import MokaCallbackView


class OzelCallbackView(MokaCallbackView):
    def on_success(self, request, payment):
        return render(request, "tesekkurler.html", {"payment": payment})

    def on_failure(self, request, payment):
        return render(request, "odeme_hata.html", {"payment": payment})
```

Bu durumda urls.py dosyanızda hazır `moka_django.urls` yerine kendi görünümünüzü bağlayın:

```python
path("moka/callback/", OzelCallbackView.as_view(), name="moka-callback"),
```

## 3D Secure Olmadan Ödeme (Non-3D)

Bayinizin Non-3D işlem yetkisi varsa tek adımda ödeme alabilirsiniz:

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

### Saklı kartla ödeme

```python
payment, response = create_payment(amount="100.50", card_token="kart tokeni")
```

### Ek API alanları

CreatePaymentRequest üzerindeki diğer alanlar `extra` sözlüğüyle gönderilir:

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

Her ödeme girisimi veritabanına kaydedilir:

| Alan | Açıklama |
| --- | --- |
| other_trx_code | Moka United'a gönderilen benzersiz işlem kodu (OtherTrxCode) |
| code_for_hash | 3D ödemede saklanan doğrulama kodu (CodeForHash) |
| virtual_pos_order_id | Başarılı işlemde dönen sipariş numarası; iptal ve iade işlemlerinde kullanılır |
| amount, currency, installment_number | Tutar, para birimi, taksit sayısı |
| is_three_d | 3D Secure ödeme olup olmadığı |
| status | created, redirected, success, failed, cancelled, refunded |
| result_code, result_message | Başarısız işlemde hata kodu ve mesajı |
| completed_at, created_at, updated_at | Zaman bilgileri |

## Diğer Moka United Servisleri

İptal, iade, kart saklama, tekrarlayan ödeme, raporlama gibi tüm servislere ayarlarınızla yapılandırılmış istemci üzerinden erişebilirsiniz:

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

Servislerin tam listesi ve örnekleri için moka-python dokümantasyonuna bakınız.

## Test Kartları

Test ortamında (ENVIRONMENT = "test") Moka United test kartları kullanılabilir. Bu kartlarla yapılan ödemeler bankaya gönderilmez; cevap Moka United sisteminden döner. Güncel test kartı listesi için resmi dokümantasyona bakınız (liste zaman içinde değişebilir):

https://developer.mokaunited.com/home.php?page=test-kartlari

Geliştirme kolaylığı için kartlara moka-python içinden de erişilebilir:

```python
from moka import get_test_card

kart = get_test_card(bank="Garanti Bankasi")
```

## Testler

```bash
pip install Django moka-python
python runtests.py
```

Testler ağ bağlantısı gerektirmez; Moka istemcisi sahte yanıtlarla taklit edilir ve callback doğrulaması gerçek hash kuralıyla test edilir.

## PyPI Yayınlama (twine)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Lisans

MIT lisansı ile dağıtılmaktadır. Ayrıntılar için LICENSE dosyasına bakınız.
