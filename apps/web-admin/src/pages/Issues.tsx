import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ReportProblem } from "../components/ReportProblem";
import { Badge, Drawer, Empty, ErrorBox, Loading, PageHead, Pager, useToast } from "../components/ui";
import { api } from "../lib/api";
import { ISSUE_CATEGORY_LABEL, ISSUE_SOURCE_LABEL, dateTime } from "../lib/format";
import type { Issue, IssueStatus } from "../lib/types";

const PER_PAGE = 25;
const STATUS: Record<IssueStatus, [string, string]> = {
  open: ["Nouveau", "warning"],
  in_progress: ["En cours", "info"],
  resolved: ["Résolu", "success"],
};

export function IssueStatusBadge({ status }: { status: IssueStatus }) {
  const [label, tone] = STATUS[status];
  return <Badge tone={tone}>{label}</Badge>;
}

export function IssuesPage() {
  const [status, setStatus] = useState("unresolved");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<Issue | null>(null);
  const [reporting, setReporting] = useState(false);
  const q = useQuery({
    queryKey: ["issues", status, source, page],
    queryFn: () => api.page<Issue[]>("/issues", { status, source, page, per_page: PER_PAGE }),
  });
  const rows = q.data?.data ?? [];

  return (
    <div>
      <PageHead title="Signalements" subtitle="Problèmes remontés par les collecteurs, les producteurs (USSD), les acheteurs et l'équipe.">
        <button onClick={() => setReporting(true)}>+ Nouveau signalement</button>
      </PageHead>
      <div className="filters">
        <label className="field">Statut
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
            <option value="unresolved">À traiter</option><option value="open">Nouveaux</option>
            <option value="in_progress">En cours</option><option value="resolved">Résolus</option><option value="">Tous</option>
          </select>
        </label>
        <label className="field">Origine
          <select value={source} onChange={(e) => { setSource(e.target.value); setPage(1); }}>
            <option value="">Toutes</option>
            {Object.entries(ISSUE_SOURCE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      <div className="card">
        {q.isLoading ? <Loading /> : q.error ? <ErrorBox error={q.error} /> : rows.length === 0 ? <Empty>Aucun signalement {status === "unresolved" ? "à traiter 🎉" : ""}</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Réf.</th><th>Reçu</th><th>Origine</th><th>Signalé par</th><th>Type</th><th>Message</th><th>Statut</th></tr></thead>
              <tbody>
                {rows.map((i) => (
                  <tr key={i.id} className="clickable" onClick={() => setOpen(i)}>
                    <td className="mono">{i.reference}</td>
                    <td>{dateTime(i.created_at)}</td>
                    <td>{ISSUE_SOURCE_LABEL[i.source]}</td>
                    <td>{i.reporter_name ?? "—"}</td>
                    <td>{ISSUE_CATEGORY_LABEL[i.category]}</td>
                    <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{i.message}</td>
                    <td><IssueStatusBadge status={i.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pager page={page} perPage={PER_PAGE} total={q.data?.meta?.total ?? 0} onPage={setPage} />
      {open && <IssueDrawer issue={open} onClose={() => setOpen(null)} />}
      {reporting && <ReportProblem onClose={() => setReporting(false)} />}
    </div>
  );
}

function IssueDrawer({ issue, onClose }: { issue: Issue; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [note, setNote] = useState(issue.resolution_note ?? "");
  const update = useMutation({
    mutationFn: (status: IssueStatus) => api.patch<Issue>(`/issues/${issue.id}`, { status, resolution_note: note || null }),
    onSuccess: (i) => {
      toast(i.status === "resolved" && i.source === "ussd" ? "Résolu — le producteur est prévenu par SMS" : "Signalement mis à jour");
      qc.invalidateQueries({ queryKey: ["issues"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });
  const ctx = issue.context ?? {};
  return (
    <Drawer onClose={onClose}>
      <div className="modal-head">
        <div><h2>{issue.reference}</h2><div className="muted small">{dateTime(issue.created_at)} · {ISSUE_SOURCE_LABEL[issue.source]}</div></div>
        <span className="spacer" /><IssueStatusBadge status={issue.status} />
        <button className="ghost" onClick={onClose} aria-label="Fermer">✕</button>
      </div>
      <div className="modal-body stack">
        <dl className="kv">
          <dt>Type</dt><dd>{ISSUE_CATEGORY_LABEL[issue.category]}</dd>
          <dt>Signalé par</dt><dd>{issue.reporter_name ?? "—"}{issue.reporter_phone && <> · <a href={`tel:${issue.reporter_phone}`}>{issue.reporter_phone}</a></>}</dd>
          {issue.producer_id && <><dt>Producteur</dt><dd><Link to={`/producers/${issue.producer_id}`}>{issue.producer_name}</Link></dd></>}
          {issue.collection_reference && <><dt>Collecte</dt><dd className="mono">{issue.collection_reference}</dd></>}
          {issue.lot_reference && <><dt>Lot</dt><dd className="mono">{issue.lot_reference}</dd></>}
        </dl>
        <div className="card card-body" style={{ whiteSpace: "pre-wrap" }}>{issue.message}</div>
        {Object.keys(ctx).length > 0 && (
          <details>
            <summary className="small muted" style={{ cursor: "pointer" }}>Informations techniques</summary>
            <pre className="mono" style={{ whiteSpace: "pre-wrap", background: "var(--surface-2)", padding: 8, borderRadius: 8 }}>{JSON.stringify(ctx, null, 2)}</pre>
          </details>
        )}
        <label className="field">Réponse / note de résolution
          <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder={issue.source === "ussd" ? "Envoyée par SMS au producteur à la résolution" : "Ce qui a été fait"} />
        </label>
        <div className="row">
          {issue.status !== "in_progress" && issue.status !== "resolved" && <button disabled={update.isPending} onClick={() => update.mutate("in_progress")}>Prendre en charge</button>}
          {issue.status !== "resolved" && <button className="primary" disabled={update.isPending} onClick={() => update.mutate("resolved")}>✓ Marquer résolu</button>}
          {issue.status === "resolved" && <button disabled={update.isPending} onClick={() => update.mutate("open")}>Rouvrir</button>}
        </div>
        <ErrorBox error={update.error} />
      </div>
    </Drawer>
  );
}
