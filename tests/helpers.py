"""Test yardimcilari: sahte Moka istemcisi."""

import json

from moka import ApiResponse


def make_response(payload):
    return ApiResponse(json.dumps(payload))


SUCCESS_PAYMENT_RESPONSE = {
    "Data": {
        "IsSuccessful": True,
        "ResultCode": "",
        "ResultMessage": "",
        "VirtualPosOrderId": "ORDER-TEST-123",
    },
    "ResultCode": "Success",
    "ResultMessage": "",
    "Exception": None,
}

BANK_DECLINED_RESPONSE = {
    "Data": {
        "IsSuccessful": False,
        "ResultCode": "002",
        "ResultMessage": "Limit Yetersiz",
        "VirtualPosOrderId": "",
    },
    "ResultCode": "Success",
    "ResultMessage": "",
    "Exception": None,
}

THREEDS_START_RESPONSE = {
    "Data": {
        "Url": "https://service.refmokaunited.com/PaymentDealerThreeDProcess?threeDTrxCode=abc",
        "CodeForHash": "9FDFBDFC-42C5-417E-AA93-E4D9D5312AAC",
    },
    "ResultCode": "Success",
    "ResultMessage": "",
    "Exception": None,
}

INVALID_ACCOUNT_RESPONSE = {
    "Data": None,
    "ResultCode": "PaymentDealer.CheckPaymentDealerAuthentication.InvalidAccount",
    "ResultMessage": "",
    "Exception": None,
}


class FakePaymentService:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def create(self, request):
        self.requests.append(request)
        return self.response

    def create_threeds(self, request):
        self.requests.append(request)
        return self.response


class FakeMokaClient:
    def __init__(self, response_payload):
        self.payment_service = FakePaymentService(make_response(response_payload))

    def payments(self):
        return self.payment_service

    @property
    def last_request(self):
        return self.payment_service.requests[-1]
