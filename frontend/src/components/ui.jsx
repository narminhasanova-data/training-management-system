import { useEffect, useRef } from "react";
import { t } from "../i18n/index.js";
import Icon from "./Icon.jsx";

export function PageHeader({ title, subtitle, children }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {children ? <div className="page-header-tools">{children}</div> : null}
    </header>
  );
}

export function Card({ title, aside, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {title || aside ? (
        <div className="card-head">
          {title ? <h2>{title}</h2> : null}
          {aside ? <div className="card-aside">{aside}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Tabs({ items, value, onChange, label }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          role="tab"
          aria-selected={item.value === value}
          className={item.value === value ? "active" : ""}
          onClick={() => onChange(item.value)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button type="button" className="icon-button" onClick={onClose} aria-label={t("Close")}>
            <Icon name="x" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export function Kpi({ icon, label, value, tone = "brand" }) {
  return (
    <div className={`kpi tone-${tone}`}>
      <span className="kpi-icon">
        <Icon name={icon} />
      </span>
      <div>
        <div className="kpi-value">{value}</div>
        <div className="kpi-label">{label}</div>
      </div>
    </div>
  );
}

export function Badge({ tone = "neutral", children, title }) {
  return (
    <span className={`badge tone-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function Alert({ tone = "danger", children }) {
  return (
    <div className={`alert tone-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <Icon name={tone === "danger" ? "alert" : "clock"} />
      <div>{children}</div>
    </div>
  );
}

export function Loading({ label }) {
  return <p className="muted loading">{label || t("Loading…")}</p>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function PrototypeBanner() {
  return (
    <Alert tone="warning">
      <b>{t("Prototype")}</b> · {t("This page shows sample data and is not connected to the API. It is kept to show the planned design.")}
    </Alert>
  );
}

// "07.11 14:05" in the browser's time zone.
export function stamp(value) {
  if (!value) return "";
  const d = new Date(value);
  const two = (n) => String(n).padStart(2, "0");
  return `${two(d.getDate())}.${two(d.getMonth() + 1)} ${two(d.getHours())}:${two(d.getMinutes())}`;
}

export function scoreTone(value, { high = 4.5, low = 3 } = {}) {
  if (value == null) return "neutral";
  if (value >= high) return "success";
  return value < low ? "danger" : "neutral";
}
