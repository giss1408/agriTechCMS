import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge, Empty, ErrorBox, Loading, PageHead, Status, Tabs, useToast } from "../components/ui";
import { api } from "../lib/api";
import { pollEvery } from "../lib/network";
import { OPERATOR_LABEL, date, dateTime, fcfa } from "../lib/format";
import type { Payable, Payment } from "../lib/types";

type Tab = "to_pay" | "history";

export function PaymentsPage() {
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>(params.get("status") ? "history" : "to_pay");
  return (
    <div>
      <PageHead title="Paiements" subtitle="Payez les producteurs par mobile money. Les avances sont déduites automatiquement." />
      <Tabs<Tab> value={tab} onChange={setTab} tabs={[["to_pay", "À payer"], ["history", "Historique"]]} />
      {tab === "to_pay" ? <ToPay onDone={() => setTab("history")} /> : <History initialStatus={params.get("status") ?? ""} />}
    </div>
  );
}

function ToPay({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const q = useQuery({ queryKey: ["payables"], queryFn: () => api.get<Payable[]>("/payments/payables") });
  const rows = q.data ?? [];
  const payable = rows.filter((r) => r.momo_account);
  const chosen = rows.filter((r) => selected.has(r.producer_id));
  const total = chosen.reduce((s, r) => s + r.net_amount, 0);
  const pay = useMutation({
    mutationFn: () => api.post<{ count: number; total_amount: number; skipped: unknown[] }>("/payments/batch", { producer_ids: [...selected], reference_note: note || null }),
    onSuccess: (r) => {
      toast(`${r.count} paiement(s) lancé(s) pour ${fcfa(r.total_amount)}`);
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["payables"] });
      qc.invalidateQueries({ queryKey: ["payments"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      onDone();
    },
  });
  if (q.isLoading) return <Loading />;
  if (!rows.length) return <div className="card"><Empty>Aucune livraison validée en attente de paiement.</Empty></div>;
  return (
    <div className="stack">
      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: 32 }}><input type="checkbox" aria-label="Tout sélectionner" checked={payable.length > 0 && payable.every((r) => selected.has(r.producer_id))}
                  onChange={(e) => setSelected(e.target.checked ? new Set(payable.map((r) => r.producer_id)) : new Set())} /></th>
                <th>Producteur</th><th>Mobile money</th><th className="num">Livraisons</th><th>Depuis le</th>
                <th className="num">Dû</th><th className="num">Avance déduite</th><th className="num">À envoyer</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.producer_id} className={selected.has(r.producer_id) ? "selected" : ""}>
                  <td>{r.momo_account && <input type="checkbox" checked={selected.has(r.producer_id)} aria-label={r.producer_name}
                    onChange={() => setSelected((s) => { const n = new Set(s); n.has(r.producer_id) ? n.delete(r.producer_id) : n.add(r.producer_id); return n; })} />}</td>
                  <td><b>{r.producer_name}</b> <span className="muted small">{r.producer_code}</span></td>
                  <td>{r.momo_operator ? <>{OPERATOR_LABEL[r.momo_operator]} <span className="muted small">{r.momo_account}</span></> : <Badge tone="danger">Aucun compte</Badge>}</td>
                  <td className="num">{r.collections_count}</td>
                  <td>{date(r.oldest_collection_at)}</td>
                  <td className="num">{fcfa(r.gross_amount)}</td>
                  <td className="num">{r.outstanding_advances ? `− ${fcfa(Math.min(r.outstanding_advances, r.gross_amount))}` : "—"}</td>
                  <td className="num"><b>{fcfa(r.net_amount)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card card-body row">
        <label className="field" style={{ flex: "1 1 260px" }}>Libellé du paiement
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="ex. : Campagne octobre, semaine 1" />
        </label>
        <div style={{ textAlign: "right" }}>
          <div className="muted small">{chosen.length} producteur(s)</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{fcfa(total)}</div>
        </div>
        <button className="primary" disabled={!selected.size || pay.isPending} onClick={() => pay.mutate()}>💸 Payer la sélection</button>
        <div style={{ flexBasis: "100%" }}><ErrorBox error={pay.error} /></div>
      </div>
    </div>
  );
}

function History({ initialStatus }: { initialStatus: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [status, setStatus] = useState(initialStatus);
  const q = useQuery({
    queryKey: ["payments", { status }],
    queryFn: () => api.get<Payment[]>("/payments", { status, per_page: 100 }),
    // transfers complete in the background: poll while some are still running
    refetchInterval: (query) => (query.state.data?.some((p) => p.status === "processing" || p.status === "initiated") ? pollEvery(5000) : false),
  });
  const act = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: "retry" | "cancel" }) => api.post<Payment>(`/payments/${id}/${kind}`),
    onSuccess: (_, v) => { toast(v.kind === "retry" ? "Paiement relancé" : "Paiement annulé : les livraisons sont de nouveau à payer"); qc.invalidateQueries({ queryKey: ["payments"] }); qc.invalidateQueries({ queryKey: ["payables"] }); },
    onError: (e: Error) => toast(e.message),
  });
  return (
    <div className="stack">
      <div className="filters">
        <label className="field">Statut
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Tous</option><option value="success">Payés</option><option value="processing">En cours</option><option value="failed">Échecs</option><option value="cancelled">Annulés</option>
          </select>
        </label>
      </div>
      <div className="card">
        {q.isLoading ? <Loading /> : q.error ? <ErrorBox error={q.error} /> : !q.data?.length ? <Empty>Aucun paiement.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Producteur</th><th>Opérateur</th><th className="num">Brut</th><th className="num">Avance</th><th className="num">Envoyé</th><th>Statut</th><th /></tr></thead>
              <tbody>
                {q.data.map((p) => (
                  <tr key={p.id}>
                    <td>{dateTime(p.paid_at ?? p.created_at)}</td>
                    <td>{p.producer_name}</td>
                    <td>{p.operator ? OPERATOR_LABEL[p.operator] : "—"}</td>
                    <td className="num">{fcfa(p.gross_amount)}</td>
                    <td className="num">{p.advance_deduction ? `− ${fcfa(p.advance_deduction)}` : "—"}</td>
                    <td className="num"><b>{fcfa(p.amount)}</b></td>
                    <td><Status value={p.status} />{p.failure_reason && <div className="small" style={{ color: "var(--danger)" }}>{p.failure_reason}</div>}</td>
                    <td>{p.status === "failed" && (
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        <button className="sm" onClick={() => act.mutate({ id: p.id, kind: "retry" })}>Relancer</button>
                        <button className="sm danger" onClick={() => act.mutate({ id: p.id, kind: "cancel" })}>Annuler</button>
                      </div>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
