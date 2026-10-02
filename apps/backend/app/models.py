"""Domain model. Every business row carries `cooperative_id`: tenancy is enforced in every query.

Money is integer XOF (the franc CFA has no subunit in practice). Weights are Decimal kilograms.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .core.ids import new_id
from .core.timeutil import UTCDateTime, utcnow


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime, dict[str, Any]: JSON, list[Any]: JSON}


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    # Indexed: the mobile app pulls "everything changed since <cursor>".
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, index=True)


def _pk(prefix: str):
    return mapped_column(String(40), primary_key=True, default=lambda: new_id(prefix))


def _coop_fk():
    return mapped_column(ForeignKey("cooperatives.id"), index=True)


# ---------------------------------------------------------------- tenancy & people


class Cooperative(Timestamped, Base):
    __tablename__ = "cooperatives"
    id: Mapped[str] = _pk("coop")
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(8), unique=True)  # prefix of producer codes: DAL-00042
    region: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    rccm: Mapped[str | None] = mapped_column(String(50))
    tax_id: Mapped[str | None] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    campaign_start_month: Mapped[int] = mapped_column(default=10)
    max_moisture_percent: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("8.0"))
    max_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1000"))
    producer_seq: Mapped[int] = mapped_column(default=0)
    lot_seq: Mapped[int] = mapped_column(default=0)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[str] = _pk("usr")
    cooperative_id: Mapped[str] = _coop_fk()
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20), unique=True)  # login identity
    role: Mapped[str] = mapped_column(String(20))  # super_admin | admin | collector
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None]

    cooperative: Mapped[Cooperative] = relationship(lazy="joined")


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"
    id: Mapped[str] = _pk("otp")
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    consumed_at: Mapped[datetime | None]


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = _pk("rt")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    device_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]


class Zone(Timestamped, Base):
    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("cooperative_id", "name"),)
    id: Mapped[str] = _pk("zone")
    cooperative_id: Mapped[str] = _coop_fk()
    name: Mapped[str] = mapped_column(String(100))


class Producer(Timestamped, Base):
    __tablename__ = "producers"
    __table_args__ = (UniqueConstraint("cooperative_id", "code"), Index("ix_producers_coop_phone", "cooperative_id", "phone"))
    id: Mapped[str] = _pk("prod")
    cooperative_id: Mapped[str] = _coop_fk()
    code: Mapped[str] = mapped_column(String(20))  # printed on the QR card
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    cin_number: Mapped[str | None] = mapped_column(String(30))
    gender: Mapped[str | None] = mapped_column(String(1))
    birth_year: Mapped[int | None]
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.id"))
    membership_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | inactive
    momo_operator: Mapped[str | None] = mapped_column(String(20))  # orange_money | mtn_momo | wave | moov_money
    momo_account: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)

    parcels: Mapped[list["Parcel"]] = relationship(back_populates="producer", lazy="selectin")
    zone: Mapped[Zone | None] = relationship(lazy="joined")

    @property
    def full_name(self) -> str:
        return f"{self.last_name.upper()} {self.first_name}"


class Parcel(Timestamped, Base):
    __tablename__ = "parcels"
    id: Mapped[str] = _pk("parc")
    cooperative_id: Mapped[str] = _coop_fk()
    producer_id: Mapped[str] = mapped_column(ForeignKey("producers.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    crop: Mapped[str] = mapped_column(String(30))
    area_hectares: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))  # declared
    measured_area_hectares: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))  # from polygon
    geometry: Mapped[dict[str, Any] | None]  # GeoJSON Point or Polygon
    planted_year: Mapped[int | None]
    deforestation_status: Mapped[str] = mapped_column(String(10), default="unchecked")  # unchecked|clear|flagged

    producer: Mapped[Producer] = relationship(back_populates="parcels")


# ---------------------------------------------------------------- pricing & collections


class PurchasePrice(Timestamped, Base):
    """Versioned: a collection is valued with the price in force on its collection date."""

    __tablename__ = "purchase_prices"
    id: Mapped[str] = _pk("price")
    cooperative_id: Mapped[str] = _coop_fk()
    product: Mapped[str] = mapped_column(String(30))
    quality: Mapped[str] = mapped_column(String(10))
    price_per_kg: Mapped[int]
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class Collection(Timestamped, Base):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("cooperative_id", "client_uuid", name="uq_collection_client_uuid"),
        Index("ix_collections_coop_status", "cooperative_id", "status"),
        Index("ix_collections_coop_collected", "cooperative_id", "collected_at"),
    )
    id: Mapped[str] = _pk("col")
    cooperative_id: Mapped[str] = _coop_fk()
    client_uuid: Mapped[str] = mapped_column(String(64))  # created on the phone: the idempotency key
    reference: Mapped[str] = mapped_column(String(30))
    producer_id: Mapped[str] = mapped_column(ForeignKey("producers.id"), index=True)
    collector_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product: Mapped[str] = mapped_column(String(30))
    quality: Mapped[str] = mapped_column(String(10))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    moisture_percent: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    unit_price: Mapped[int]
    amount: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="XOF")
    # pending_validation -> validated -> paid ; pending_validation -> rejected ; any non-paid -> cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending_validation")
    collected_at: Mapped[datetime]  # clock-corrected
    collected_at_device: Mapped[datetime]  # as typed on the phone, kept for audit
    clock_offset_seconds: Mapped[int] = mapped_column(default=0)
    gps_lat: Mapped[float | None]
    gps_lng: Mapped[float | None]
    notes: Mapped[str | None] = mapped_column(Text)
    photo_ids: Mapped[list[Any]] = mapped_column(default=list)
    producer_signature: Mapped[str | None] = mapped_column(Text)
    sync_source: Mapped[str] = mapped_column(String(20))  # online | offline_mobile | web | import
    device_id: Mapped[str | None] = mapped_column(String(64))
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    validated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    validated_at: Mapped[datetime | None]
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("lots.id"), index=True)
    payment_id: Mapped[str | None] = mapped_column(ForeignKey("payments.id"), index=True)

    producer: Mapped[Producer] = relationship(lazy="joined")
    collector: Mapped[User] = relationship(lazy="joined", foreign_keys=[collector_id])


class Lot(Timestamped, Base):
    """A batch of bags sold to a buyer. The link collection -> lot -> buyer is what traceability is about."""

    __tablename__ = "lots"
    __table_args__ = (UniqueConstraint("cooperative_id", "reference"),)
    id: Mapped[str] = _pk("lot")
    cooperative_id: Mapped[str] = _coop_fk()
    reference: Mapped[str] = mapped_column(String(30))
    product: Mapped[str] = mapped_column(String(30))
    quality: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), default="open")  # open -> sealed -> shipped
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    collections_count: Mapped[int] = mapped_column(default=0)
    bags_count: Mapped[int | None]
    buyer_name: Mapped[str | None] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    sealed_at: Mapped[datetime | None]
    shipped_at: Mapped[datetime | None]
    trace_token: Mapped[str | None] = mapped_column(String(40), unique=True)  # public buyer link, set on seal


# ---------------------------------------------------------------- money


class Advance(Timestamped, Base):
    """Cash advanced to a producer before harvest, recovered on later payments (oldest first)."""

    __tablename__ = "advances"
    id: Mapped[str] = _pk("adv")
    cooperative_id: Mapped[str] = _coop_fk()
    producer_id: Mapped[str] = mapped_column(ForeignKey("producers.id"), index=True)
    amount: Mapped[int]
    remaining: Mapped[int]
    reason: Mapped[str | None] = mapped_column(String(200))
    given_at: Mapped[date] = mapped_column(Date)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class PaymentBatch(Timestamped, Base):
    __tablename__ = "payment_batches"
    id: Mapped[str] = _pk("pbat")
    cooperative_id: Mapped[str] = _coop_fk()
    reference_note: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    total_amount: Mapped[int] = mapped_column(default=0)
    count: Mapped[int] = mapped_column(default=0)


class Payment(Timestamped, Base):
    """One mobile-money transfer to one producer, covering one or more validated collections."""

    __tablename__ = "payments"
    id: Mapped[str] = _pk("pay")
    cooperative_id: Mapped[str] = _coop_fk()
    batch_id: Mapped[str] = mapped_column(ForeignKey("payment_batches.id"), index=True)
    producer_id: Mapped[str] = mapped_column(ForeignKey("producers.id"), index=True)
    gross_amount: Mapped[int]  # sum of the collections
    advance_deduction: Mapped[int] = mapped_column(default=0)
    amount: Mapped[int]  # actually sent
    advance_allocations: Mapped[list[Any]] = mapped_column(default=list)  # [{"advance_id", "amount"}]
    operator: Mapped[str | None] = mapped_column(String(20))
    account: Mapped[str | None] = mapped_column(String(20))
    # initiated -> processing -> success | failed ; failed -> processing (retry) | cancelled
    status: Mapped[str] = mapped_column(String(12), default="initiated")
    provider: Mapped[str] = mapped_column(String(20))
    external_ref: Mapped[str | None] = mapped_column(String(100), index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    attempts: Mapped[int] = mapped_column(default=0)
    paid_at: Mapped[datetime | None]

    producer: Mapped[Producer] = relationship(lazy="joined")


# ---------------------------------------------------------------- support


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = _pk("img")
    cooperative_id: Mapped[str] = _coop_fk()
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class SyncDevice(Base):
    __tablename__ = "sync_devices"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # device uuid generated by the app
    cooperative_id: Mapped[str] = _coop_fk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    app_version: Mapped[str | None] = mapped_column(String(20))
    last_push_at: Mapped[datetime | None]
    last_pull_at: Mapped[datetime | None]
    last_clock_offset_seconds: Mapped[int] = mapped_column(default=0)
    pending_on_device: Mapped[int] = mapped_column(default=0)


class AuditEvent(Base):
    """Append-only: who changed what, when. Required for trust in weights and amounts."""

    __tablename__ = "audit_events"
    id: Mapped[str] = _pk("evt")
    cooperative_id: Mapped[str] = _coop_fk()
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(30))
    changes: Mapped[dict[str, Any]] = mapped_column(default=dict)
    at: Mapped[datetime] = mapped_column(default=utcnow)


class Notification(Base):
    """Outgoing SMS. With the console provider this table *is* the SMS gateway (visible in the demo)."""

    __tablename__ = "notifications"
    id: Mapped[str] = _pk("sms")
    cooperative_id: Mapped[str | None] = mapped_column(ForeignKey("cooperatives.id"), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))  # otp | payment | info
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="sent")
    provider: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
