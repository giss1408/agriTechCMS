# 0002 — Lots as a first-class entity

**Context.** The v0 spec promised "traceability by lot", a buyer portal and QR codes on bags, but had no lot
in its data model: there was no way to say which deliveries ended up in which shipment.

**Decision.** `lots` table; a validated collection belongs to at most one lot. Lifecycle open → sealed →
shipped. Sealing freezes the content and issues an unguessable public token; the buyer page and the GeoJSON
export are computed from lot → collections → producers → parcels of the same crop.

**Consequences.** Traceability is real and testable. Producer-level (not parcel-level) attribution: a
collection is not tied to a specific parcel; all of the producer's parcels for that crop are declared, which
is what EUDR due-diligence statements accept for smallholders. Mass-balance mixing at warehouse level is out of scope.
