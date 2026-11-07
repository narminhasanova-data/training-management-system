import { useState } from "react";
import { useAuth } from "../auth/AuthContext.jsx";
import { t } from "../i18n/index.js";

export default function LoginPage() {
  const { signIn } = useAuth();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    setBusy(true);
    setError("");
    try {
      await signIn(form.get("username"), form.get("password"));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <div className="login">
      <div className="login-art">
        <span className="brand-mark large" aria-hidden="true">T</span>
        <h2>{t("Training Management System")}</h2>
        <p>{t("Plan each week's agenda, collect student feedback, follow homework and grades, and keep Google Classroom in sync, in one place.")}</p>
        <ul>
          <li>{t("Agendas with PDF, email and WhatsApp delivery")}</li>
          <li>{t("Weekly surveys with personal links and live results")}</li>
          <li>{t("Gradebook synced from Google Classroom")}</li>
          <li>{t("Training materials library")}</li>
        </ul>
      </div>
      <form className="login-form form" onSubmit={submit}>
        <h1>{t("Sign in")}</h1>
        <p className="muted">{t("Use your training office account.")}</p>
        {error ? <p className="error-text" role="alert">{error}</p> : null}
        <label className="field">
          <span>{t("Username")}</span>
          <input name="username" autoComplete="username" required />
        </label>
        <label className="field">
          <span>{t("Password")}</span>
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        <button type="submit" className="button primary block" disabled={busy}>
          {busy ? t("Signing in…") : t("Sign in")}
        </button>
        <p className="demo-hint">
          {t("Demo account")}: <code>coordinator</code> / <code>coordinator-demo</code>
        </p>
      </form>
    </div>
  );
}
