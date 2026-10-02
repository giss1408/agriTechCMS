"""API contracts. Field names match docs/technical/03-api.md."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .core.envelope import Schema
from .core.phone import normalize_phone

Role = Literal["super_admin", "admin", "collector"]
Product = Literal["cacao", "anacarde", "cafe", "hevea", "karite"]
Operator = Literal["orange_money", "mtn_momo", "wave", "moov_money"]


class PhoneModel(BaseModel):
    @field_validator("phone", "momo_account", mode="before", check_fields=False)
    @classmethod
    def _phone(cls, v):
        return normalize_phone(v) if v else v


# ---------------------------------------------------------------- auth & users


class OtpRequest(PhoneModel):
    phone: str


class OtpVerify(PhoneModel):
    phone: str
    otp: str = Field(pattern=r"^\d{6}$")
    device_id: str | None = Field(default=None, max_length=64)


class RefreshIn(BaseModel):
    refresh_token: str


class CooperativeBrief(Schema):
    id: str
    name: str
    code: str


class UserOut(Schema):
    id: str
    name: str
    phone: str
    role: str
    is_active: bool
    cooperative_id: str
    last_seen_at: datetime | None


class MeOut(UserOut):
    cooperative: CooperativeBrief
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: MeOut


class UserIn(PhoneModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str
    role: Role = "collector"


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    role: Role | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------- cooperative & settings


class CooperativeOut(Schema):
    id: str
    name: str
    code: str
    region: str | None
    phone: str | None
    rccm: str | None
    tax_id: str | None
    logo_url: str | None
    currency: str
    campaign_start_month: int
    current_campaign: str = ""


class CooperativePatch(PhoneModel):
    name: str | None = None
    region: str | None = None
    phone: str | None = None
    rccm: str | None = None
    tax_id: str | None = None
    logo_url: str | None = None


class AlertSettings(BaseModel):
    max_moisture_percent: Decimal = Field(gt=0, le=30)
    max_weight_kg: Decimal = Field(gt=0, le=100_000)


class PriceIn(BaseModel):
    product: Product
    quality: str = Field(min_length=1, max_length=10)
    price_per_kg: int = Field(gt=0, le=100_000)
    effective_from: date
    effective_to: date | None = None


class PricePatch(BaseModel):
    price_per_kg: int | None = Field(default=None, gt=0, le=100_000)
    effective_to: date | None = None


class PriceOut(Schema):
    id: str
    product: str
    quality: str
    price_per_kg: int
    currency: str = "XOF"
    effective_from: date
    effective_to: date | None


class ZoneIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ZoneOut(Schema):
    id: str
    name: str
    updated_at: datetime


# ---------------------------------------------------------------- producers & parcels


class Geometry(BaseModel):
    type: Literal["Point", "Polygon"]
    coordinates: Any


class ParcelIn(BaseModel):
    name: str | None = None
    crop: Product = "cacao"
    area_hectares: Decimal | None = Field(default=None, gt=0, le=10_000)
    planted_year: int | None = Field(default=None, ge=1900, le=2100)
    # Either a GeoJSON geometry, or the shorthand latitude/longitude for a point.
    geometry: Geometry | None = None
    latitude: float | None = None
    longitude: float | None = None


class ParcelPatch(BaseModel):
    name: str | None = None
    crop: Product | None = None
    area_hectares: Decimal | None = Field(default=None, gt=0)
    planted_year: int | None = None
    geometry: Geometry | None = None
    deforestation_status: Literal["unchecked", "clear", "flagged"] | None = None


class ParcelOut(Schema):
    id: str
    producer_id: str
    name: str | None
    crop: str
    area_hectares: Decimal | None
    measured_area_hectares: Decimal | None
    geometry: dict | None
    planted_year: int | None
    deforestation_status: str
    eudr_issues: list[str] = []
    updated_at: datetime


class MobileMoney(PhoneModel):
    operator: Operator
    account: str

    @field_validator("account", mode="before")
    @classmethod
    def _acc(cls, v):
        return normalize_phone(v)


class ProducerIn(PhoneModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = None
    cin_number: str | None = None
    gender: Literal["M", "F"] | None = None
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    zone_id: str | None = None
    membership_date: date | None = None
    mobile_money: MobileMoney | None = None
    notes: str | None = None
    parcels: list[ParcelIn] = []


class ProducerPatch(PhoneModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    cin_number: str | None = None
    gender: Literal["M", "F"] | None = None
    birth_year: int | None = None
    zone_id: str | None = None
    membership_date: date | None = None
    status: Literal["active", "inactive"] | None = None
    mobile_money: MobileMoney | None = None
    notes: str | None = None


class ProducerOut(Schema):
    id: str
    code: str
    first_name: str
    last_name: str
    full_name: str
    phone: str | None
    cin_number: str | None
    gender: str | None
    birth_year: int | None
    zone_id: str | None
    zone_name: str | None = None
    membership_date: date | None
    status: str
    momo_operator: str | None
    momo_account: str | None
    notes: str | None
    qr_payload: str = ""
    parcels: list[ParcelOut] = []
    updated_at: datetime


class BalanceOut(BaseModel):
    producer_id: str
    campaign: str
    total_delivered_kg: Decimal
    total_earned: int
    total_paid: int
    balance_due: int
    outstanding_advances: int
    net_payable: int
    pending_validation_amount: int
    last_delivery: date | None


class AdvanceIn(BaseModel):
    amount: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=200)
    given_at: date | None = None


class AdvanceOut(Schema):
    id: str
    producer_id: str
    amount: int
    remaining: int
    reason: str | None
    given_at: date


# ---------------------------------------------------------------- collections


class GpsIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class CollectionIn(BaseModel):
    client_uuid: str = Field(min_length=8, max_length=64)
    producer_id: str
    collected_at: datetime
    product: Product = "cacao"
    quality: str = Field(min_length=1, max_length=10)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    moisture_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=4, decimal_places=1)
    notes: str | None = Field(default=None, max_length=1000)
    photos: list[str] = []
    producer_signature: str | None = None
    gps: GpsIn | None = None


class CollectionPatch(BaseModel):
    quality: str | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0)
    moisture_percent: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    reason: str = Field(min_length=3, max_length=300, description="Why the admin edits a field collection")


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class BulkIds(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


class CollectionOut(Schema):
    id: str
    client_uuid: str
    reference: str
    producer_id: str
    producer_name: str = ""
    producer_code: str = ""
    collector_id: str
    collector_name: str = ""
    product: str
    quality: str
    weight_kg: Decimal
    moisture_percent: Decimal | None
    unit_price: int
    amount: int
    currency: str
    status: str
    collected_at: datetime
    collected_at_device: datetime
    clock_offset_seconds: int
    gps_lat: float | None
    gps_lng: float | None
    notes: str | None
    photo_ids: list[str]
    sync_source: str
    rejection_reason: str | None
    validated_at: datetime | None
    lot_id: str | None
    payment_id: str | None
    created_at: datetime
    updated_at: datetime


class CollectionTotals(BaseModel):
    count: int
    weight_kg: Decimal
    amount: int


# ---------------------------------------------------------------- sync


class SyncPushIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    device_time: datetime = Field(description="The phone's clock at the moment of sending")
    app_version: str | None = None
    pending_on_device: int = 0
    collections: list[CollectionIn] = Field(default=[], max_length=500)


class SyncAccepted(BaseModel):
    client_uuid: str
    id: str
    reference: str
    amount: int
    unit_price: int
    status: str
    duplicate: bool = False


class SyncRejected(BaseModel):
    client_uuid: str
    code: str
    message: str


class SyncPushOut(BaseModel):
    accepted: list[SyncAccepted]
    rejected: list[SyncRejected]
    clock_offset_seconds: int
    server_time: datetime


class SyncSettings(BaseModel):
    max_moisture_percent: Decimal
    max_weight_kg: Decimal
    campaign: str
    currency: str


class SyncPullOut(BaseModel):
    server_time: datetime
    cursor: datetime
    full: bool
    settings: SyncSettings
    producers: list[ProducerOut]
    prices: list[PriceOut]
    zones: list[ZoneOut]
    collections: list[CollectionOut]


class DeviceOut(Schema):
    id: str
    user_id: str
    user_name: str = ""
    app_version: str | None
    last_push_at: datetime | None
    last_pull_at: datetime | None
    last_clock_offset_seconds: int
    pending_on_device: int


# ---------------------------------------------------------------- lots


class LotIn(BaseModel):
    product: Product = "cacao"
    quality: str | None = None
    notes: str | None = None
    collection_ids: list[str] = []


class LotShipIn(BaseModel):
    buyer_name: str = Field(min_length=2, max_length=200)
    destination: str | None = None
    bags_count: int | None = Field(default=None, gt=0)


class LotOut(Schema):
    id: str
    reference: str
    product: str
    quality: str | None
    status: str
    total_weight_kg: Decimal
    collections_count: int
    bags_count: int | None
    buyer_name: str | None
    destination: str | None
    notes: str | None
    sealed_at: datetime | None
    shipped_at: datetime | None
    trace_url: str | None = None
    created_at: datetime


# ---------------------------------------------------------------- payments


class PaymentBatchIn(BaseModel):
    producer_ids: list[str] = []
    collection_ids: list[str] = []
    reference_note: str | None = Field(default=None, max_length=200)


class PaymentOut(Schema):
    id: str
    batch_id: str
    producer_id: str
    producer_name: str = ""
    gross_amount: int
    advance_deduction: int
    amount: int
    operator: str | None
    account: str | None
    status: str
    provider: str
    external_ref: str | None
    failure_reason: str | None
    attempts: int
    paid_at: datetime | None
    created_at: datetime


class PaymentBatchOut(BaseModel):
    batch_id: str
    total_amount: int
    count: int
    payments: list[PaymentOut]
    skipped: list[dict[str, str]]


class PayableOut(BaseModel):
    producer_id: str
    producer_name: str
    producer_code: str
    momo_operator: str | None
    momo_account: str | None
    collections_count: int
    gross_amount: int
    outstanding_advances: int
    net_amount: int
    oldest_collection_at: datetime


class WebhookIn(BaseModel):
    payment_id: str | None = None
    external_ref: str | None = None
    status: Literal["success", "failed"]
    trans_id: str | None = None
    reason: str | None = None
