import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Loading, ToastProvider } from "./components/ui";
import { AuthProvider, useAuth } from "./lib/auth";
import { DashboardPage } from "./pages/Dashboard";
import { LoginPage } from "./pages/Login";
import "./styles.css";

// Each page is its own chunk, downloaded on first visit. Leaflet (map) only ships with the two pages that
// show a map, so the first load on a slow link stays small.
const CollectionsPage = lazy(() => import("./pages/Collections").then((m) => ({ default: m.CollectionsPage })));
const LotsPage = lazy(() => import("./pages/Lots").then((m) => ({ default: m.LotsPage })));
const PaymentsPage = lazy(() => import("./pages/Payments").then((m) => ({ default: m.PaymentsPage })));
const ProducerPage = lazy(() => import("./pages/Producer").then((m) => ({ default: m.ProducerPage })));
const ProducersPage = lazy(() => import("./pages/Producers").then((m) => ({ default: m.ProducersPage })));
const SettingsPage = lazy(() => import("./pages/Settings").then((m) => ({ default: m.SettingsPage })));
const IssuesPage = lazy(() => import("./pages/Issues").then((m) => ({ default: m.IssuesPage })));
const TracePage = lazy(() => import("./pages/Trace").then((m) => ({ default: m.TracePage })));

const queryClient = new QueryClient({
  // Data younger than a minute is reused when switching pages instead of being downloaded again.
  defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: true, retry: 1 } },
});

function Protected() {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/login" replace />;
  if (me.role === "collector") {
    return (
      <div className="login">
        <div className="card card-body">
          <h2>Espace collecteur</h2>
          <p className="muted">Les collecteurs utilisent l'application mobile Cabosse Collecte. Ce tableau de bord est réservé aux gestionnaires.</p>
        </div>
      </div>
    );
  }
  return <Layout />;
}

function App() {
  const { me } = useAuth();
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={me ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/trace/:token" element={<TracePage />} />
        <Route element={<Protected />}>
          <Route index element={<DashboardPage />} />
          <Route path="collections" element={<CollectionsPage />} />
          <Route path="producers" element={<ProducersPage />} />
          <Route path="producers/:id" element={<ProducerPage />} />
          <Route path="lots" element={<LotsPage />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="issues" element={<IssuesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

// App shell cached on the device: after the first visit, only API data crosses the network.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
