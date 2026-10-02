"""Parcel geometry as GeoJSON (RFC 7946: [longitude, latitude]).

Stored as JSON rather than PostGIS so the MVP runs anywhere; the EUDR export is GeoJSON anyway.
Move to PostGIS when we need spatial queries (overlap with protected forests, duplicates between parcels).
"""

import math
from typing import Any

from .errors import ApiError

EARTH_RADIUS_M = 6_371_008.8
# EUDR: plots above 4 ha must be described by a polygon, a single point is enough below.
EUDR_POLYGON_THRESHOLD_HA = 4.0


def _check_position(pos: Any) -> tuple[float, float]:
    if not (isinstance(pos, (list, tuple)) and len(pos) >= 2):
        raise ApiError(400, "invalid_geometry", "Coordonnée invalide")
    lng, lat = float(pos[0]), float(pos[1])
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        raise ApiError(400, "invalid_geometry", "Coordonnée hors limites (attendu [longitude, latitude])")
    return lng, lat


def validate_geometry(geometry: dict) -> dict:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Point":
        lng, lat = _check_position(coords)
        return {"type": "Point", "coordinates": [lng, lat]}
    if kind == "Polygon":
        if not coords or not isinstance(coords, list):
            raise ApiError(400, "invalid_geometry", "Polygone vide")
        ring = [list(_check_position(p)) for p in coords[0]]
        if len(ring) >= 3 and ring[0] != ring[-1]:
            ring.append(ring[0])  # tolerate unclosed rings drawn on a phone
        if len(ring) < 4:
            raise ApiError(400, "invalid_geometry", "Un polygone doit avoir au moins 3 sommets")
        return {"type": "Polygon", "coordinates": [ring]}
    raise ApiError(400, "invalid_geometry", "Géométrie attendue : Point ou Polygon")


def polygon_area_ha(geometry: dict) -> float | None:
    """Area of the outer ring, equirectangular projection around the centroid. Accurate to well under 1 %
    at parcel scale, which is plenty to cross-check the area a producer declares."""
    if geometry.get("type") != "Polygon":
        return None
    ring = geometry["coordinates"][0]
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    pts = [
        (math.radians(lng) * EARTH_RADIUS_M * math.cos(lat0), math.radians(lat) * EARTH_RADIUS_M)
        for lng, lat in ring
    ]
    twice_area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:]))
    return round(abs(twice_area) / 2 / 10_000, 2)


def centroid(geometry: dict) -> tuple[float, float]:
    if geometry["type"] == "Point":
        return tuple(geometry["coordinates"])  # type: ignore[return-value]
    ring = geometry["coordinates"][0][:-1]
    return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))


def eudr_issues(geometry: dict | None, area_ha: float | None, deforestation_status: str) -> list[str]:
    """Why a parcel is not yet acceptable in an EUDR due-diligence statement (empty list = ready)."""
    issues = []
    if not geometry:
        issues.append("missing_geometry")
    elif geometry["type"] == "Point" and (area_ha or 0) > EUDR_POLYGON_THRESHOLD_HA:
        issues.append("polygon_required_above_4ha")
    if deforestation_status == "flagged":
        issues.append("deforestation_flagged")
    elif deforestation_status == "unchecked":
        issues.append("deforestation_unchecked")
    return issues
