# 0004 — Parcels as GeoJSON before PostGIS

**Context.** EUDR needs point (≤ 4 ha) or polygon (> 4 ha) per plot and accepts GeoJSON. The MVP must run on
a laptop with SQLite for demos.

**Decision.** Store validated GeoJSON in a JSON column; compute polygon area in Python (equirectangular
projection, accurate well under 1 % at parcel scale); expose EUDR issues per parcel.

**Consequences.** No spatial queries yet (overlaps, protected areas). Migration path: add a PostGIS geometry
column populated from the JSON, with a GiST index, when those checks are built.
