import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import Icon from "../../components/Icon.jsx";
import { Alert, Card, Loading } from "../../components/ui.jsx";
import { t } from "../../i18n/index.js";

const fromServer = (courses) => courses.map((c) => ({ ...c, weeksText: c.split_weeks.join(", ") }));

// The catalogue of courses: agenda modules and survey blocks, with Day 1 / Day 2 weeks.
export default function CourseCatalog({ onSaved }) {
  const [rows, setRows] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api("courses/").then((d) => setRows(fromServer(d.courses))).catch((e) => setError(e.message));
  }, []);
  const edit = (i, patch) => {
    setRows((list) => list.map((r, j) => (j === i ? { ...r, ...patch } : r)));
    setDirty(true);
  };
  const save = async () => {
    setBusy(true);
    setError("");
    const courses = rows.map((r) => ({
      ...(r.id ? { id: r.id } : {}),
      name: r.name.trim(),
      weeks: Number(r.weeks) || 1,
      day_split: r.day_split,
      split_weeks: r.day_split === "some" ? r.weeksText.split(/[^0-9]+/).filter(Boolean).map(Number) : [],
    }));
    try {
      const d = await api("courses/", { method: "PUT", body: { courses } });
      setRows(fromServer(d.courses));
      setDirty(false);
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  if (!rows) return error ? <Alert>{error}</Alert> : <Loading />;
  return (
    <Card
      title={t("Courses")}
      aside={
        <button type="button" className="button primary" onClick={save} disabled={busy || !dirty}>
          {busy ? t("Saving…") : t("Save")}
        </button>
      }
    >
      <p className="muted">{t("Agendas use these as modules and surveys as course blocks: how many weeks each course lasts and in which weeks it is taught as Day 1 / Day 2.")}</p>
      {error ? <Alert>{error}</Alert> : null}
      <div className="catalogue">
        <div className="catalogue-row head" aria-hidden="true">
          <span>{t("Course")}</span>
          <span>{t("Weeks")}</span>
          <span>{t("Day 1 / Day 2")}</span>
          <span>{t("In which weeks")}</span>
          <span />
        </div>
        {rows.map((row, i) => (
          <div key={row.id || `new-${i}`} className="catalogue-row">
            <input aria-label={t("Course name")} value={row.name} onChange={(e) => edit(i, { name: e.target.value })} />
            <input aria-label={t("Number of weeks")} type="number" min={1} max={52} value={row.weeks} onChange={(e) => edit(i, { weeks: e.target.value })} />
            <select aria-label={t("Day 1 / Day 2")} value={row.day_split} onChange={(e) => edit(i, { day_split: e.target.value })}>
              <option value="none">{t("No (one session a week)")}</option>
              <option value="all">{t("Every week")}</option>
              <option value="some">{t("Selected weeks")}</option>
            </select>
            {row.day_split === "some" ? (
              <input aria-label={t("In which weeks")} value={row.weeksText} placeholder={t("e.g. 3, 4")} onChange={(e) => edit(i, { weeksText: e.target.value })} />
            ) : (
              <span className="muted">{row.day_split === "all" ? t("all weeks") : "—"}</span>
            )}
            <button
              type="button"
              className="icon-button"
              aria-label={t("Remove course")}
              onClick={() => {
                setRows((list) => list.filter((_, j) => j !== i));
                setDirty(true);
              }}
            >
              <Icon name="x" size={15} />
            </button>
          </div>
        ))}
        <button
          type="button"
          className="button small ghost"
          onClick={() => {
            setRows((list) => [...list, { name: "", weeks: 4, day_split: "none", split_weeks: [], weeksText: "" }]);
            setDirty(true);
          }}
        >
          <Icon name="plus" size={14} /> {t("Add a course")}
        </button>
      </div>
    </Card>
  );
}
