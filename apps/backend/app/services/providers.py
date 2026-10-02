"""Mobile-money disbursement providers.

`sandbox` makes the demo and the tests deterministic: every transfer succeeds immediately, except to an
account ending in "00", which fails (to demonstrate retries).

`cinetpay` is the production target (one API for Orange Money, MTN MoMo, Moov, Wave). The endpoint paths
below follow CinetPay's Transfer API as documented at the time of writing; **check them against the
current documentation and test in their sandbox before enabling it** (AGT_PAYMENT_PROVIDER=cinetpay).
"""

import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import settings
from ..core.ids import new_id
from ..models import Payment


@dataclass
class ProviderResult:
    status: str  # processing | success | failed
    external_ref: str | None = None
    reason: str | None = None


class PaymentProvider(Protocol):
    name: str

    async def send(self, payment: Payment) -> ProviderResult: ...


class SandboxProvider:
    name = "sandbox"

    async def send(self, payment: Payment) -> ProviderResult:
        if (payment.account or "").endswith("00"):
            return ProviderResult("failed", reason="Compte mobile money introuvable (sandbox)")
        return ProviderResult("success", external_ref=new_id("sbx"))


class CinetPayProvider:
    name = "cinetpay"
    base_url = "https://client.cinetpay.com/v1"

    async def _token(self, client: httpx.AsyncClient) -> str:
        r = await client.post(
            f"{self.base_url}/auth/login",
            data={"apikey": settings.cinetpay_api_key, "password": settings.cinetpay_password},
        )
        r.raise_for_status()
        return r.json()["data"]["token"]

    async def send(self, payment: Payment) -> ProviderResult:
        if not settings.cinetpay_api_key:
            return ProviderResult("failed", reason="CinetPay non configuré (AGT_CINETPAY_API_KEY)")
        account = payment.account or ""
        prefix, phone = account[1:4], account[4:]  # +225 0712345678 -> "225", "0712345678"
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                token = await self._token(client)
                r = await client.post(
                    f"{self.base_url}/transfer/money/send/contact",
                    params={"token": token, "lang": "fr"},
                    data={
                        "data": json.dumps(  # CinetPay expects a JSON string in a form field
                            [{
                                "prefix": prefix,
                                "phone": phone,
                                "amount": payment.amount,
                                "client_transaction_id": payment.id,
                                "notify_url": settings.cinetpay_notify_url,
                            }]
                        )
                    },
                )
                r.raise_for_status()
                body = r.json()
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                return ProviderResult("failed", reason=f"CinetPay: {exc}")
        if str(body.get("code")) != "0":
            return ProviderResult("failed", reason=f"CinetPay: {body.get('message')}")
        item = (body.get("data") or [[{}]])[0][0]
        return ProviderResult("processing", external_ref=item.get("transaction_id") or payment.id)


def get_provider() -> PaymentProvider:
    return CinetPayProvider() if settings.payment_provider == "cinetpay" else SandboxProvider()
