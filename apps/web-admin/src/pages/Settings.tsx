import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { Badge, ErrorBox, PageHead, Status, Tabs, useToast } from "../components/ui";
import { api } from "../lib/api";
import { pollEvery } from "../lib/network";
import { ROLE_LABEL, ago, date, dateTime, fcfa } from "../lib/format";
import type { Device, Price, User, Zone } from "../lib/types";

type Tab = "prices" | "thresholds" | "users" | "zones" | "devices" | "sms";

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>("prices");
  return (
    <div>
      <PageHead title="Paramètres" />
      <Tabs<Tab> value={tab} onChange={setTab} tabs={[
        ["prices", "Prix d'achat"], ["thresholds", "Seuils d'alerte"], ["users", "Utilisateurs"],
        ["zones", "Zones"], ["devices", "Téléphones"], ["sms", "SMS envoyés (démo)"],
      ]} />
      {tab === "prices" && <Prices />}
      {tab === "thresholds" && <Thresholds />}
      {tab === "users" && <Users />}
      {tab === "zones" && <Zones />}
      {tab === "devices" && <Devices />}
      {tab === "sms" && <SmsOutbox />}
    </div>
  );
}

function Prices() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["prices"], queryFn: () => api.get<Price[]>("/settings/purchase-prices") });
  const [f, setF] = useState({ product: "cacao", quality: "A", price_per_kg: "", effective_from: new Date().toISOString().slice(0, 10) });
  const add = useMutation({
    mutationFn: () => api.post<Price>("/settings/purchase-prices", { ...f, price_per_kg: Number(f.price_per_kg) }),
    onSuccess: () => { toast("Nouveau prix enregistré. Les collectes déjà saisies gardent leur prix."); qc.invalidateQueries({ queryKey: ["prices"] }); setF({ ...f, price_per_kg: "" }); },
  });
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div className="grid grid-3-1">
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Produit</th><th>Qualité</th><th className="num">Prix / kg</th><th>Du</th><th>Au</th><th /></tr></thead>
          <tbody>
            {q.data?.map((p) => {
              const current = p.effective_from <= today && (!p.effective_to || p.effective_to >= today);
              return (
                <tr key={p.id} style={{ opacity: current || p.effective_from > today ? 1 : 0.55 }}>
                  <td>{p.product}</td><td>{p.quality}</td><td className="num"><b>{fcfa(p.price_per_kg)}</b></td>
                  <td>{date(p.effective_from)}</td><td>{p.effective_to ? date(p.effective_to) : "…"}</td>
                  <td>{current ? <Badge tone="success">En vigueur</Badge> : p.effective_from > today ? <Badge tone="info">À venir</Badge> : null}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <form className="card card-body stack" onSubmit={(e: FormEvent) => { e.preventDefault(); add.mutate(); }}>
        <h2>Nouveau prix</h2>
        <p className="muted small" style={{ margin: 0 }}>Le prix précédent est clôturé automatiquement la veille. Chaque collecte est valorisée au prix en vigueur à sa date.</p>
        <div className="form-grid">
          <label className="field">Produit<select value={f.product} onChange={(e) => setF({ ...f, product: e.target.value })}><option value="cacao">Cacao</option><option value="anacarde">Anacarde</option><option value="cafe">Café</option></select></label>
          <label className="field">Qualité<input value={f.quality} onChange={(e) => setF({ ...f, quality: e.target.value })} /></label>
          <label className="field">Prix (FCFA/kg)<input required inputMode="numeric" value={f.price_per_kg} onChange={(e) => setF({ ...f, price_per_kg: e.target.value.replace(/\D/g, "") })} /></label>
          <label className="field">À partir du<input type="date" required value={f.effective_from} onChange={(e) => setF({ ...f, effective_from: e.target.value })} /></label>
        </div>
        <ErrorBox error={add.error} />
        <button className="primary" disabled={!f.price_per_kg || add.isPending}>Enregistrer</button>
      </form>
    </div>
  );
}

function Thresholds() {
  const toast = useToast();
  const q = useQuery({ queryKey: ["alerts"], queryFn: () => api.get<{ max_moisture_percent: string; max_weight_kg: string }>("/settings/alerts") });
  const [m, setM] = useState("");
  const [w, setW] = useState("");
  useEffect(() => { if (q.data) { setM(q.data.max_moisture_percent); setW(q.data.max_weight_kg); } }, [q.data]);
  const save = useMutation({
    mutationFn: () => api.put("/settings/alerts", { max_moisture_percent: m, max_weight_kg: w }),
    onSuccess: () => toast("Seuils enregistrés — appliqués aux téléphones à la prochaine synchronisation"),
  });
  return (
    <form className="card card-body stack" style={{ maxWidth: 480 }} onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label className="field">Humidité maximale acceptée (%)<input inputMode="decimal" value={m} onChange={(e) => setM(e.target.value)} /></label>
      <label className="field">Poids maximal par pesée (kg)<input inputMode="decimal" value={w} onChange={(e) => setW(e.target.value)} /></label>
      <p className="muted small" style={{ margin: 0 }}>Au-delà, la collecte est refusée sur le téléphone et par le serveur (le lot doit être re-séché ou la pesée fractionnée).</p>
      <ErrorBox error={save.error} />
      <button className="primary" disabled={save.isPending}>Enregistrer</button>
    </form>
  );
}

function Users() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ["users"], queryFn: () => api.get<User[]>("/users") });
  const [f, setF] = useState({ name: "", phone: "", role: "collector" });
  const add = useMutation({
    mutationFn: () => api.post<User>("/users", f),
    onSuccess: (u) => { toast(`${u.name} peut se connecter avec ${u.phone}`); qc.invalidateQueries({ queryKey: ["users"] }); setF({ name: "", phone: "", role: "collector" }); },
  });
  const toggle = useMutation({
    mutationFn: (u: User) => api.patch<User>(`/users/${u.id}`, { is_active: !u.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e: Error) => toast(e.message),
  });
  return (
    <div className="grid grid-3-1">
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Nom</th><th>Téléphone</th><th>Rôle</th><th>Dernière activité</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {q.data?.map((u) => (
              <tr key={u.id}>
                <td><b>{u.name}</b></td><td>{u.phone}</td><td>{ROLE_LABEL[u.role]}</td><td>{ago(u.last_seen_at)}</td>
                <td><Status value={u.is_active ? "active" : "inactive"} /></td>
                <td><button className="sm" onClick={() => toggle.mutate(u)}>{u.is_active ? "Désactiver" : "Réactiver"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form className="card card-body stack" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <h2>Ajouter un utilisateur</h2>
        <label className="field">Nom<input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
        <label className="field">Téléphone (identifiant de connexion)<input required inputMode="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></label>
        <label className="field">Rôle<select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="collector">Collecteur</option><option value="admin">Administrateur</option></select></label>
        <ErrorBox error={add.error} />
        <button className="primary" disabled={add.isPending}>Créer</button>
      </form>
    </div>
  );
}

function Zones() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["zones"], queryFn: () => api.get<Zone[]>("/zones") });
  const [name, setName] = useState("");
  const add = useMutation({ mutationFn: () => api.post<Zone>("/zones", { name }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["zones"] }); setName(""); } });
  return (
    <div className="card card-body stack" style={{ maxWidth: 480 }}>
      <div className="row">{q.data?.map((z) => <Badge key={z.id}>{z.name}</Badge>)}</div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
        <input placeholder="Nouvelle zone (village, secteur…)" value={name} onChange={(e) => setName(e.target.value)} style={{ flex: 1 }} />
        <button className="primary" disabled={!name || add.isPending}>Ajouter</button>
      </form>
      <ErrorBox error={add.error} />
    </div>
  );
}

function Devices() {
  const q = useQuery({ queryKey: ["devices"], queryFn: () => api.get<Device[]>("/sync/devices"), refetchInterval: pollEvery(120_000) });
  return (
    <div className="card table-wrap">
      <table>
        <thead><tr><th>Téléphone</th><th>Collecteur</th><th>Version</th><th>Dernier envoi</th><th>Dernière réception</th><th>Horloge</th></tr></thead>
        <tbody>
          {q.data?.map((d) => {
            const stale = !d.last_push_at || Date.now() - new Date(d.last_push_at).getTime() > 3 * 86400_000;
            return (
              <tr key={d.id}>
                <td className="mono">{d.id.slice(0, 12)}</td><td>{d.user_name}</td><td>{d.app_version ?? "—"}</td>
                <td>{stale ? <Badge tone="warning">{ago(d.last_push_at)}</Badge> : ago(d.last_push_at)}</td>
                <td>{ago(d.last_pull_at)}</td>
                <td>{Math.abs(d.last_clock_offset_seconds) > 120 ? <Badge tone="warning">décalée de {Math.round(d.last_clock_offset_seconds / 60)} min</Badge> : <span className="muted">à l'heure</span>}</td>
              </tr>
            );
          })}
          {!q.data?.length && <tr><td colSpan={6} className="muted">Aucun téléphone n'a encore synchronisé.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function SmsOutbox() {
  const q = useQuery({ queryKey: ["sms"], queryFn: () => api.get<{ id: string; phone: string; kind: string; body: string; created_at: string }[]>("/dev/sms", { limit: 50 }), refetchInterval: pollEvery(15_000) });
  return (
    <div className="stack">
      <p className="muted" style={{ margin: 0 }}>En démonstration, les SMS ne partent pas : ils s'affichent ici (codes de connexion, confirmations de paiement).</p>
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Heure</th><th>Destinataire</th><th>Type</th><th>Message</th></tr></thead>
          <tbody>
            {q.data?.map((m) => <tr key={m.id}><td>{dateTime(m.created_at)}</td><td>{m.phone}</td><td><Badge tone={m.kind === "payment" ? "success" : "info"}>{m.kind}</Badge></td><td>{m.body}</td></tr>)}
          </tbody>
        </table>
        <ErrorBox error={q.error} />
      </div>
    </div>
  );
}
