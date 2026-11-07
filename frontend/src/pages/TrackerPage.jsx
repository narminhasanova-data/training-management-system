import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import { defaultCohort, useCohorts } from "../api/hooks.js";
import DataTable from "../components/DataTable.jsx";
import Icon from "../components/Icon.jsx";
import { CohortSelect, WeekSelect } from "../components/Pickers.jsx";
import { useToast } from "../components/Toast.jsx";
import { Alert, Empty, Loading, PageHeader, stamp } from "../components/ui.jsx";
import { t } from "../i18n/index.js";

const tone = (pct) => (pct >= 90 ? "top" : pct < 50 ? "low" : "");

function Cell({ cell }) {
  if (!cell || cell.status === "missing") return <span className="muted">—</span>;
  const body =
    cell.status === "graded" ? (
      <span className={`grade ${tone(cell.percent)}`}>{Number(cell.points.toFixed(1))}</span>
    ) : (
      <span className="status ok" title={t("Submitted, waiting for a grade")}>
        <Icon name="check" size={14} />
      </span>
    );
  return (
    <span className="cell">
      {cell.link ? (
        <a href={cell.link} target="_blank" rel="noreferrer" title={t("Open the work")}>
          {body}
        </a>
      ) : (
        body
      )}
      {cell.late ? <small className="late">{t("late")}</small> : null}
    </span>
  );
}

export default function TrackerPage() {
  const [cohorts, cohortsError] = useCohorts();
  const [cohort, setCohort] = useState(null);
  const [week, setWeek] = useState(null);
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const toast = useToast();

  useEffect(() => {
    if (cohort || !cohorts) return;
    const first = defaultCohort(cohorts);
    if (first) {
      setCohort(first.number);
      setWeek(first.current_week);
    }
  }, [cohorts, cohort]);
  const load = useCallback(() => {
    if (!cohort) return;
    setError("");
    api(`cohorts/${cohort}/gradebook/`, { query: { week } })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [cohort, week]);
  useEffect(load, [load]);

  const sync = async () => {
    setBusy(true);
    setError("");
    try {
      await api(`cohorts/${cohort}/classroom/sync/`, { method: "POST", body: {} });
      load();
      toast(t("Updated from Classroom"));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (cohortsError) return <Alert>{cohortsError}</Alert>;
  if (!cohorts) return <Loading />;
  if (!cohorts.length) return <Empty>{t("There are no cohorts yet.")}</Empty>;
  const meta = data?.cohort;
  const weeks = [...new Set([...(data?.weeks || []), ...(week ? [week] : [])])].sort((a, b) => a - b);
  const columns = data
    ? [
        { key: "code", label: t("ID"), className: "strong nowrap" },
        {
          key: "name",
          label: t("Student"),
          className: "strong",
          render: (r) => (
            <span className="who">
              {r.name}
              {r.dropped ? <small className="muted"> · {t("left")}</small> : null}
              {r.email ? (
                <a href={`mailto:${r.email}`} className="who-mail">
                  {r.email}
                </a>
              ) : null}
            </span>
          ),
        },
        ...data.assignments.map((a) => ({
          key: `a${a.id}`,
          className: "center",
          label: (
            <span className="assignment-head" title={`${a.title} · ${t("max. {n}", { n: a.max_points })}`}>
              {a.link ? (
                <a href={a.link} target="_blank" rel="noreferrer">
                  {a.title}
                </a>
              ) : (
                a.title
              )}
              <small>
                {t("W{n}", { n: a.week })}
                {a.course ? ` · ${a.course}` : ""} · {a.max_points}
              </small>
            </span>
          ),
          render: (r) => <Cell cell={r.cells[a.id]} />,
        })),
        { key: "done", label: t("Handed in"), className: "center strong", render: (r) => (r.due ? `${r.done}/${r.due}` : "—") },
        {
          key: "average",
          label: t("Average"),
          className: "center strong",
          render: (r) => (r.average == null ? "—" : <span className={`grade ${tone(r.average)}`}>{r.average}%</span>),
        },
      ]
    : [];

  return (
    <>
      <PageHeader title={t("Tracker: homework and grades")} subtitle={t("Submissions and grades from Classroom and from the site. A Classroom grade appears here once the work is returned.")}>
        <CohortSelect
          cohorts={cohorts}
          value={cohort}
          onChange={(n) => {
            setCohort(n);
            setWeek(null);
            setData(null);
          }}
        />
        <WeekSelect weeks={weeks} value={week} allLabel={t("All weeks")} onChange={setWeek} />
        {meta?.classroom_linked ? (
          <button type="button" className="button" onClick={sync} disabled={busy}>
            <Icon name="refresh" size={15} /> {busy ? t("Updating…") : t("Update from Classroom")}
          </button>
        ) : null}
      </PageHeader>
      {error ? <Alert>{error}</Alert> : null}
      <div className="toolbar">
        <label className="search">
          <Icon name="search" size={16} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("Search by name, ID or email")} aria-label={t("Search")} />
        </label>
        <span className="legend">
          <span className="grade top">90+</span> {t("excellent")} · <span className="grade low">&lt;50</span> {t("needs attention")} ·{" "}
          <Icon name="check" size={13} /> {t("submitted, not graded")} · — {t("not submitted")}
        </span>
        <span className="muted small">
          {meta?.classroom_linked
            ? meta.classroom_synced_at
              ? t("Classroom: {when}", { when: stamp(meta.classroom_synced_at) })
              : t("Classroom: not synced yet")
            : t("Not linked to Classroom")}
        </span>
      </div>
      {!data ? (
        <Loading />
      ) : !data.assignments.length ? (
        <Empty>{t("No assignments for this selection.")}</Empty>
      ) : (
        <DataTable
          columns={columns}
          rows={data.people}
          query={query}
          searchKeys={["code", "name", "email"]}
          rowClass={(r) => (r.dropped ? "dimmed" : undefined)}
        />
      )}
    </>
  );
}
