import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { defaultCohort, useCohorts } from "../../api/hooks.js";
import { ChannelStatus, MailNotice, useConnectReturn } from "../../components/Channels.jsx";
import Icon from "../../components/Icon.jsx";
import { CohortSelect, range, WeekSelect } from "../../components/Pickers.jsx";
import RecipientPicker from "../../components/RecipientPicker.jsx";
import TestSendDialog from "../../components/TestSendDialog.jsx";
import { useToast } from "../../components/Toast.jsx";
import { Alert, Empty, Loading, PageHeader, stamp, Tabs } from "../../components/ui.jsx";
import { t } from "../../i18n/index.js";
import CourseCatalog from "./CourseCatalog.jsx";
import SurveyEditor from "./SurveyEditor.jsx";
import SurveyResults from "./SurveyResults.jsx";

const FIELDS = ["title", "blocks", "trainers", "mentors", "materials", "grid_weeks"];
const pick = (d) => Object.fromEntries(FIELDS.map((k) => [k, d[k]]));

export default function SurveyPage() {
  const [cohorts, cohortsError] = useCohorts();
  const [cohort, setCohort] = useState(null);
  const [week, setWeek] = useState(1);
  const [tab, setTab] = useState("editor");
  const [survey, setSurvey] = useState(null);
  const [form, setForm] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [failed, setFailed] = useState([]);
  const [picker, setPicker] = useState(null);
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

  const take = (d) => {
    setSurvey(d);
    setForm(pick(d));
    setDirty(false);
  };
  const load = useCallback(() => {
    if (!cohort) return;
    setError("");
    setSurvey(null);
    api(`cohorts/${cohort}/survey/`, { query: { week } }).then(take).catch((e) => setError(e.message));
  }, [cohort, week]);
  useEffect(load, [load]);
  useConnectReturn(load);

  const leaveOk = () => !dirty || window.confirm(t("Unsaved changes will be lost. Continue?"));
  const edit = (change) => {
    setForm((current) => {
      const next = structuredClone(current);
      change(next);
      return next;
    });
    setDirty(true);
  };

  const save = async () => {
    setBusy("save");
    setError("");
    try {
      take(await api(`cohorts/${cohort}/survey/`, { method: "PUT", body: { week, ...form } }));
      toast(t("Survey saved"));
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy("");
    }
  };
  const ensureSaved = async () => (dirty || !survey.saved ? save() : true);

  const preview = async () => {
    const win = window.open("", "_blank"); // opened before the save, or the browser blocks the pop-up
    if (!(await ensureSaved())) {
      win?.close();
      return;
    }
    const d = await api(`cohorts/${cohort}/survey/`, { query: { week } });
    if (win) win.location.href = d.preview_url;
  };

  const send = async (channel, { testTo = "", studentIds = [] } = {}) => {
    if (!(await ensureSaved())) return false;
    setBusy(testTo ? `test-${channel}` : channel);
    setError("");
    setFailed([]);
    try {
      const body = { week, channel, ...(testTo ? { test_to: testTo } : { student_ids: studentIds }) };
      const d = await api(`cohorts/${cohort}/survey/send/`, { method: "POST", body });
      take(d.survey);
      setFailed(d.failed);
      toast(
        testTo
          ? t("Test sent to {to}", { to: testTo })
          : t("Links sent to {n} students", { n: d.sent }) + (d.failed.length ? ` · ${t("{n} failed", { n: d.failed.length })}` : ""),
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
  const current = cohorts.find((c) => c.number === cohort);
  const results = survey?.results;
  const mail = survey?.integrations?.mail;
  const mailReady = mail?.connected && !mail.expired;
  const waReady = survey?.integrations?.whatsapp?.ready;
  const tabs = [
    { value: "editor", label: t("Survey") },
    { value: "results", label: results ? t("Results ({answered}/{invited})", results) : t("Results") },
    { value: "courses", label: t("Courses") },
  ];

  return (
    <>
      <PageHeader
        title={t("Weekly survey")}
        subtitle={t("Courses, trainers and mentors change every week: set them here, send each student a personal link, and follow the answers in Results.")}
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
        <WeekSelect weeks={range(current?.weeks_total || 12)} value={week} onChange={(w) => leaveOk() && setWeek(w)} />
      </PageHeader>
      <Tabs label={t("Survey sections")} items={tabs} value={tab} onChange={(v) => (v !== "courses" || leaveOk()) && setTab(v)} />
      {error ? <Alert>{error}</Alert> : null}
      {failed.length ? <Alert>{t("Not sent to: {list}", { list: failed.map((f) => f.to).join("; ") })}</Alert> : null}

      {tab === "courses" ? (
        <CourseCatalog
          onSaved={() => {
            toast(t("Courses saved"));
            load();
          }}
        />
      ) : !survey || !form ? (
        <Loading />
      ) : tab === "results" ? (
        <SurveyResults
          results={results}
          scales={survey.scales}
          canRemind={mailReady || waReady}
          onRemind={(ids) => setPicker({ channel: mailReady ? "email" : "whatsapp", preselect: ids })}
        />
      ) : (
        <>
          <MailNotice status={mail} />
          <ChannelStatus integrations={survey.integrations} page="surveys" busy={busy === "connect"} onBusy={(b) => setBusy(b ? "connect" : "")} onChanged={load} />
          <div className="actionbar">
            <span className="actionbar-status">
              {survey.saved ? (
                <>
                  {t("Saved {when}", { when: stamp(survey.updated_at) })}
                  {survey.updated_by ? ` · ${survey.updated_by}` : ""}
                </>
              ) : (
                t("Draft prefilled from this week's lessons (or last week's survey)")
              )}
              {dirty ? <b className="warn-text"> · {t("unsaved changes")}</b> : null}
              {results?.invited ? (
                <span className="status ok">
                  <Icon name="check" size={14} /> {t("Sent to {invited} · {answered} answered", results)}
                </span>
              ) : null}
            </span>
            <span className="actionbar-buttons">
              <button type="button" className="button" onClick={save} disabled={!!busy || (!dirty && survey.saved)}>
                {busy === "save" ? t("Saving…") : t("Save")}
              </button>
              <button type="button" className="button" onClick={preview} disabled={!!busy}>
                <Icon name="eye" size={15} /> {t("Preview")}
              </button>
              <button type="button" className="button" onClick={() => setTestOpen(true)} disabled={!!busy || !(mailReady || waReady)}>
                {t("Send test")}
              </button>
              <button type="button" className="button primary" onClick={() => setPicker({ channel: "email" })} disabled={!!busy || !mailReady}>
                <Icon name="mail" size={15} /> {busy === "email" ? t("Sending…") : t("Send by email")}
              </button>
              <button type="button" className="button whatsapp" onClick={() => setPicker({ channel: "whatsapp" })} disabled={!!busy || !waReady}>
                <Icon name="phone" size={15} /> {busy === "whatsapp" ? t("Sending…") : t("Send by WhatsApp")}
              </button>
            </span>
          </div>
          <SurveyEditor form={form} survey={survey} week={week} edit={edit} />
        </>
      )}

      {picker ? (
        <RecipientPicker
          channel={picker.channel}
          cohort={cohort}
          only
          preselect={picker.preselect}
          note={t("each student gets a personal link")}
          busy={busy === picker.channel}
          onClose={() => setPicker(null)}
          onSend={async (ids) => {
            if (await send(picker.channel, { studentIds: ids })) setPicker(null);
          }}
        />
      ) : null}
      {testOpen ? (
        <TestSendDialog
          intro={t("Only the preview link is sent (answers given there are not saved). Check the survey before students get it.")}
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
