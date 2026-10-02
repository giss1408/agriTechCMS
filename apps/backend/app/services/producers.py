import csv
import io
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import geo
from ..core.errors import ApiError, not_found
from ..models import Parcel, Producer, User, Zone
from ..schemas import ParcelIn, ParcelOut, ProducerIn, ProducerOut
from . import audit

QR_PREFIX = "AGT1"  # versioned so the card format can evolve


def qr_payload(producer: Producer) -> str:
    return f"{QR_PREFIX}:{producer.id}:{producer.code}"


def parcel_out(p: Parcel) -> ParcelOut:
    out = ParcelOut.model_validate(p)
    area = float(p.measured_area_hectares or p.area_hectares or 0) or None
    out.eudr_issues = geo.eudr_issues(p.geometry, area, p.deforestation_status)
    return out


def producer_out(p: Producer) -> ProducerOut:
    out = ProducerOut.model_validate(p)
    out.zone_name = p.zone.name if p.zone else None
    out.qr_payload = qr_payload(p)
    out.parcels = [parcel_out(x) for x in p.parcels]
    return out


async def get_for(db: AsyncSession, user: User, producer_id: str) -> Producer:
    p = await db.get(Producer, producer_id)
    if not p or p.cooperative_id != user.cooperative_id:
        raise not_found("Producteur")
    return p


async def _check_zone(db: AsyncSession, user: User, zone_id: str | None) -> None:
    if zone_id:
        zone = await db.get(Zone, zone_id)
        if not zone or zone.cooperative_id != user.cooperative_id:
            raise ApiError(422, "unknown_zone", "Zone inconnue")


def build_parcel(user: User, producer_id: str, data: ParcelIn) -> Parcel:
    geometry = None
    if data.geometry:
        geometry = geo.validate_geometry(data.geometry.model_dump())
    elif data.latitude is not None and data.longitude is not None:
        geometry = geo.validate_geometry({"type": "Point", "coordinates": [data.longitude, data.latitude]})
    measured = geo.polygon_area_ha(geometry) if geometry else None
    return Parcel(
        cooperative_id=user.cooperative_id,
        producer_id=producer_id,
        name=data.name,
        crop=data.crop,
        area_hectares=data.area_hectares,
        measured_area_hectares=Decimal(str(measured)) if measured is not None else None,
        geometry=geometry,
        planted_year=data.planted_year,
    )


async def create(db: AsyncSession, user: User, data: ProducerIn) -> Producer:
    await _check_zone(db, user, data.zone_id)
    coop = user.cooperative
    coop.producer_seq += 1
    producer = Producer(
        cooperative_id=coop.id,
        code=f"{coop.code}-{coop.producer_seq:05d}",
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        phone=data.phone,
        cin_number=data.cin_number,
        gender=data.gender,
        birth_year=data.birth_year,
        zone_id=data.zone_id,
        membership_date=data.membership_date,
        momo_operator=data.mobile_money.operator if data.mobile_money else None,
        momo_account=data.mobile_money.account if data.mobile_money else None,
        notes=data.notes,
    )
    db.add(producer)
    await db.flush()
    for parcel in data.parcels:
        db.add(build_parcel(user, producer.id, parcel))
    audit.record(db, cooperative_id=coop.id, actor_id=user.id, entity="producer", entity_id=producer.id, action="created")
    await db.flush()
    await db.refresh(producer, ["parcels", "zone"])
    return producer


IMPORT_COLUMNS = [
    "first_name", "last_name", "phone", "gender", "birth_year", "zone", "cin_number",
    "momo_operator", "momo_account", "latitude", "longitude", "area_hectares", "crop",
]


async def import_csv(db: AsyncSession, user: User, content: bytes) -> dict:
    """Bulk import from the spreadsheet a cooperative already keeps. Bad rows are reported, good rows imported."""
    text = content.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text.splitlines()[0] if text else ",", delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    zones = {z.name.lower(): z for z in (await db.execute(select(Zone).where(Zone.cooperative_id == user.cooperative_id))).scalars()}
    created, errors = 0, []
    for line, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        try:
            zone_id = None
            if row.get("zone"):
                zone = zones.get(row["zone"].lower())
                if not zone:
                    zone = Zone(cooperative_id=user.cooperative_id, name=row["zone"])
                    db.add(zone)
                    await db.flush()
                    zones[zone.name.lower()] = zone
                zone_id = zone.id
            parcels = []
            if row.get("latitude") and row.get("longitude"):
                parcels.append(ParcelIn(
                    latitude=float(row["latitude"].replace(",", ".")),
                    longitude=float(row["longitude"].replace(",", ".")),
                    area_hectares=Decimal(row["area_hectares"].replace(",", ".")) if row.get("area_hectares") else None,
                    crop=row.get("crop") or "cacao",
                ))
            momo = None
            if row.get("momo_operator") and row.get("momo_account"):
                momo = {"operator": row["momo_operator"], "account": row["momo_account"]}
            data = ProducerIn(
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                phone=row.get("phone") or None,
                gender=(row.get("gender") or "").upper()[:1] or None,
                birth_year=int(row["birth_year"]) if row.get("birth_year") else None,
                cin_number=row.get("cin_number") or None,
                zone_id=zone_id,
                mobile_money=momo,
                parcels=parcels,
            )
            await create(db, user, data)
            created += 1
        except (ValidationError, ValueError, InvalidOperation) as exc:
            errors.append({"line": line, "message": str(exc).splitlines()[0][:200]})
        except ApiError as exc:
            errors.append({"line": line, "message": exc.message})
    return {"created": created, "errors": errors, "expected_columns": IMPORT_COLUMNS}
