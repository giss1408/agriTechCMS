import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ParcelMap } from "../components/ParcelMap";
import { Badge, ErrorBox, Loading, Modal, PageHead, Stat, Status, Tabs, useToast } from "../components/ui";
import { api, imageUrl } from "../lib/api";
import { EUDR_ISSUE_LABEL, OPERATOR_LABEL, date, dateTime, fcfa, kg, num } from "../lib/format";
import type { Advance, Balance, Collection, Parcel, Payment, Producer } from "../lib/types";

type Tab = "identity" | "parcels" | "collections" | "money" | "card";

export function ProducerPage() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<Tab>("identity");
  const q = useQuery({ queryKey: ["producer", id], queryFn: () => api.get<Producer>(`/producers/${id}`) });
  const balance = useQuery({ queryKey: ["producer", id, "balance"], queryFn: () => api.get<Balance>(`/producers/${id}/balance`) });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const p = q.data!;
  const b = balance.data;

  return (
    <div className="stack">
      <div className="muted small"><Link to="/producers">← Adhérents</Link></div>
      <PageHead title={p.full_name} subtitle={<><span className="mono">{p.code}</span> · {p.zone_name ?? "sans zone"} · <Status value={p.status} /></>} />
      {b && (
        <div className="grid grid-4">
          <Stat label={`Livré (${b.campaign})`} value={kg(b.total_delivered_kg)} sub={b.last_delivery ? `dernière livraison le ${date(b.last_delivery)}` : "aucune livraison"} />
          <Stat label="Gagné" value={fcfa(b.total_earned)} sub={b.pending_validation_amount ? `+ ${fcfa(b.pending_validation_amount)} en vérification` : undefined} />
          <Stat label="Payé" value={fcfa(b.total_paid)} />
          <Stat label="Reste à payer" value={fcfa(b.net_payable)} sub={b.outstanding_advances ? `après déduction de ${fcfa(b.outstanding_advances)} d'avance` : undefined} accent />
        </div>
      )}
      <Tabs<Tab> value={tab} onChange={setTab} tabs={[["identity", "Identité"], ["parcels", `Parcelles (${p.parcels.length})`], ["collections", "Livraisons"], ["money", "Paiements & avances"], ["card", "Carte QR"]]} />
      {tab === "identity" && <Identity p={p} />}
      {tab === "parcels" && <Parcels p={p} />}
      {tab === "collections" && <Deliveries producerId={p.id} />}
      {tab === "money" && <Money producerId={p.id} />}
      {tab === "card" && <QrCard p={p} />}
    </div>
  );
}

function Identity({ p }: { p: Producer }) {
  return (
    <div className="card card-body">
      <dl className="kv">
        <dt>Téléphone</dt><dd>{p.phone ?? "—"}</dd>
        <dt>Mobile money</dt><dd>{p.momo_operator ? `${OPERATOR_LABEL[p.momo_operator]} · ${p.momo_account}` : <Badge tone="warning">Non renseigné : paiement impossible</Badge>}</dd>
        <dt>Sexe</dt><dd>{p.gender === "F" ? "Femme" : p.gender === "M" ? "Homme" : "—"}</dd>
        <dt>Année de naissance</dt><dd>{p.birth_year ?? "—"}</dd>
        <dt>N° CNI</dt><dd>{p.cin_number ?? "—"}</dd>
        <dt>Adhérent depuis</dt><dd>{date(p.membership_date)}</dd>
        {p.notes && <><dt>Notes</dt><dd>{p.notes}</dd></>}
      </dl>
    </div>
  );
}

function Parcels({ p }: { p: Producer }) {
  const qc = useQueryClient();
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Parcel["deforestation_status"] }) => api.patch<Parcel>(`/parcels/${id}`, { deforestation_status: status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["producer", p.id] }),
  });
  const features = p.parcels.filter((x) => x.geometry).map((x) => ({ id: x.id, geometry: x.geometry!, label: `${x.crop} · ${num(x.measured_area_hectares ?? x.area_hectares)} ha`, ok: x.eudr_issues.length === 0 }));
  return (
    <div className="grid grid-3-1">
      <ParcelMap features={features} height={380} />
      <div className="stack">
        {p.parcels.length === 0 && <div className="card card-body muted">Aucune parcelle. Le collecteur peut l'ajouter depuis l'application (point GPS) ou vous pouvez importer un polygone.</div>}
        {p.parcels.map((x) => (
          <div className="card card-body stack" key={x.id} style={{ gap: 8 }}>
            <div className="row">
              <b>{x.name ?? `Parcelle ${x.crop}`}</b>
              <span className="spacer" />
              <Badge tone={x.eudr_issues.length ? "warning" : "success"}>{x.eudr_issues.length ? "Incomplète" : "Prête EUDR"}</Badge>
            </div>
            <div className="small muted">
              {x.geometry?.type === "Polygon" ? "Polygone" : x.geometry ? "Point GPS" : "Non géolocalisée"} · déclarée {num(x.area_hectares)} ha
              {x.measured_area_hectares && ` · mesurée ${num(x.measured_area_hectares)} ha`} {x.planted_year && `· plantée en ${x.planted_year}`}
            </div>
            {x.eudr_issues.map((i) => <div key={i} className="small">⚠ {EUDR_ISSUE_LABEL[i] ?? i}</div>)}
            <label className="field">Contrôle déforestation
              <select value={x.deforestation_status} onChange={(e) => setStatus.mutate({ id: x.id, status: e.target.value as Parcel["deforestation_status"] })}>
                <option value="unchecked">Non vérifiée</option><option value="clear">Vérifiée — conforme</option><option value="flagged">Alerte</option>
              </select>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}

function Deliveries({ producerId }: { producerId: string }) {
  const q = useQuery({ queryKey: ["collections", { producer_id: producerId }], queryFn: () => api.get<Collection[]>("/collections", { producer_id: producerId, per_page: 100 }) });
  if (q.isLoading) return <Loading />;
  return (
    <div className="card table-wrap">
      <table>
        <thead><tr><th>Date</th><th>Référence</th><th>Qualité</th><th className="num">Poids</th><th className="num">Prix</th><th className="num">Montant</th><th>Statut</th></tr></thead>
        <tbody>
          {q.data?.map((c) => (
            <tr key={c.id}><td>{dateTime(c.collected_at)}</td><td className="mono">{c.reference}</td><td>{c.quality}</td>
              <td className="num">{num(c.weight_kg)} kg</td><td className="num">{fcfa(c.unit_price)}</td><td className="num">{fcfa(c.amount)}</td><td><Status value={c.status} /></td></tr>
          ))}
          {!q.data?.length && <tr><td colSpan={7} className="muted">Aucune livraison.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function Money({ producerId }: { producerId: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const payments = useQuery({ queryKey: ["payments", { producer_id: producerId }], queryFn: () => api.get<Payment[]>("/payments", { producer_id: producerId }) });
  const advances = useQuery({ queryKey: ["advances", producerId], queryFn: () => api.get<Advance[]>(`/producers/${producerId}/advances`) });
  const add = useMutation({
    mutationFn: () => api.post<Advance>(`/producers/${producerId}/advances`, { amount: Number(amount), reason: reason || null }),
    onSuccess: () => {
      toast("Avance enregistrée : elle sera déduite du prochain paiement");
      qc.invalidateQueries({ queryKey: ["advances", producerId] });
      qc.invalidateQueries({ queryKey: ["producer", producerId, "balance"] });
      setAdding(false); setAmount(""); setReason("");
    },
  });
  return (
    <div className="grid grid-2">
      <div className="card">
        <div className="card-head"><h2>Paiements</h2></div>
        <table>
          <thead><tr><th>Date</th><th className="num">Brut</th><th className="num">Avance</th><th className="num">Envoyé</th><th>Statut</th></tr></thead>
          <tbody>
            {payments.data?.map((p) => (
              <tr key={p.id}><td>{dateTime(p.paid_at ?? p.created_at)}</td><td className="num">{fcfa(p.gross_amount)}</td>
                <td className="num">{p.advance_deduction ? `− ${fcfa(p.advance_deduction)}` : "—"}</td><td className="num"><b>{fcfa(p.amount)}</b></td><td><Status value={p.status} /></td></tr>
            ))}
            {!payments.data?.length && <tr><td colSpan={5} className="muted">Aucun paiement.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="card">
        <div className="card-head"><h2>Avances</h2><span className="spacer" /><button className="sm" onClick={() => setAdding(true)}>+ Avance</button></div>
        <table>
          <thead><tr><th>Date</th><th>Motif</th><th className="num">Montant</th><th className="num">Reste dû</th></tr></thead>
          <tbody>
            {advances.data?.map((a) => (
              <tr key={a.id}><td>{date(a.given_at)}</td><td>{a.reason ?? "—"}</td><td className="num">{fcfa(a.amount)}</td>
                <td className="num">{a.remaining ? fcfa(a.remaining) : <Badge tone="success">Remboursée</Badge>}</td></tr>
            ))}
            {!advances.data?.length && <tr><td colSpan={4} className="muted">Aucune avance.</td></tr>}
          </tbody>
        </table>
      </div>
      {adding && (
        <Modal title="Nouvelle avance" onClose={() => setAdding(false)} footer={<>
          <button className="ghost" onClick={() => setAdding(false)}>Annuler</button>
          <button className="primary" disabled={!Number(amount) || add.isPending} onClick={() => add.mutate()}>Enregistrer</button>
        </>}>
          <div className="stack">
            <label className="field">Montant (FCFA)<input autoFocus inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value.replace(/\D/g, ""))} /></label>
            <label className="field">Motif<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Rentrée scolaire, santé, intrants…" /></label>
            <ErrorBox error={add.error} />
          </div>
        </Modal>
      )}
    </div>
  );
}

function QrCard({ p }: { p: Producer }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    imageUrl(`/producers/${p.id}/qr-code?scale=10`).then((u) => { url = u; setSrc(u); }).catch(() => setSrc(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [p.id]);
  return (
    <div className="stack">
      <p className="muted" style={{ margin: 0 }}>Imprimez la carte et plastifiez-la : le collecteur la scanne pour retrouver le producteur en une seconde, même sans réseau.</p>
      <div className="qr-card">
        {src ? <img src={src} alt={`QR ${p.code}`} /> : <div style={{ width: 120, height: 120 }} />}
        <div>
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em", color: "#8a4b2a", fontWeight: 700 }}>Carte producteur</div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{p.full_name}</div>
          <div className="mono" style={{ fontSize: 14 }}>{p.code}</div>
          <div style={{ fontSize: 12, marginTop: 6 }}>{p.zone_name}</div>
        </div>
      </div>
      <div className="no-print"><button onClick={() => window.print()}>🖨 Imprimer</button></div>
    </div>
  );
}
