import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation } from "react-router-dom";
import { api, recentErrors } from "../lib/api";
import { ISSUE_CATEGORY_LABEL } from "../lib/format";
import type { Issue } from "../lib/types";
import { ErrorBox, Modal, useToast } from "./ui";

type Props = {
  onClose: () => void;
  collectionId?: string;
  collectionLabel?: string;
  defaultCategory?: Issue["category"];
};

/** Collects what support needs without asking the user for it: page, browser, connection, recent errors. */
function diagnostics(path: string) {
  const conn = (navigator as Navigator & { connection?: { effectiveType?: string; saveData?: boolean } }).connection;
  return {
    app: "web",
    page: path,
    user_agent: navigator.userAgent.slice(0, 200),
    online: navigator.onLine,
    connection: conn?.effectiveType ?? null,
    save_data: conn?.saveData ?? null,
    screen: `${window.innerWidth}x${window.innerHeight}`,
    recent_errors: recentErrors.slice(0, 5),
  };
}

export function ReportProblem({ onClose, collectionId, collectionLabel, defaultCategory }: Props) {
  const qc = useQueryClient();
  const toast = useToast();
  const location = useLocation();
  const [category, setCategory] = useState<Issue["category"]>(defaultCategory ?? (collectionId ? "data_error" : "app_bug"));
  const [message, setMessage] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const context = diagnostics(location.pathname + location.search);

  const send = useMutation({
    mutationFn: () => api.post<Issue>("/issues", { category, message, collection_id: collectionId ?? null, context }),
    onSuccess: (issue) => {
      toast(`Signalement ${issue.reference} envoyé. Merci !`);
      qc.invalidateQueries({ queryKey: ["issues"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      onClose();
    },
  });

  return (
    <Modal title="Signaler un problème" onClose={onClose} footer={<>
      <button className="ghost" onClick={onClose}>Annuler</button>
      <button className="primary" disabled={message.trim().length < 5 || send.isPending} onClick={() => send.mutate()}>Envoyer</button>
    </>}>
      <div className="stack">
        {collectionLabel && <div className="hint">Concerne la collecte <b>{collectionLabel}</b></div>}
        <label className="field">Type de problème
          <select value={category} onChange={(e) => setCategory(e.target.value as Issue["category"])}>
            {Object.entries(ISSUE_CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="field">Que s'est-il passé ?
          <textarea autoFocus rows={5} value={message} onChange={(e) => setMessage(e.target.value)}
            placeholder="Ce que vous faisiez, ce que vous attendiez, ce qui s'est passé à la place." />
        </label>
        <div className="small muted">
          Des informations techniques sont jointes automatiquement (page, navigateur, connexion, dernières erreurs).{" "}
          <button className="ghost sm" type="button" onClick={() => setShowDetails((v) => !v)}>{showDetails ? "Masquer" : "Voir"}</button>
        </div>
        {showDetails && <pre className="mono" style={{ whiteSpace: "pre-wrap", margin: 0, background: "var(--surface-2)", padding: 8, borderRadius: 8, maxHeight: 160, overflow: "auto" }}>{JSON.stringify(context, null, 2)}</pre>}
        <ErrorBox error={send.error} />
      </div>
    </Modal>
  );
}
