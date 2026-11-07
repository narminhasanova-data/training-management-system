import { t } from "../i18n/index.js";

const STATUS = { running: "running", upcoming: "upcoming", finished: "finished" };

export function CohortSelect({ cohorts, value, onChange }) {
  return (
    <select className="select" aria-label={t("Cohort")} value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
      {cohorts.map((c) => (
        <option key={c.number} value={c.number}>
          {c.name}
          {c.status !== "finished" ? ` · ${t(STATUS[c.status])}` : ""}
        </option>
      ))}
    </select>
  );
}

export function WeekSelect({ weeks, value, onChange, allLabel }) {
  return (
    <select
      className="select"
      aria-label={t("Week")}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
    >
      {allLabel ? <option value="">{allLabel}</option> : null}
      {weeks.map((w) => (
        <option key={w} value={w}>
          {t("Week {n}", { n: w })}
        </option>
      ))}
    </select>
  );
}

export const range = (n) => Array.from({ length: n }, (_, i) => i + 1);
