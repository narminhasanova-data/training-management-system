import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { defaultCohort } from "../../api/hooks.js";
import Icon from "../../components/Icon.jsx";
import RecipientPicker from "../../components/RecipientPicker.jsx";
import TestSendDialog from "../../components/TestSendDialog.jsx";
import { useToast } from "../../components/Toast.jsx";
import { Alert, Card, Loading } from "../../components/ui.jsx";
import { t } from "../../i18n/index.js";

const TYPES = { file: "File", link: "Link", video: "Video", form: "Form" };

// "Training materials": each course's Classroom material posts (the same in every cohort), opened
// from here and emailed to chosen students of a cohort.
export default function MaterialsLibrary({ cohorts, onReconnect, reconnecting }) {
  const [course, setCourse] = useState("");
  const [cohort, setCohort] = useState(null);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [picker, setPicker] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();

  useEffect(() => {
    if (cohort == null && cohorts.length) setCohort(defaultCohort(cohorts).number);
  }, [cohorts, cohort]);
  useEffect(() => {
    if (cohort == null) return;
    setLoading(true);
    setError("");
    api("library/", { query: { course, cohort } })
      .then((d) => {
        setData(d);
        if (!course) setCourse(d.course);
        setSelected(new Set(d.items.map((i) => i.id)));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [course, cohort]);

  const send = async ({ studentIds = [], testTo = "" }) => {
    setBusy(testTo ? "test" : "send");
    setError("");
    try {
      const body = { course, cohort, material_ids: [...selected], ...(testTo ? { test_to: testTo } : { student_ids: studentIds }) };
      const d = await api("library/send/", { method: "POST", body });
      toast(testTo ? t("Test sent to {to}", { to: testTo }) : t("{course} materials sent to {n} students", { course, n: d.sent }));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  };

  const groups = [];
  for (const item of data?.items || []) {
    const topic = item.topic || (item.week ? t("Week {n}", { n: item.week }) : t("Materials"));
    let group = groups.find((g) => g.topic === topic);
    if (!group) groups.push((group = { topic, items: [] }));
    group.items.push(item);
  }
  const allSelected = data?.items.length && selected.size === data.items.length;
  const cohortName = cohorts.find((c) => c.number === cohort)?.name || "";

  return (
    <Card title={t("Training materials")} aside={<span className="muted">{t("Classroom material posts · the same for every cohort of a course")}</span>}>
      {error ? <Alert>{error}</Alert> : null}
      {data && !data.materials_permission ? (
        <Alert tone="warning">
          {t("Reading materials needs one more permission. Reconnect the Classroom account once and allow “View class materials”.")}{" "}
          <button type="button" className="button small primary" onClick={onReconnect} disabled={reconnecting}>
            {t("Reconnect")}
          </button>
        </Alert>
      ) : null}
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="course-chips" role="tablist" aria-label={t("Course")}>
            {data.courses.map((c) => (
              <button
                key={c.name}
                type="button"
                role="tab"
                aria-selected={c.name === course}
                className={`course-chip ${c.name === course ? "on" : ""}`}
                onClick={() => setCourse(c.name)}
              >
                {c.name}
                <small>{c.count}</small>
              </button>
            ))}
          </div>
          <div className="actionbar">
            <span className="actionbar-status">
              <select className="select" aria-label={t("Cohort")} value={cohort ?? ""} onChange={(e) => setCohort(Number(e.target.value))}>
                {cohorts.map((c) => (
                  <option key={c.number} value={c.number}>
                    {c.name}
                  </option>
                ))}
              </select>
              {data.items.length ? (
                <button type="button" className="button small ghost" onClick={() => setSelected(allSelected ? new Set() : new Set(data.items.map((i) => i.id)))}>
                  {allSelected ? t("Clear selection") : t("Select all")}
                </button>
              ) : null}
              {data.source ? <span className="muted small">{t("List from {name} (the fullest set)", { name: data.source.name })}</span> : null}
            </span>
            <span className="actionbar-buttons">
              {!data.mail_ready ? <span className="status bad">{t("Email not connected (connect it on the Agenda page)")}</span> : null}
              <button type="button" className="button" onClick={() => setTestOpen(true)} disabled={!!busy || !data.mail_ready || !selected.size}>
                {t("Send test")}
              </button>
              <button type="button" className="button primary" onClick={() => setPicker(true)} disabled={loading || !!busy || !data.mail_ready || !selected.size}>
                <Icon name="mail" size={15} /> {busy === "send" ? t("Sending…") : t("Send by email ({n} materials)", { n: selected.size })}
              </button>
            </span>
          </div>
          {loading ? (
            <Loading />
          ) : !data.items.length ? (
            <p className="muted">{data.materials_permission ? t("Classroom has no materials for {course}.", { course }) : t("Materials appear here after reconnecting.")}</p>
          ) : (
            <div className="library">
              {groups.map((g) => (
                <div key={g.topic} className="library-group">
                  <p className="library-topic">{g.topic}</p>
                  {g.items.map((item) => (
                    <label key={item.id} className="library-item">
                      <input
                        type="checkbox"
                        checked={selected.has(item.id)}
                        onChange={(e) =>
                          setSelected((current) => {
                            const next = new Set(current);
                            if (e.target.checked) next.add(item.id);
                            else next.delete(item.id);
                            return next;
                          })
                        }
                      />
                      <span className="library-body">
                        <b>{item.title}</b>
                        {item.description ? <span className="muted small">{item.description}</span> : null}
                        <span className="library-files">
                          {item.attachments.map((a, i) =>
                            a.url ? (
                              <a key={i} href={a.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                                <small>{t(TYPES[a.type] || "Link")}</small>
                                {a.title || a.url}
                              </a>
                            ) : null,
                          )}
                        </span>
                        {item.from_other_cohort ? (
                          <span className="status warn small">
                            {t("Not in {name}'s Classroom: the link is from cohort {n}, so students may not have access.", { name: cohortName, n: item.cohort })}
                          </span>
                        ) : null}
                      </span>
                    </label>
                  ))}
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {picker ? (
        <RecipientPicker
          channel="email"
          cohort={cohort}
          only
          note={t("{n} {course} materials will be sent", { n: selected.size, course })}
          busy={busy === "send"}
          onClose={() => setPicker(false)}
          onSend={async (ids) => {
            if (await send({ studentIds: ids })) setPicker(false);
          }}
        />
      ) : null}
      {testOpen ? (
        <TestSendDialog
          intro={t("The selected materials go only to this address, so you can check the email first.")}
          busy={busy === "test"}
          onClose={() => setTestOpen(false)}
          onSend={async (to) => {
            if (await send({ testTo: to })) setTestOpen(false);
          }}
        />
      ) : null}
    </Card>
  );
}
