import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ROLE_LABEL } from "../lib/format";
import type { Totals } from "../lib/types";

const NAV: [string, string, string][] = [
  ["/", "◧", "Tableau de bord"],
  ["/collections", "⚖", "Collectes"],
  ["/producers", "☘", "Adhérents"],
  ["/lots", "▣", "Lots & traçabilité"],
  ["/payments", "₣", "Paiements"],
  ["/settings", "⚙", "Paramètres"],
];

export function Layout() {
  const { me, logout } = useAuth();
  const pending = useQuery({
    queryKey: ["collections", "totals", "pending"],
    queryFn: () => api.get<Totals>("/collections/totals", { status: "pending_validation" }),
    refetchInterval: 60_000,
  });
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
            <ellipse cx="16" cy="16" rx="9" ry="14" fill="var(--accent)" />
            <path d="M16 3v26M11 6c-2 6-2 14 0 20M21 6c2 6 2 14 0 20" stroke="var(--accent-soft)" strokeWidth="1.5" fill="none" />
          </svg>
          <div>
            Cabosse
            <small>{me?.cooperative.name}</small>
          </div>
        </div>
        <nav className="nav">
          {NAV.map(([to, icon, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              <span aria-hidden style={{ width: 18, textAlign: "center" }}>{icon}</span>
              {label}
              {to === "/collections" && !!pending.data?.count && <span className="count">{pending.data.count}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div style={{ fontWeight: 600 }}>{me?.name}</div>
          <div className="muted">{me && ROLE_LABEL[me.role]}</div>
          <button className="sm" style={{ marginTop: 8 }} onClick={logout}>Se déconnecter</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
