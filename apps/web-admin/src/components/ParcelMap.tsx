import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, GeoJSON, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Geometry } from "../lib/types";

export type MapFeature = { id: string; geometry: Geometry; label: string; ok?: boolean };

function FitBounds({ features }: { features: MapFeature[] }) {
  const map = useMap();
  const key = features.map((f) => f.id).join(",");
  useEffect(() => {
    const layer = L.geoJSON({ type: "FeatureCollection", features: features.map((f) => ({ type: "Feature", geometry: f.geometry, properties: {} })) } as any);
    const b = layer.getBounds();
    if (b.isValid()) map.fitBounds(b.pad(0.25), { maxZoom: 16 });
  }, [key, map]); // refit only when the set of parcels changes, not on every render
  return null;
}

/** Parcels on OpenStreetMap tiles. Green = EUDR-ready, amber = something missing. */
export function ParcelMap({ features, height = 320 }: { features: MapFeature[]; height?: number }) {
  if (!features.length) return <div className="map empty" style={{ height }}>Aucune parcelle géolocalisée</div>;
  return (
    <div className="map" style={{ height }}>
      <MapContainer center={[6.88, -6.45]} zoom={11} style={{ height: "100%" }} scrollWheelZoom={false}>
        <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {features.map((f) => {
          const color = f.ok === false ? "#c98a12" : "#1f8a4c";
          if (f.geometry.type === "Point") {
            const [lng, lat] = f.geometry.coordinates;
            return (
              <CircleMarker key={f.id} center={[lat, lng]} radius={7} pathOptions={{ color, fillOpacity: 0.6 }}>
                <Tooltip>{f.label}</Tooltip>
              </CircleMarker>
            );
          }
          return (
            <GeoJSON key={f.id} data={{ type: "Feature", geometry: f.geometry, properties: {} } as any} style={{ color, weight: 2, fillOpacity: 0.25 }}>
              <Tooltip sticky>{f.label}</Tooltip>
            </GeoJSON>
          );
        })}
        <FitBounds features={features} />
      </MapContainer>
    </div>
  );
}
