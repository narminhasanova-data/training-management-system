import { useState } from "react";
import { Kpi, PageHeader, PrototypeBanner } from "../components/ui.jsx";
import { t } from "../i18n/index.js";

// Prototype: sample rows only; ticking a session changes nothing outside this page.
const SAMPLE = [
  { id: 1, course: "SQL Foundations", session: "Lecture · CTEs and window functions", trainer: "Omar Haddad", date: "Sat 10:00", present: 16, students: 17, homework: true, done: true },
  { id: 2, course: "Python for Data", session: "Lecture · Visualisation", trainer: "Lucas Moreau", date: "Sat 13:30", present: 15, students: 17, homework: true, done: true },
  { id: 3, course: "SQL Foundations", session: "Practice · Ranking queries", trainer: "Omar Haddad", date: "Sun 10:00", present: 0, students: 17, homework: false, done: false },
  { id: 4, course: "Python for Data", session: "Practice · Exploratory analysis", trainer: "Lucas Moreau", date: "Sun 13:30", present: 0, students: 17, homework: false, done: false },
];

export default function ChecklistPrototype() {
  const [rows, setRows] = useState(SAMPLE);
  const done = rows.filter((r) => r.done).length;
  const toggle = (id) => setRows((list) => list.map((r) => (r.id === id ? { ...r, done: !r.done, homework: !r.done || r.homework } : r)));
  return (
    <>
      <PageHeader title={t("Lesson checklist")} subtitle={t("Every session of the week: held, attendance, homework given.")} />
      <PrototypeBanner />
      <div className="kpis">
        <Kpi icon="check" tone="success" label={t("Sessions held")} value={`${done} / ${rows.length}`} />
        <Kpi icon="users" label={t("Average attendance")} value="91%" />
        <Kpi icon="file" label={t("Homework given")} value={rows.filter((r) => r.homework).length} />
      </div>
      <div className="table-wrap">
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>{t("Held")}</th>
                <th>{t("Course")}</th>
                <th>{t("Session")}</th>
                <th>{t("Trainer")}</th>
                <th>{t("When")}</th>
                <th className="center">{t("Attendance")}</th>
                <th>{t("Homework")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <input type="checkbox" aria-label={t("Held")} checked={r.done} onChange={() => toggle(r.id)} />
                  </td>
                  <td className="strong">{r.course}</td>
                  <td>{r.session}</td>
                  <td>{r.trainer}</td>
                  <td className="muted">{r.date}</td>
                  <td className="center">{r.present ? `${r.present} / ${r.students}` : "—"}</td>
                  <td>{r.homework ? t("Given") : t("Not yet")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
