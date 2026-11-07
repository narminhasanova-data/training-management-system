import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { t } from "../i18n/index.js";
import Icon from "./Icon.jsx";
import { Loading, Modal } from "./ui.jsx";

// "Who should receive this?": every cohort with a tick (only `cohort` when `only`), each expandable
// to its students. The current cohort's students (or `preselect`) start ticked.
export default function RecipientPicker({ channel, cohort, only = false, preselect, note, busy, onSend, onClose }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [open, setOpen] = useState({});

  useEffect(() => {
    api("recipients/", { query: { channel } })
      .then((data) => {
        const cohorts = only ? data.cohorts.filter((c) => c.number === cohort) : data.cohorts;
        setList(cohorts);
        const ids = (data.cohorts.find((c) => c.number === cohort)?.people || []).map((p) => p.id);
        setSelected(new Set(preselect ? ids.filter((id) => preselect.includes(id)) : ids));
        setOpen({ [cohort]: true });
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel, cohort]);

  const toggle = (ids, on) =>
    setSelected((current) => {
      const next = new Set(current);
      ids.forEach((id) => (on ? next.add(id) : next.delete(id)));
      return next;
    });

  return (
    <Modal title={channel === "whatsapp" ? t("Send by WhatsApp: choose students") : t("Send by email: choose students")} onClose={onClose} wide>
      {error ? <p className="error-text">{error}</p> : null}
      {!list ? (
        <Loading />
      ) : (
        <div className="picker">
          {list.map((c) => {
            const ids = c.people.map((p) => p.id);
            const count = ids.filter((id) => selected.has(id)).length;
            return (
              <div key={c.number} className="picker-group">
                <div className="picker-head">
                  <label>
                    <input
                      type="checkbox"
                      checked={ids.length > 0 && count === ids.length}
                      disabled={!ids.length}
                      ref={(el) => {
                        if (el) el.indeterminate = count > 0 && count < ids.length;
                      }}
                      onChange={(e) => toggle(ids, e.target.checked)}
                    />
                    <b>{c.name}</b>
                    {c.status === "running" ? <span className="muted"> · {t("running")}</span> : null}
                  </label>
                  <span className="muted">
                    {count}/{ids.length}
                  </span>
                  <button
                    type="button"
                    className="button small ghost"
                    aria-expanded={!!open[c.number]}
                    onClick={() => setOpen((o) => ({ ...o, [c.number]: !o[c.number] }))}
                  >
                    {open[c.number] ? t("Hide") : t("Students")} <Icon name="chevron" size={14} className={open[c.number] ? "rot90" : ""} />
                  </button>
                </div>
                {open[c.number] ? (
                  <div className="picker-list">
                    {c.people.length ? (
                      c.people.map((p) => (
                        <label key={p.id}>
                          <input type="checkbox" checked={selected.has(p.id)} onChange={(e) => toggle([p.id], e.target.checked)} />
                          <span>{p.name}</span>
                          <span className="muted">{p.to}</span>
                        </label>
                      ))
                    ) : (
                      <span className="muted">{channel === "whatsapp" ? t("No student has a phone number.") : t("No student has an email address.")}</span>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
      <div className="modal-foot">
        <span className="muted">
          {t("Selected: {n} students", { n: selected.size })}
          {note ? ` · ${note}` : ""}
        </span>
        <button type="button" className="button primary" disabled={busy || !selected.size} onClick={() => onSend([...selected])}>
          <Icon name="send" size={15} /> {busy ? t("Sending…") : t("Send ({n})", { n: selected.size })}
        </button>
      </div>
    </Modal>
  );
}
