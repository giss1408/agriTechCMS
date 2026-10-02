import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Loading, ToastProvider } from "./components/ui";
import { AuthProvider, useAuth } from "./lib/auth";
import { CollectionsPage } from "./pages/Collections";
import { DashboardPage } from "./pages/Dashboard";
import { LoginPage } from "./pages/Login";
import { LotsPage } from "./pages/Lots";
import { PaymentsPage } from "./pages/Payments";
import { ProducerPage } from "./pages/Producer";
import { ProducersPage } from "./pages/Producers";
import { SettingsPage } from "./pages/Settings";
import { TracePage } from "./pages/Trace";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, refetchOnWindowFocus: true, retry: 1 } },
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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
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
