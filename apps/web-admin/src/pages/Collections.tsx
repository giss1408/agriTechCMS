import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ReportProblem } from "../components/ReportProblem";
import { Drawer, Empty, ErrorBox, Loading, PageHead, Pager, Status, useToast } from "../components/ui";
import { api, download } from "../lib/api";
import { STATUS_LABEL, dateTime, fcfa, kg, num } from "../lib/format";
import type { Collection, Totals, User } from "../lib/types";

const PER_PAGE = 25;

export function CollectionsPage() {
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState<Collection | null>(null);
  const qc = useQueryClient();
  const toast = useToast();

  const filters = {
    status: params.get("status") ?? "",
    date_from: params.get("date_from") ?? "",
    date_to: params.get("date_to") ?? "",
    collector_id: params.get("collector_id") ?? "",
    quality: params.get("quality") ?? "",
  };
  const setFilter = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
    setPage(1);
    setSelected(new Set());
  };

  const list = useQuery({
    queryKey: ["collections", filters, page],
    queryFn: () => api.page<Collection[]>("/collections", { ...filters, page, per_page: PER_PAGE }),
  });
  const totals = useQuery({ queryKey: ["collections", "totals", filters], queryFn: () => api.get<Totals>("/collections/totals", filters) });
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });

  const validate = useMutation({
    mutationFn: (ids: string[]) => api.post<{ validated: string[]; refused: { id: string; reason: string }[] }>("/collections/validate", { ids }),
    onSuccess: (r) => {
      toast(`${r.validated.length} collecte(s) validée(s)${r.refused.length ? `, ${r.refused.length} refusée(s)` : ""}`);
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const rows = list.data?.data ?? [];
  const pendingIds = rows.filter((c) => c.status === "pending_validation").map((c) => c.id);
  const toggle = (id: string) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return (
    <div>
      <PageHead title="Collectes" subtitle="Toutes les pesées saisies par les collecteurs, synchronisées depuis le terrain.">
        <button onClick={() => download(`/collections/export${toQs(filters)}`, "collectes.csv")}>⬇ Export Excel (CSV)</button>
      </PageHead>

      <div className="filters">
        <label className="field">Statut
          <select value={filters.status} onChange={(e) => setFilter("status", e.target.value)}>
            <option value="">Tous</option>
            {["pending_validation", "validated", "paid", "rejected", "cancelled"].map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </label>
        <label className="field">Du<input type="date" value={filters.date_from} onChange={(e) => setFilter("date_from", e.target.value)} /></label>
        <label className="field">Au<input type="date" value={filters.date_to} onChange={(e) => setFilter("date_to", e.target.value)} /></label>
        <label className="field">Collecteur
          <select value={filters.collector_id} onChange={(e) => setFilter("collector_id", e.target.value)}>
            <option value="">Tous</option>
            {users.data?.filter((u) => u.role === "collector").map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </label>
        <label className="field">Qualité
          <select value={filters.quality} onChange={(e) => setFilter("quality", e.target.value)}>
            <option value="">Toutes</option><option>A</option><option>B</option>
          </select>
        </label>
        <span className="spacer" />
        {selected.size > 0 && (
          <button className="primary" disabled={validate.isPending} onClick={() => validate.mutate([...selected])}>
            ✓ Valider la sélection ({selected.size})
          </button>
        )}
      </div>

      <div className="card">
        {list.isLoading ? <Loading /> : list.error ? <ErrorBox error={list.error} /> : rows.length === 0 ? <Empty>Aucune collecte pour ces filtres.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 32 }}>
                    <input type="checkbox" aria-label="Tout sélectionner" disabled={!pendingIds.length}
                      checked={pendingIds.length > 0 && pendingIds.every((id) => selected.has(id))}
                      onChange={(e) => setSelected(e.target.checked ? new Set(pendingIds) : new Set())} />
                  </th>
                  <th>Date</th><th>Producteur</th><th>Collecteur</th><th>Qualité</th>
                  <th className="num">Poids</th><th className="num">Humidité</th><th className="num">Montant</th><th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className={`clickable${selected.has(c.id) ? " selected" : ""}`} onClick={() => setOpen(c)}>
                    <td onClick={(e) => e.stopPropagation()}>
                      {c.status === "pending_validation" && <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} aria-label={`Sélectionner ${c.reference}`} />}
                    </td>
                    <td>{dateTime(c.collected_at)}</td>
                    <td><b>{c.producer_name}</b> <span className="muted small">{c.producer_code}</span></td>
                    <td>{c.collector_name}</td>
                    <td>{c.product} {c.quality}</td>
                    <td className="num">{num(c.weight_kg)} kg</td>
                    <td className="num">{c.moisture_percent ? `${num(c.moisture_percent)} %` : "—"}</td>
                    <td className="num">{fcfa(c.amount)}</td>
                    <td><Status value={c.status} /></td>
                  </tr>
                ))}
              </tbody>
              {totals.data && (
                <tfoot>
                  <tr>
                    <td /><td colSpan={4}>Total filtré : {num(totals.data.count)} collectes</td>
                    <td className="num">{kg(totals.data.weight_kg)}</td><td /><td className="num">{fcfa(totals.data.amount)}</td><td />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>
      <Pager page={page} perPage={PER_PAGE} total={list.data?.meta?.total ?? 0} onPage={setPage} />
      {open && <CollectionDrawer collection={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function toQs(f: Record<string, string>) {
  const sp = new URLSearchParams(Object.entries(f).filter(([, v]) => v));
  return sp.toString() ? `?${sp}` : "";
}

type HistoryItem = { at: string; action: string; actor: string | null; changes: Record<string, unknown> };
const ACTION_LABEL: Record<string, string> = { created: "Saisie", edited: "Modifiée", validated: "Validée", rejected: "Rejetée", cancelled: "Annulée" };

function CollectionDrawer({ collection, onClose }: { collection: Collection; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const detail = useQuery({ queryKey: ["collection", collection.id], queryFn: () => api.get<Collection>(`/collections/${collection.id}`), initialData: collection });
  const history = useQuery({ queryKey: ["collection", collection.id, "history"], queryFn: () => api.get<HistoryItem[]>(`/collections/${collection.id}/history`) });
  const [rejecting, setRejecting] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState("");
  const c = detail.data;

  const act = useMutation({
    mutationFn: (kind: "validate" | "reject") =>
      kind === "validate" ? api.post<Collection>(`/collections/${c.id}/validate`) : api.post<Collection>(`/collections/${c.id}/reject`, { reason }),
    onSuccess: (r) => {
      toast(`Collecte ${STATUS_LABEL[r.status].toLowerCase()}`);
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["collection", c.id] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setRejecting(false);
    },
  });

  return (
    <Drawer onClose={onClose}>
      <div className="modal-head">
        <div>
          <h2>{c.reference}</h2>
          <div className="muted small">{dateTime(c.collected_at)}</div>
        </div>
        <span className="spacer" />
        <Status value={c.status} />
        <button className="ghost" onClick={onClose} aria-label="Fermer">✕</button>
      </div>
      <div className="modal-body stack">
        <dl className="kv">
          <dt>Producteur</dt><dd><Link to={`/producers/${c.producer_id}`}>{c.producer_name}</Link> <span className="muted">{c.producer_code}</span></dd>
          <dt>Collecteur</dt><dd>{c.collector_name}</dd>
          <dt>Produit</dt><dd>{c.product} — qualité {c.quality}</dd>
          <dt>Poids</dt><dd><b>{num(c.weight_kg)} kg</b></dd>
          <dt>Humidité</dt><dd>{c.moisture_percent ? `${num(c.moisture_percent)} %` : "non mesurée"}</dd>
          <dt>Prix appliqué</dt><dd>{fcfa(c.unit_price)} / kg</dd>
          <dt>Montant</dt><dd><b>{fcfa(c.amount)}</b></dd>
          <dt>Source</dt><dd>{c.sync_source === "offline_mobile" ? "Téléphone (hors-ligne)" : c.sync_source}</dd>
          {Math.abs(c.clock_offset_seconds) > 120 && <><dt>Horloge</dt><dd className="small">Heure du téléphone corrigée de {Math.round(c.clock_offset_seconds / 60)} min</dd></>}
          {c.gps_lat && <><dt>GPS</dt><dd><a href={`https://www.openstreetmap.org/?mlat=${c.gps_lat}&mlon=${c.gps_lng}#map=15/${c.gps_lat}/${c.gps_lng}`} target="_blank" rel="noreferrer">{c.gps_lat.toFixed(5)}, {c.gps_lng?.toFixed(5)}</a></dd></>}
          {c.rejection_reason && <><dt>Motif du rejet</dt><dd>{c.rejection_reason}</dd></>}
          {c.notes && <><dt>Notes</dt><dd>{c.notes}</dd></>}
        </dl>

        {c.status === "pending_validation" && !rejecting && (
          <div className="row">
            <button className="primary" disabled={act.isPending} onClick={() => act.mutate("validate")}>✓ Valider</button>
            <button className="danger" onClick={() => setRejecting(true)}>Rejeter…</button>
          </div>
        )}
        {rejecting && (
          <div className="stack">
            <label className="field">Motif du rejet (visible dans l'historique)
              <input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} placeholder="ex. : doublon d'une pesée papier" />
            </label>
            <div className="row">
              <button className="danger" disabled={reason.length < 3 || act.isPending} onClick={() => act.mutate("reject")}>Confirmer le rejet</button>
              <button className="ghost" onClick={() => setRejecting(false)}>Annuler</button>
            </div>
          </div>
        )}
        <ErrorBox error={act.error} />
        <div><button className="sm ghost" onClick={() => setReporting(true)}>⚑ Signaler un problème sur cette collecte</button></div>
        {reporting && <ReportProblem collectionId={c.id} collectionLabel={`${c.reference} — ${c.producer_name}`} onClose={() => setReporting(false)} />}

        <div>
          <h3 style={{ marginBottom: 8 }}>Historique</h3>
          {history.data?.map((h, i) => (
            <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
              <b>{ACTION_LABEL[h.action] ?? h.action}</b> par {h.actor ?? "système"} · <span className="muted">{dateTime(h.at)}</span>
              {Object.keys(h.changes).length > 0 && h.action !== "created" && (
                <div className="muted mono">{Object.entries(h.changes).map(([k, v]) => `${k}: ${Array.isArray(v) ? `${v[0]} → ${v[1]}` : v}`).join(" · ")}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Drawer>
  );
}
