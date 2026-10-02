import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Badge, Empty, ErrorBox, Loading, Modal, PageHead, Pager, Status, useToast } from "../components/ui";
import { api } from "../lib/api";
import { OPERATOR_LABEL } from "../lib/format";
import type { Producer, Zone } from "../lib/types";

const PER_PAGE = 25;

export function ProducersPage() {
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const navigate = useNavigate();
  const search = params.get("search") ?? "";
  const zone = params.get("zone_id") ?? "";
  const missing = params.get("missing_parcel") === "1";

  const set = (k: string, v: string) => {
    const n = new URLSearchParams(params);
    v ? n.set(k, v) : n.delete(k);
    setParams(n, { replace: true });
    setPage(1);
  };

  const list = useQuery({
    queryKey: ["producers", search, zone, missing, page],
    queryFn: () => api.page<Producer[]>("/producers", { search, zone_id: zone, missing_parcel: missing, page, per_page: PER_PAGE }),
  });
  const zones = useQuery({ queryKey: ["zones"], queryFn: () => api.get<Zone[]>("/zones") });
  const rows = list.data?.data ?? [];

  return (
    <div>
      <PageHead title="Adhérents" subtitle={`${list.data?.meta?.total ?? "…"} producteurs`}>
        <button onClick={() => setImporting(true)}>⬆ Importer un fichier</button>
        <button className="primary" onClick={() => setCreating(true)}>+ Ajouter un producteur</button>
      </PageHead>
      <div className="filters">
        <label className="field" style={{ flex: "1 1 260px" }}>Recherche
          <input placeholder="Nom, code ou téléphone" value={search} onChange={(e) => set("search", e.target.value)} />
        </label>
        <label className="field">Zone
          <select value={zone} onChange={(e) => set("zone_id", e.target.value)}>
            <option value="">Toutes</option>
            {zones.data?.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}
          </select>
        </label>
        <label className="row" style={{ paddingBottom: 8 }}>
          <input type="checkbox" checked={missing} onChange={(e) => set("missing_parcel", e.target.checked ? "1" : "")} />
          Sans parcelle géolocalisée
        </label>
      </div>
      <div className="card">
        {list.isLoading ? <Loading /> : list.error ? <ErrorBox error={list.error} /> : rows.length === 0 ? <Empty>Aucun producteur.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Nom</th><th>Zone</th><th>Téléphone</th><th>Mobile money</th><th>Parcelles</th><th>Statut</th></tr></thead>
              <tbody>
                {rows.map((p) => {
                  const ready = p.parcels.filter((x) => x.eudr_issues.length === 0).length;
                  return (
                    <tr key={p.id} className="clickable" onClick={() => navigate(`/producers/${p.id}`)}>
                      <td className="mono">{p.code}</td>
                      <td><b>{p.full_name}</b></td>
                      <td>{p.zone_name ?? "—"}</td>
                      <td>{p.phone ?? "—"}</td>
                      <td>{p.momo_operator ? OPERATOR_LABEL[p.momo_operator] : <Badge tone="warning">À renseigner</Badge>}</td>
                      <td>
                        {p.parcels.length === 0 ? <Badge tone="danger">Aucune</Badge> : (
                          <Badge tone={ready === p.parcels.length ? "success" : "warning"}>{ready}/{p.parcels.length} prête(s) EUDR</Badge>
                        )}
                      </td>
                      <td><Status value={p.status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Pager page={page} perPage={PER_PAGE} total={list.data?.meta?.total ?? 0} onPage={setPage} />
      {creating && <ProducerForm zones={zones.data ?? []} onClose={() => setCreating(false)} onCreated={(p) => navigate(`/producers/${p.id}`)} />}
      {importing && <ImportModal onClose={() => setImporting(false)} />}
    </div>
  );
}

function ProducerForm({ zones, onClose, onCreated }: { zones: Zone[]; onClose: () => void; onCreated: (p: Producer) => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ first_name: "", last_name: "", phone: "", gender: "", birth_year: "", zone_id: "", operator: "", account: "", lat: "", lng: "", area: "" });
  const up = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const create = useMutation({
    mutationFn: () =>
      api.post<Producer>("/producers", {
        first_name: f.first_name, last_name: f.last_name, phone: f.phone || null, gender: f.gender || null,
        birth_year: f.birth_year ? Number(f.birth_year) : null, zone_id: f.zone_id || null,
        mobile_money: f.operator && f.account ? { operator: f.operator, account: f.account } : null,
        parcels: f.lat && f.lng ? [{ latitude: Number(f.lat), longitude: Number(f.lng), area_hectares: f.area || null, crop: "cacao" }] : [],
      }),
    onSuccess: (p) => { qc.invalidateQueries({ queryKey: ["producers"] }); onCreated(p); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };
  return (
    <Modal title="Nouveau producteur" onClose={onClose} footer={<>
      <button className="ghost" onClick={onClose}>Annuler</button>
      <button className="primary" form="producer-form" disabled={create.isPending}>Enregistrer</button>
    </>}>
      <form id="producer-form" className="form-grid" onSubmit={submit}>
        <label className="field">Nom<input required value={f.last_name} onChange={up("last_name")} /></label>
        <label className="field">Prénom(s)<input required value={f.first_name} onChange={up("first_name")} /></label>
        <label className="field">Téléphone<input inputMode="tel" value={f.phone} onChange={up("phone")} placeholder="07 12 34 56 78" /></label>
        <label className="field">Zone
          <select value={f.zone_id} onChange={up("zone_id")}><option value="">—</option>{zones.map((z) => <option key={z.id} value={z.id}>{z.name}</option>)}</select>
        </label>
        <label className="field">Sexe<select value={f.gender} onChange={up("gender")}><option value="">—</option><option value="M">Homme</option><option value="F">Femme</option></select></label>
        <label className="field">Année de naissance<input inputMode="numeric" value={f.birth_year} onChange={up("birth_year")} /></label>
        <label className="field">Opérateur mobile money
          <select value={f.operator} onChange={up("operator")}><option value="">—</option>{Object.entries(OPERATOR_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        </label>
        <label className="field">Numéro mobile money<input inputMode="tel" value={f.account} onChange={up("account")} /></label>
        <label className="field">Parcelle — latitude<input inputMode="decimal" value={f.lat} onChange={up("lat")} placeholder="6.8774" /></label>
        <label className="field">Parcelle — longitude<input inputMode="decimal" value={f.lng} onChange={up("lng")} placeholder="-6.4502" /></label>
        <label className="field">Superficie (ha)<input inputMode="decimal" value={f.area} onChange={up("area")} /></label>
        <div className="full"><ErrorBox error={create.error} /></div>
      </form>
    </Modal>
  );
}

function ImportModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const run = useMutation({
    mutationFn: () => { const fd = new FormData(); fd.append("file", file!); return api.post<{ created: number; errors: { line: number; message: string }[] }>("/producers/import", fd); },
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["producers"] }); toast(`${r.created} producteur(s) importé(s)`); if (!r.errors.length) onClose(); },
  });
  return (
    <Modal title="Importer des adhérents" onClose={onClose} footer={<>
      <button className="ghost" onClick={onClose}>Fermer</button>
      <button className="primary" disabled={!file || run.isPending} onClick={() => run.mutate()}>Importer</button>
    </>}>
      <div className="stack">
        <p className="muted" style={{ margin: 0 }}>
          Fichier CSV (exporté depuis Excel, séparateur virgule ou point-virgule) avec les colonnes :
        </p>
        <code className="mono">first_name; last_name; phone; gender; birth_year; zone; cin_number; momo_operator; momo_account; latitude; longitude; area_hectares; crop</code>
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <ErrorBox error={run.error} />
        {run.data && run.data.errors.length > 0 && (
          <div className="error-box">
            {run.data.created} importé(s). Lignes en erreur :
            <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>{run.data.errors.slice(0, 10).map((e) => <li key={e.line}>ligne {e.line} : {e.message}</li>)}</ul>
          </div>
        )}
      </div>
    </Modal>
  );
}
