import { useState } from "react";
import { t } from "../i18n/index.js";
import { Modal } from "./ui.jsx";

const remembered = (key) => {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
};

// Send to one address / number first, to check how it looks. Values are remembered in the browser.
export default function TestSendDialog({ intro, email = true, whatsapp = false, busy, onSend, onClose }) {
  const [to, setTo] = useState(() => (email ? remembered("tms.test-email") : ""));
  const [phone, setPhone] = useState(() => (whatsapp ? remembered("tms.test-phone") : ""));
  const submit = (e) => {
    e.preventDefault();
    try {
      localStorage.setItem("tms.test-email", to);
      localStorage.setItem("tms.test-phone", phone);
    } catch {
      /* storage unavailable */
    }
    onSend(to.trim(), phone.trim());
  };
  return (
    <Modal title={t("Send a test")} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <p className="muted">{intro}</p>
        {email ? (
          <label className="field">
            <span>{t("Email")}</span>
            <input type="email" value={to} onChange={(e) => setTo(e.target.value)} placeholder="you@example.com" />
          </label>
        ) : null}
        {whatsapp ? (
          <label className="field">
            <span>{t("WhatsApp number")}</span>
            <input inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 202 555 0100" />
          </label>
        ) : null}
        <button type="submit" className="button primary" disabled={busy || !(to.trim() || phone.trim())}>
          {busy ? t("Sending…") : t("Send test")}
        </button>
      </form>
    </Modal>
  );
}
