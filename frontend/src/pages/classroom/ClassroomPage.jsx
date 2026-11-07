import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { useCohorts, useResource } from "../../api/hooks.js";
import { connectAccount, disconnectAccount, useConnectReturn } from "../../components/Channels.jsx";
import Icon from "../../components/Icon.jsx";
import { useToast } from "../../components/Toast.jsx";
import { Alert, Badge, Card, Loading, PageHeader, stamp } from "../../components/ui.jsx";
import { t } from "../../i18n/index.js";
import MaterialsLibrary from "./MaterialsLibrary.jsx";

const STATES = { ACTIVE: "running", PROVISIONED: "not started", ARCHIVED: "archived" };

export default function ClassroomPage() {
  const [cohorts, cohortsError, reloadCohorts] = useCohorts();
  const [integrations, integrationsError, reloadIntegrations] = useResource("integrations/");
  const [classes, setClasses] = useState(null);
  const [ticked, setTicked] = useState(null);
  const [busy, setBusy] = useState("");
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const toast = useToast();
  const account = integrations?.classroom;
  const live = account?.connected && !account.expired;

  const loadClasses = useCallback(() => {
    api("classroom/classes/")
      .then((d) => {
        setClasses(d);
        setTicked((current) => current || new Set(d.cohorts.filter((c) => c.new_classes).map((c) => c.number)));
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (live) loadClasses();
  }, [live, loadClasses]);
  useConnectReturn(() => {
    reloadIntegrations();
    toast(t("Materials are being loaded from Classroom"), "neutral");
  });

  const connect = async () => {
    setBusy("connect");
    try {
      await connectAccount("classroom", "classroom");
    } catch (e) {
      setError(e.message);
      setBusy("");
    }
  };
  const disconnect = async () => {
    if (!window.confirm(t("Disconnect Classroom? Homework and grades will stop updating."))) return;
    await disconnectAccount("classroom").catch((e) => setError(e.message));
    setClasses(null);
    reloadIntegrations();
  };

  const syncOne = async (number, addUnmatched = false) => {
    setBusy(`sync-${number}`);
    setError("");
    try {
      const d = await api(`cohorts/${number}/classroom/sync/`, { method: "POST", body: { add_unmatched: addUnmatched } });
      reloadCohorts();
      toast(t("{name}: updated from Classroom", { name: d.cohort.name }));
    } catch (e) {
      setError(e.message);
      reloadCohorts();
    } finally {
      setBusy("");
    }
  };
  const linked = (cohorts || []).filter((c) => c.classroom.classes.length);
  const syncAll = async () => {
    setBusy("sync-all");
    setError("");
    try {
      for (const [i, c] of linked.entries()) {
        setProgress(t("{i} of {n}: {name}", { i: i + 1, n: linked.length, name: c.name }));
        await api(`cohorts/${c.number}/classroom/sync/`, { method: "POST", body: {} }).catch((e) => setError(`${c.name}: ${e.message}`));
      }
      toast(t("All linked cohorts updated"));
    } finally {
      setBusy("");
      setProgress("");
      reloadCohorts();
    }
  };
  const importTicked = async () => {
    const todo = classes.cohorts.filter((c) => ticked.has(c.number) && c.new_classes);
    setBusy("import");
    setError("");
    let added = 0;
    try {
      for (const [i, c] of todo.entries()) {
        setProgress(t("{i} of {n}: {name} ({classes} classes)", { i: i + 1, n: todo.length, name: c.name, classes: c.classes.length }));
        const d = await api("classroom/import/", { method: "POST", body: { number: c.number } });
        if (d.cohort.classroom.summary?.error) setError(`${c.name}: ${d.cohort.classroom.summary.error}`);
        added += 1;
      }
      toast(t("{n} cohorts brought onto the site", { n: added }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
      setProgress("");
      setTicked(new Set());
      reloadCohorts();
      loadClasses();
    }
  };

  if (cohortsError || integrationsError) return <Alert>{cohortsError || integrationsError}</Alert>;
  const tickable = classes ? classes.cohorts.filter((c) => ticked?.has(c.number) && c.new_classes).length : 0;
  const soon = live && account.expiring_soon;

  return (
    <>
      <PageHeader
        title={t("Classroom")}
        subtitle={t("Cohorts in Google Classroom: students, coursework, submissions and grades come here and stay up to date (running cohorts every 15 minutes).")}
      />
      {error ? <Alert>{error}</Alert> : null}
      {account?.expired ? (
        <Alert>{t("The Classroom connection has expired, so homework and grades are not updating. Reconnect below.")}</Alert>
      ) : soon ? (
        <Alert tone="warning">{t("The Classroom connection ends on {when}. Reconnect now so updates do not stop.", { when: stamp(account.expires_at) })}</Alert>
      ) : null}

      <Card title={t("Google account")}>
        {!integrations ? (
          <Loading />
        ) : account.connected ? (
          <div className="account-line">
            <span className={`status ${account.expired ? "bad" : soon ? "warn" : "ok"}`}>
              <Icon name={account.expired ? "alert" : soon ? "clock" : "check"} size={16} /> {account.email}
            </span>
            <span className="muted">
              {t("connected {when}", { when: stamp(account.connected_at) })}
              {account.connected_by ? ` · ${account.connected_by}` : ""}
              {account.expires_at ? ` · ${t("until {when}", { when: stamp(account.expires_at) })}` : ""}
            </span>
            {account.mode === "mock" ? <Badge tone="warning">{t("mock")}</Badge> : null}
            {account.expired || soon ? (
              <button type="button" className="button primary" onClick={connect} disabled={busy === "connect"}>
                {t("Reconnect")}
              </button>
            ) : null}
            <button type="button" className="button small" onClick={disconnect}>
              {t("Disconnect")}
            </button>
          </div>
        ) : (
          <div className="account-line">
            <span className="muted">{t("Connect the account that teaches the Classroom classes. In this demo a mock sign-in screen opens; no real Google account is used.")}</span>
            <button type="button" className="button primary" onClick={connect} disabled={busy === "connect"}>
              {busy === "connect" ? t("Opening…") : t("Connect Google account")}
            </button>
          </div>
        )}
      </Card>

      {live ? <MaterialsLibrary cohorts={cohorts || []} onReconnect={connect} reconnecting={busy === "connect"} /> : null}

      {live ? (
        <Card
          title={t("Cohorts in Classroom")}
          aside={
            <>
              {classes ? <span className="muted">{t("Cohort {n} and later · {count} cohorts", { n: classes.min_cohort, count: classes.cohorts.length })}</span> : null}
              <button type="button" className="button primary" onClick={importTicked} disabled={!!busy || !tickable}>
                <Icon name="download" size={15} /> {busy === "import" ? t("Adding…") : t("Bring selected onto the site ({n})", { n: tickable })}
              </button>
              <button type="button" className="button" onClick={syncAll} disabled={!!busy || !linked.length}>
                <Icon name="refresh" size={15} /> {busy === "sync-all" ? t("Updating…") : t("Update all")}
              </button>
            </>
          }
        >
          {progress ? <Alert tone="info">{progress}</Alert> : null}
          {!classes ? (
            <Loading />
          ) : !classes.cohorts.length ? (
            <p className="muted">{t("Classroom has no classes for cohort {n} or later.", { n: classes.min_cohort })}</p>
          ) : (
            <div className="class-list">
              {classes.cohorts.map((c) => (
                <label key={c.number} className={`class-row ${c.new_classes ? "" : "on-site"}`}>
                  <input
                    type="checkbox"
                    disabled={!c.new_classes || !!busy}
                    checked={!c.new_classes || !!ticked?.has(c.number)}
                    onChange={(e) =>
                      setTicked((current) => {
                        const next = new Set(current);
                        if (e.target.checked) next.add(c.number);
                        else next.delete(c.number);
                        return next;
                      })
                    }
                  />
                  <span className="class-name">
                    <b>{c.name}</b>
                    <span className="chips">
                      {c.classes.map((x) => (
                        <span key={x.id} className="chip" title={x.name}>
                          {x.course || x.name}
                          {x.state !== "ACTIVE" && STATES[x.state] ? <small> · {t(STATES[x.state])}</small> : null}
                        </span>
                      ))}
                    </span>
                  </span>
                  <span className={c.on_site ? "status ok" : "muted"}>
                    {c.on_site ? (
                      <>
                        <Icon name="check" size={14} /> {t("on the site")}
                        {c.new_classes ? ` · ${t("new class")}` : ""}
                      </>
                    ) : (
                      t("not on the site")
                    )}
                  </span>
                </label>
              ))}
            </div>
          )}
          {classes?.left_out ? (
            <p className="muted small">{t("{n} classes are not shown: they belong to an older cohort or their name has no cohort number.", { n: classes.left_out })}</p>
          ) : null}
          <p className="muted small">{t("All classes of a cohort (one per course) become one cohort on the site. Students are merged across classes, and students who join a class later are picked up automatically.")}</p>
        </Card>
      ) : null}

      {live ? (
        <Card title={t("Linked cohorts")}>
          {!cohorts ? (
            <Loading />
          ) : !linked.length ? (
            <p className="muted">{t("No cohort comes from Classroom yet: choose cohorts above and bring them onto the site.")}</p>
          ) : (
            <div className="linked-list">
              {linked.map((c) => {
                const s = c.classroom.summary || {};
                return (
                  <div key={c.number} className="linked-row">
                    <b>
                      {c.name}
                      {c.status === "running" ? <span className="muted"> · {t("running")}</span> : null}
                    </b>
                    <span className="chips">
                      {c.classroom.classes.map((x) => (
                        <span key={x.id} className="chip" title={x.name}>
                          {x.course || x.name}
                        </span>
                      ))}
                    </span>
                    <span className="sync-info">
                      {s.error ? (
                        <span className="status bad">{t("Error: {message}", { message: s.error })}</span>
                      ) : c.classroom.synced_at ? (
                        t("{when} · {students} students · {assignments} assignments · {submitted} submitted · {graded} graded", {
                          when: stamp(c.classroom.synced_at),
                          ...s,
                        })
                      ) : (
                        t("not synced yet")
                      )}
                      {s.unmatched?.length ? (
                        <details>
                          <summary>{t("{n} students not found on the site (email does not match)", { n: s.unmatched.length })}</summary>
                          {s.unmatched.map((u) => (
                            <div key={u.email}>
                              {u.name} · {u.email}
                            </div>
                          ))}
                          <button type="button" className="button small" onClick={() => syncOne(c.number, true)} disabled={!!busy}>
                            {t("Add these students to the site")}
                          </button>
                        </details>
                      ) : null}
                    </span>
                    <button type="button" className="button small" onClick={() => syncOne(c.number)} disabled={!!busy}>
                      <Icon name="refresh" size={14} /> {busy === `sync-${c.number}` ? t("Updating…") : t("Update from Classroom")}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      ) : null}
    </>
  );
}
