import { useCallback, useEffect, useState } from "react";
import { api, download } from "../../api/client.js";
import { defaultCohort, useCohorts } from "../../api/hooks.js";
import { ChannelStatus, MailNotice, useConnectReturn } from "../../components/Channels.jsx";
import Icon from "../../components/Icon.jsx";
import { CohortSelect, range, WeekSelect } from "../../components/Pickers.jsx";
import RecipientPicker from "../../components/RecipientPicker.jsx";
import TestSendDialog from "../../components/TestSendDialog.jsx";
import { useToast } from "../../components/Toast.jsx";
import { Alert, Empty, Loading, PageHeader, stamp, Tabs } from "../../components/ui.jsx";
import { t } from "../../i18n/index.js";
import AgendaDay from "./AgendaDay.jsx";

const TITLES = { midterm: "Midterm exam schedule", final: "Final exam schedule", career: "Career day schedule" };
const KINDS = [
  { value: "week", label: "Week" },
  { value: "midterm", label: "Midterm exam" },
  { value: "final", label: "Final exam" },
  { value: "career", label: "Career day" },
];

export default function AgendaPage() {
  const [cohorts, cohortsError] = useCohorts();
  const [cohort, setCohort] = useState(null);
  const [week, setWeek] = useState(1);
  const [kind, setKind] = useState("week");
  const [agenda, setAgenda] = useState(null);
  const [days, setDays] = useState([]);
  const [dirty, setDirty] = useState(false);
  const [courses, setCourses] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [failed, setFailed] = useState([]);
  const [picker, setPicker] = useState("");
  const [testOpen, setTestOpen] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (cohort || !cohorts) return;
    const first = defaultCohort(cohorts);
    if (first) {
      setCohort(first.number);
      setWeek(first.current_week);
    }
  }, [cohorts, cohort]);
  useEffect(() => {
    api("courses/").then((d) => setCourses(d.courses.map((c) => c.name))).catch(() => {});
  }, []);

  const load = useCallback(() => {
    if (!cohort) return;
    setError("");
    setAgenda(null);
    api(`cohorts/${cohort}/agenda/`, { query: { week, kind } })
      .then((d) => {
        setAgenda(d);
        setDays(d.days);
        setDirty(false);
      })
      .catch((e) => setError(e.message));
  }, [cohort, week, kind]);
  useEffect(load, [load]);
  useConnectReturn(load);

  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (e) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const leaveOk = () => !dirty || window.confirm(t("Unsaved changes will be lost. Continue?"));
  const edit = (change) => {
    setDays((current) => {
      const next = structuredClone(current);
      change(next);
      return next;
    });
    setDirty(true);
  };
  const current = cohorts?.find((c) => c.number === cohort);

  const save = async () => {
    setBusy("save");
    setError("");
    try {
      const d = await api(`cohorts/${cohort}/agenda/`, { method: "PUT", body: { week, kind, days } });
      setAgenda(d);
      setDays(d.days);
      setDirty(false);
      toast(t("Agenda saved"));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  };
  const ensureSaved = async () => (dirty || !agenda.saved ? save() : true);

  const pdf = async () => {
    if (!(await ensureSaved())) return;
    setBusy("pdf");
    try {
      const file = await api(`cohorts/${cohort}/agenda/pdf/`, { query: { week, kind }, blob: true });
      download(file, `agenda-cohort-${cohort}-${kind === "week" ? `week-${week}` : kind}.pdf`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  };

  const send = async (channel, { testTo = "", studentIds = [] } = {}) => {
    if (!(await ensureSaved())) return false;
    setBusy(testTo ? `test-${channel}` : channel);
    setError("");
    setFailed([]);
    try {
      const body = { week, kind, channel, ...(testTo ? { test_to: testTo } : { student_ids: studentIds }) };
      const d = await api(`cohorts/${cohort}/agenda/send/`, { method: "POST", body });
      setAgenda(d.agenda);
      setFailed(d.failed);
      toast(
        testTo
          ? t("Test sent to {to}", { to: testTo })
          : t("Sent to {n} students", { n: d.sent }) + (d.failed.length ? ` · ${t("{n} failed", { n: d.failed.length })}` : ""),
      );
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  };

  if (cohortsError) return <Alert>{cohortsError}</Alert>;
  if (!cohorts) return <Loading />;
  if (!cohorts.length) return <Empty>{t("There are no cohorts yet.")}</Empty>;
  const mail = agenda?.integrations?.mail;
  const mailReady = mail?.connected && !mail.expired;
  const waReady = agenda?.integrations?.whatsapp?.ready;

  return (
    <>
      <PageHeader
        title={t("Agenda")}
        subtitle={t("Build the timetable for a teaching week, an exam or the career day, then send it to students by email or WhatsApp with a PDF.")}
      >
        <CohortSelect
          cohorts={cohorts}
          value={cohort}
          onChange={(n) => {
            if (!leaveOk()) return;
            setCohort(n);
            setWeek(cohorts.find((c) => c.number === n)?.current_week || 1);
          }}
        />
        {kind === "week" ? <WeekSelect weeks={range(current?.weeks_total || 12)} value={week} onChange={(w) => leaveOk() && setWeek(w)} /> : null}
      </PageHeader>
      <Tabs
        label={t("Agenda type")}
        items={KINDS.map((k) => ({ value: k.value, label: t(k.label) }))}
        value={kind}
        onChange={(k) => leaveOk() && setKind(k)}
      />
      {error ? <Alert>{error}</Alert> : null}
      {failed.length ? <Alert>{t("Not sent to: {list}", { list: failed.map((f) => `${f.to}${f.error ? ` (${f.error})` : ""}`).join("; ") })}</Alert> : null}
      {!agenda ? (
        <Loading />
      ) : (
        <>
          <MailNotice status={mail} />
          <ChannelStatus integrations={agenda.integrations} page="agenda" busy={busy === "connect"} onBusy={(b) => setBusy(b ? "connect" : "")} onChanged={load} />
          <div className="actionbar">
            <span className="actionbar-status">
              {agenda.saved ? (
                <>
                  {t("Saved {when}", { when: stamp(agenda.updated_at) })}
                  {agenda.updated_by ? ` · ${agenda.updated_by}` : ""}
                </>
              ) : kind === "week" ? (
                t("Draft prefilled from this week's lessons")
              ) : (
                t("Draft")
              )}
              {dirty ? <b className="warn-text"> · {t("unsaved changes")}</b> : null}
              {agenda.emailed_at ? (
                <span className="status ok">
                  <Icon name="check" size={14} /> {t("Email {when} · {n} students", { when: stamp(agenda.emailed_at), n: agenda.emailed_count })}
                </span>
              ) : null}
              {agenda.whatsapp_at ? (
                <span className="status ok">
                  <Icon name="check" size={14} /> {t("WhatsApp {when} · {n} students", { when: stamp(agenda.whatsapp_at), n: agenda.whatsapp_count })}
                </span>
              ) : null}
            </span>
            <span className="actionbar-buttons">
              <button type="button" className="button" onClick={save} disabled={!!busy || (!dirty && agenda.saved)}>
                {busy === "save" ? t("Saving…") : t("Save")}
              </button>
              <button type="button" className="button" onClick={pdf} disabled={!!busy}>
                <Icon name="download" size={15} /> {busy === "pdf" ? t("Preparing…") : t("Download PDF")}
              </button>
              <button type="button" className="button" onClick={() => setTestOpen(true)} disabled={!!busy || !(mailReady || waReady)}>
                {t("Send test")}
              </button>
              <button type="button" className="button primary" onClick={() => setPicker("email")} disabled={!!busy || !mailReady}>
                <Icon name="mail" size={15} /> {busy === "email" ? t("Sending…") : t("Send by email")}
              </button>
              <button type="button" className="button whatsapp" onClick={() => setPicker("whatsapp")} disabled={!!busy || !waReady}>
                <Icon name="phone" size={15} /> {busy === "whatsapp" ? t("Sending…") : t("Send by WhatsApp")}
              </button>
            </span>
          </div>
          <div className="agenda">
            <h2 className="agenda-title">{kind === "week" ? t("Week {n} timetable", { n: week }) : t(TITLES[kind])}</h2>
            {days.map((day, i) => (
              <AgendaDay key={i} day={day} index={i} courses={courses} edit={edit} />
            ))}
          </div>
        </>
      )}
      {picker ? (
        <RecipientPicker
          channel={picker}
          cohort={cohort}
          note={t("the agenda PDF is attached")}
          busy={busy === picker}
          onClose={() => setPicker("")}
          onSend={async (ids) => {
            if (await send(picker, { studentIds: ids })) setPicker("");
          }}
        />
      ) : null}
      {testOpen ? (
        <TestSendDialog
          intro={t("The agenda (with its PDF) goes only to this address, so you can check it before students get it.")}
          email={mailReady}
          whatsapp={waReady}
          busy={busy.startsWith("test")}
          onClose={() => setTestOpen(false)}
          onSend={async (to, phone) => {
            let ok = true;
            if (to) ok = await send("email", { testTo: to });
            if (ok && phone) ok = await send("whatsapp", { testTo: phone });
            if (ok) setTestOpen(false);
          }}
        />
      ) : null}
    </>
  );
}
