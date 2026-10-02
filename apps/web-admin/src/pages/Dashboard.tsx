import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ErrorBox, Loading, PageHead, Stat } from "../components/ui";
import { api } from "../lib/api";
import { fcfa, kg, num, shortDay } from "../lib/format";
import type { Dashboard } from "../lib/types";

const ALERT_ICON = { info: "ℹ", warning: "⚠", danger: "⛔" } as const;

function WeekChart({ series }: { series: Dashboard["series_7d"] }) {
  const max = Math.max(1, ...series.map((s) => s.weight_kg));
  return (
    <div className="bars" role="img" aria-label="Poids collecté sur 7 jours">
      {series.map((s, i) => (
        <div className="bar-col" key={s.date} title={`${s.count} collectes · ${kg(s.weight_kg)}`}>
          <span className="v">{s.weight_kg ? kg(s.weight_kg) : ""}</span>
          <div className={`bar${i === series.length - 1 ? " today" : ""}`} style={{ height: `${(s.weight_kg / max) * 100}%` }} />
          <span className="d">{shortDay(s.date)}</span>
        </div>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<Dashboard>("/dashboard/summary"), refetchInterval: 30_000 });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  const geoPct = d.producers.active ? Math.round((d.producers.geolocated / d.producers.active) * 100) : 0;

  return (
    <div className="stack">
      <PageHead title="Tableau de bord" subtitle={`Campagne ${d.campaign} · mis à jour toutes les 30 secondes`} />
      <div className="grid grid-4">
        <Stat label="Collectes du jour" value={d.today.count} sub={`${kg(d.today.weight_kg)} · ${fcfa(d.today.amount)}`} />
        <Stat label="À valider" value={d.pending_validation} sub={<Link to="/collections?status=pending_validation">Voir les collectes →</Link>} />
        <Stat label="Reste à payer" value={fcfa(d.amount_to_pay)} sub={<Link to="/payments">Préparer un paiement →</Link>} accent />
        <Stat label="Campagne" value={kg(d.campaign_totals.weight_kg)} sub={`${num(d.campaign_totals.count)} collectes · ${fcfa(d.campaign_totals.amount)}`} />
      </div>

      <div className="grid grid-3-1">
        <div className="card">
          <div className="card-head"><h2>Poids collecté — 7 derniers jours</h2></div>
          <div className="card-body"><WeekChart series={d.series_7d} /></div>
        </div>
        <div className="card">
          <div className="card-head"><h2>À traiter</h2></div>
          <div className="card-body">
            {d.alerts.length === 0 && <div className="muted">Rien à signaler 🎉</div>}
            {d.alerts.map((a) => (
              <Link key={a.code} to={a.link} className={`alert tone-${a.level}`} style={{ textDecoration: "none" }}>
                <span aria-hidden>{ALERT_ICON[a.level]}</span>
                <span>{a.message}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-head"><h2>Collecteurs du mois</h2></div>
          <table>
            <thead><tr><th>#</th><th>Collecteur</th><th className="num">Collectes</th><th className="num">Poids</th></tr></thead>
            <tbody>
              {d.top_collectors.map((c, i) => (
                <tr key={c.id}><td>{i + 1}</td><td>{c.name}</td><td className="num">{c.count}</td><td className="num">{kg(c.weight_kg)}</td></tr>
              ))}
              {d.top_collectors.length === 0 && <tr><td colSpan={4} className="muted">Pas encore de collecte ce mois-ci</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="card-head"><h2>Prêt pour l'EUDR ?</h2></div>
          <div className="card-body stack">
            <div className="row">
              <span style={{ fontSize: 28, fontWeight: 700 }}>{geoPct} %</span>
              <span className="muted">des {d.producers.active} adhérents actifs ont au moins une parcelle géolocalisée</span>
            </div>
            <div className="progress"><div style={{ width: `${geoPct}%` }} /></div>
            <div className="row">
              <Link to="/producers?missing_parcel=1">Voir les adhérents à géolocaliser →</Link>
              <span className="spacer" />
              <span className="muted small">{d.open_lots} lot(s) en constitution</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
