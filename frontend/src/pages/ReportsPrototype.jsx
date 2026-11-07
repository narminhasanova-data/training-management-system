import Icon from "../components/Icon.jsx";
import { useToast } from "../components/Toast.jsx";
import { PageHeader, PrototypeBanner } from "../components/ui.jsx";
import { t } from "../i18n/index.js";

// Prototype: the report catalogue as designed; the export buttons are not implemented.
const REPORTS = [
  ["Attendance by week", "Who attended each lesson, with weekly rates", "users"],
  ["Homework completion", "Handed in, late and missing work per student", "file"],
  ["Grades overview", "Average grade per student and course", "reports"],
  ["Weekly survey summary", "Understanding and satisfaction scores per week", "survey"],
  ["Trainer and mentor feedback", "Ratings and comments per person", "check"],
  ["Cohort comparison", "Headline numbers of every cohort side by side", "tracker"],
];

export default function ReportsPrototype() {
  const toast = useToast();
  const notReady = (name, format) => toast(t("Prototype: “{name}” ({format}) export is not implemented yet.", { name: t(name), format }), "neutral");
  return (
    <>
      <PageHeader title={t("Reports")} subtitle={t("Reports built from the tracker and checklist data.")} />
      <PrototypeBanner />
      <div className="report-grid">
        {REPORTS.map(([name, description, icon]) => (
          <div key={name} className="card report-card">
            <span className="kpi-icon">
              <Icon name={icon} />
            </span>
            <div>
              <b>{t(name)}</b>
              <p className="muted small">{t(description)}</p>
              <div className="report-buttons">
                <button type="button" className="button small" onClick={() => notReady(name, "Excel")}>
                  <Icon name="download" size={14} /> Excel
                </button>
                <button type="button" className="button small" onClick={() => notReady(name, "PDF")}>
                  <Icon name="file" size={14} /> PDF
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
