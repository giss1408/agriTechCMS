import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Empty, ErrorBox, Loading, Modal, PageHead, Status, useToast } from "../components/ui";
import { api, download } from "../lib/api";
import { dateTime, fcfa, kg, num } from "../lib/format";
import type { Collection, Lot } from "../lib/types";

export function LotsPage() {
  const [composing, setComposing] = useState<Lot | "new" | null>(null);
  const [shipping, setShipping] = useState<Lot | null>(null);
  const qc = useQueryClient();
  const toast = useToast();
  const lots = useQuery({ queryKey: ["lots"], queryFn: () => api.get<Lot[]>("/lots", { per_page: 100 }) });
  const seal = useMutation({
    mutationFn: (lot: Lot) => api.post<Lot>(`/lots/${lot.id}/seal`, {}),
    onSuccess: (l) => { toast(`Lot ${l.reference} scellé — lien de traçabilité créé`); qc.invalidateQueries({ queryKey: ["lots"] }); },
    onError: (e: Error) => toast(e.message),
  });

  return (
    <div>
      <PageHead title="Lots & traçabilité" subtitle="Regroupez les livraisons validées en lots : chaque lot scellé reçoit un lien de traçabilité pour l'acheteur.">
        <button className="primary" onClick={() => setComposing("new")}>+ Nouveau lot</button>
      </PageHead>
      <div className="card">
        {lots.isLoading ? <Loading /> : !lots.data?.length ? <Empty>Aucun lot pour l'instant.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Référence</th><th>Produit</th><th className="num">Livraisons</th><th className="num">Poids</th><th className="num">Sacs</th><th>Acheteur</th><th>Statut</th><th /></tr></thead>
              <tbody>
                {lots.data.map((l) => (
                  <tr key={l.id}>
                    <td className="mono">{l.reference}</td>
                    <td>{l.product}{l.quality ? ` ${l.quality}` : ""}</td>
                    <td className="num">{l.collections_count}</td>
                    <td className="num">{kg(l.total_weight_kg)}</td>
                    <td className="num">{l.bags_count ?? "—"}</td>
                    <td>{l.buyer_name ?? "—"}</td>
                    <td><Status value={l.status} /></td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        {l.status === "open" && <>
                          <button className="sm" onClick={() => setComposing(l)}>Ajouter des livraisons</button>
                          <button className="sm primary" disabled={!l.collections_count || seal.isPending} onClick={() => seal.mutate(l)}>Sceller</button>
                        </>}
                        {l.status === "sealed" && <button className="sm primary" onClick={() => setShipping(l)}>Expédier</button>}
                        {l.trace_url && <>
                          <a className="btn sm" href={l.trace_url} target="_blank" rel="noreferrer">Page acheteur ↗</a>
                          <button className="sm" onClick={() => download(`/lots/${l.id}/eudr.geojson`, `${l.reference}.geojson`)}>GeoJSON EUDR</button>
                        </>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {composing && <ComposeLot lot={composing === "new" ? null : composing} onClose={() => setComposing(null)} />}
      {shipping && <ShipLot lot={shipping} onClose={() => setShipping(null)} />}
    </div>
  );
}

function ComposeLot({ lot, onClose }: { lot: Lot | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [quality, setQuality] = useState(lot?.quality ?? "");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const candidates = useQuery({
    queryKey: ["collections", "unlotted", quality],
    queryFn: () => api.get<Collection[]>("/collections", { status: "validated", unlotted: true, quality, product: "cacao", per_page: 200 }),
  });
  const rows = candidates.data ?? [];
  const chosen = rows.filter((c) => selected.has(c.id));
  const total = chosen.reduce((s, c) => s + Number(c.weight_kg), 0);
  const save = useMutation({
    mutationFn: async () => {
      const ids = [...selected];
      if (lot) return (await api.post<{ refused: unknown[] }>(`/lots/${lot.id}/collections`, { ids })).refused;
      return (await api.post<{ refused: unknown[] }>("/lots", { product: "cacao", quality: quality || null, collection_ids: ids })).refused;
    },
    onSuccess: (refused) => {
      toast(refused.length ? `${refused.length} livraison(s) refusée(s)` : "Lot mis à jour");
      qc.invalidateQueries({ queryKey: ["lots"] });
      qc.invalidateQueries({ queryKey: ["collections"] });
      onClose();
    },
  });
  return (
    <Modal title={lot ? `Compléter ${lot.reference}` : "Nouveau lot de cacao"} onClose={onClose} footer={<>
      <span className="muted">{chosen.length} livraison(s) · {kg(total)}</span><span className="spacer" />
      <button className="ghost" onClick={onClose}>Annuler</button>
      <button className="primary" disabled={save.isPending || (!!lot && !selected.size)} onClick={() => save.mutate()}>{lot ? "Ajouter" : "Créer le lot"}</button>
    </>}>
      <div className="stack">
        {!lot && (
          <label className="field">Qualité du lot
            <select value={quality} onChange={(e) => { setQuality(e.target.value); setSelected(new Set()); }}>
              <option value="">Toutes qualités (lot mixte)</option><option value="A">A uniquement</option><option value="B">B uniquement</option>
            </select>
          </label>
        )}
        <div className="row"><b>Livraisons validées hors lot</b><span className="spacer" />
          <button className="sm" onClick={() => setSelected(new Set(rows.map((c) => c.id)))}>Tout sélectionner</button>
        </div>
        <div className="table-wrap" style={{ maxHeight: 320, overflow: "auto", border: "1px solid var(--border)", borderRadius: 8 }}>
          {candidates.isLoading ? <Loading /> : !rows.length ? <Empty>Aucune livraison validée disponible.</Empty> : (
            <table>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className={`clickable${selected.has(c.id) ? " selected" : ""}`}
                    onClick={() => setSelected((s) => { const n = new Set(s); n.has(c.id) ? n.delete(c.id) : n.add(c.id); return n; })}>
                    <td><input type="checkbox" readOnly checked={selected.has(c.id)} aria-label={c.reference} /></td>
                    <td className="small">{dateTime(c.collected_at)}</td><td>{c.producer_name}</td><td>{c.quality}</td>
                    <td className="num">{num(c.weight_kg)} kg</td><td className="num muted">{fcfa(c.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <ErrorBox error={save.error} />
      </div>
    </Modal>
  );
}

function ShipLot({ lot, onClose }: { lot: Lot; onClose: () => void }) {
  const qc = useQueryClient();
  const [buyer, setBuyer] = useState("");
  const [destination, setDestination] = useState("");
  const ship = useMutation({
    mutationFn: () => api.post<Lot>(`/lots/${lot.id}/ship`, { buyer_name: buyer, destination: destination || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); onClose(); },
  });
  return (
    <Modal title={`Expédier ${lot.reference}`} onClose={onClose} footer={<>
      <button className="ghost" onClick={onClose}>Annuler</button>
      <button className="primary" disabled={buyer.length < 2 || ship.isPending} onClick={() => ship.mutate()}>Confirmer l'expédition</button>
    </>}>
      <div className="stack">
        <div className="muted">{kg(lot.total_weight_kg)} · {lot.collections_count} livraisons · {lot.bags_count ?? "?"} sacs</div>
        <label className="field">Acheteur / exportateur<input autoFocus value={buyer} onChange={(e) => setBuyer(e.target.value)} /></label>
        <label className="field">Destination (magasin, port…)<input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="San-Pedro" /></label>
        <ErrorBox error={ship.error} />
      </div>
    </Modal>
  );
}
