import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { t } from "../i18n/index.js";
import Icon from "./Icon.jsx";
import { useToast } from "./Toast.jsx";
import { Alert, stamp } from "./ui.jsx";

// Starts the (mock) OAuth flow; the browser comes back to `page` with ?connected=…
export async function connectAccount(purpose, page) {
  const { url } = await api(`integrations/${purpose}/connect/`, { method: "POST", body: { page } });
  window.location.assign(url);
}

export async function disconnectAccount(purpose) {
  await api(`integrations/${purpose}/disconnect/`, { method: "POST" });
}

// Shows the result of a connect round-trip once, then cleans the address bar.
export function useConnectReturn(onConnected) {
  const [params, setParams] = useSearchParams();
  const toast = useToast();
  useEffect(() => {
    const result = params.get("connected");
    if (!result) return;
    if (result === "ok") {
      toast(t("Connected: {email}", { email: params.get("email") || "" }));
      onConnected?.(params.get("purpose"));
    } else {
      toast(params.get("message") || t("The account was not connected."), "danger");
    }
    setParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

// Warning above a page when the sender mailbox has expired or is about to.
export function MailNotice({ status }) {
  if (!status?.connected) return null;
  if (status.expired) {
    return <Alert>{t("The sender mailbox connection has expired, so emails cannot be sent. Reconnect it below.")}</Alert>;
  }
  if (status.expiring_soon) {
    return (
      <Alert tone="warning">
        {t("The sender mailbox connection ends on {when}. Reconnect it now so sending does not stop.", { when: stamp(status.expires_at) })}
      </Alert>
    );
  }
  return null;
}

// The channel line: mailbox state with connect / reconnect / disconnect, and WhatsApp availability.
export function ChannelStatus({ integrations, page, busy, onBusy, onChanged }) {
  const mail = integrations?.mail || {};
  const wa = integrations?.whatsapp || {};
  const connect = async () => {
    onBusy?.(true);
    try {
      await connectAccount("mail", page);
    } catch (e) {
      onBusy?.(false);
      alert(e.message);
    }
  };
  const disconnect = async () => {
    if (!window.confirm(t("Disconnect the sender mailbox? Sending emails will stop."))) return;
    await disconnectAccount("mail");
    onChanged?.();
  };
  let mailPart;
  if (!mail.connected) {
    mailPart = (
      <>
        <span className="status bad">{t("Email: not connected")}</span>
        <button type="button" className="button small" onClick={connect} disabled={busy}>
          {t("Connect sender mailbox")}
        </button>
      </>
    );
  } else if (mail.expired) {
    mailPart = (
      <>
        <span className="status bad">{t("Email: connection expired")}</span>
        <button type="button" className="button small primary" onClick={connect} disabled={busy}>
          {t("Reconnect")}
        </button>
      </>
    );
  } else {
    mailPart = (
      <>
        <span className={`status ${mail.expiring_soon ? "warn" : "ok"}`}>
          <Icon name={mail.expiring_soon ? "clock" : "check"} size={15} /> {t("Email: {email}", { email: mail.email })}
        </span>
        {mail.expires_at ? <span className="muted">{t("until {when}", { when: stamp(mail.expires_at) })}</span> : null}
        {mail.expiring_soon ? (
          <button type="button" className="button small primary" onClick={connect} disabled={busy}>
            {t("Reconnect")}
          </button>
        ) : (
          <button type="button" className="button small ghost" onClick={disconnect}>
            {t("Disconnect")}
          </button>
        )}
      </>
    );
  }
  return (
    <div className="channels">
      <span className="channel">{mailPart}</span>
      <span className="channel">
        {wa.ready ? (
          <span className="status ok">
            <Icon name="check" size={15} /> {t("WhatsApp ready")}
            {wa.mode === "mock" ? <span className="muted"> ({t("simulated")})</span> : null}
          </span>
        ) : (
          <span className="status bad">{t("WhatsApp not configured")}</span>
        )}
      </span>
    </div>
  );
}
