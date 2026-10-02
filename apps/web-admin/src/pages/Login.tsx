import { FormEvent, useState } from "react";
import { ErrorBox } from "../components/ui";
import { api, setTokens } from "../lib/api";

export function LoginPage() {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function sendCode(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ dev_code?: string }>("/auth/request-otp", { phone });
      setDevCode(r.dev_code ?? null);
      setStep("code");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ access_token: string; refresh_token: string }>("/auth/verify-otp", { phone, otp: code });
      setTokens({ access_token: r.access_token, refresh_token: r.refresh_token });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="card">
        <div className="card-body stack">
          <div className="row">
            <svg width="40" height="40" viewBox="0 0 32 32" aria-hidden>
              <ellipse cx="16" cy="16" rx="9" ry="14" fill="var(--accent)" />
              <path d="M16 3v26M11 6c-2 6-2 14 0 20M21 6c2 6 2 14 0 20" stroke="var(--accent-soft)" strokeWidth="1.5" fill="none" />
            </svg>
            <div>
              <h1>Cabosse</h1>
              <div className="muted">Collecte, paiements et traçabilité de votre coopérative</div>
            </div>
          </div>
          {step === "phone" ? (
            <form className="stack" onSubmit={sendCode}>
              <label className="field">
                Numéro de téléphone
                <input autoFocus inputMode="tel" placeholder="07 00 00 00 01" value={phone} onChange={(e) => setPhone(e.target.value)} required />
              </label>
              <ErrorBox error={error} />
              <button className="primary" disabled={busy || phone.length < 8}>Recevoir un code par SMS</button>
              <div className="muted small">Démo : 07 00 00 00 01 (gestionnaire de la coopérative de démonstration).</div>
            </form>
          ) : (
            <form className="stack" onSubmit={verify}>
              <div className="muted">Code envoyé au <b>{phone}</b>.</div>
              {devCode && <div className="hint">Mode démo : le code est <b className="mono">{devCode}</b></div>}
              <label className="field">
                Code à 6 chiffres
                <input autoFocus inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required />
              </label>
              <ErrorBox error={error} />
              <button className="primary" disabled={busy || code.length !== 6}>Se connecter</button>
              <button type="button" className="ghost" onClick={() => setStep("phone")}>Changer de numéro</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
