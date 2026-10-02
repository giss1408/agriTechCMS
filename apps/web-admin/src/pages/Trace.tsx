import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { ParcelMap } from "../components/ParcelMap";
import { Badge, ErrorBox, Loading, Stat, Status } from "../components/ui";
import { api } from "../lib/api";
import { EUDR_ISSUE_LABEL, date, kg, num } from "../lib/format";
import type { Geometry, Trace } from "../lib/types";

/** Public page for buyers — reached from the lot link or the QR printed on the bags. No login. */
export function TracePage() {
  const { token } = useParams<{ token: string }>();
  const q = useQuery({ queryKey: ["trace", token], queryFn: () => api.get<Trace>(`/public/trace/${token}`) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <div className="main"><ErrorBox error={q.error} /></div>;
  const t = q.data!;
  const s = t.summary;
  const features = t.geojson.features.map((f) => ({
    id: String(f.properties.parcel_id),
    geometry: f.geometry as Geometry,
    label: `${f.properties.producer_code} · ${num(f.properties.area_ha as number)} ha`,
    ok: Boolean(f.properties.eudr_ready),
  }));

  return (
    <div className="main" style={{ margin: "0 auto" }}>
      <div className="stack">
        <div className="row">
          <div>
            <div className="muted small" style={{ textTransform: "uppercase", letterSpacing: ".06em", fontWeight: 650 }}>Fiche de traçabilité</div>
            <h1>{t.lot.reference}</h1>
            <div className="muted">{t.cooperative.name}{t.cooperative.region ? ` · ${t.cooperative.region}` : ""}</div>
          </div>
          <span className="spacer" />
          <Status value={t.lot.status} />
          <Badge tone={s.eudr_ready ? "success" : "warning"}>{s.eudr_ready ? "Géolocalisation complète" : "Géolocalisation incomplète"}</Badge>
        </div>

        <div className="grid grid-4">
          <Stat label="Poids du lot" value={kg(t.lot.total_weight_kg)} sub={`${t.lot.collections_count} livraisons · ${t.lot.bags_count ?? "?"} sacs`} />
          <Stat label="Producteurs" value={s.producers} sub={s.producers_without_parcel ? `${s.producers_without_parcel} sans parcelle enregistrée` : "tous avec parcelle"} />
          <Stat label="Parcelles conformes" value={`${s.parcels_eudr_ready} / ${s.parcels}`} sub="géolocalisées et vérifiées" />
          <Stat label="Période de collecte" value={date(s.first_collection_at)} sub={`au ${date(s.last_collection_at)}`} />
        </div>

        <ParcelMap features={features} height={420} />

        <div className="card table-wrap">
          <table>
            <thead><tr><th>Producteur</th><th className="num">Poids livré</th><th>Parcelles</th><th>Statut</th></tr></thead>
            <tbody>
              {t.producers.map((p) => (
                <tr key={p.code}>
                  <td><b>{p.name}</b> <span className="mono muted">{p.code}</span></td>
                  <td className="num">{kg(p.weight_kg)}</td>
                  <td className="small">
                    {p.parcels.length === 0 ? "Aucune parcelle enregistrée" : p.parcels.map((x) => (
                      <div key={x.id}>
                        {x.geometry_type === "Polygon" ? "Polygone" : x.geometry_type === "Point" ? "Point GPS" : "—"} · {num(x.area_hectares)} ha
                        {x.eudr_issues.length > 0 && <span className="muted"> — {x.eudr_issues.map((i) => EUDR_ISSUE_LABEL[i] ?? i).join(", ")}</span>}
                      </div>
                    ))}
                  </td>
                  <td><Badge tone={p.eudr_ready ? "success" : "warning"}>{p.eudr_ready ? "Conforme" : "À compléter"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">
          Données déclarées par la coopérative. Aucune donnée personnelle (téléphone, pièce d'identité) n'est publiée.
          {t.lot.buyer_name && ` Lot expédié à ${t.lot.buyer_name}${t.lot.shipped_at ? ` le ${date(t.lot.shipped_at)}` : ""}.`}
        </p>
      </div>
    </div>
  );
}
