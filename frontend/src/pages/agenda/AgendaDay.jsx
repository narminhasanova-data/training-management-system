import Icon from "../../components/Icon.jsx";
import { t } from "../../i18n/index.js";

export const PALETTE = ["indigo", "amber", "sky", "rose", "lime"];
const TRACK_LABELS = ["Morning course", "Afternoon course"];

function Swatches({ value, onChange, label }) {
  return (
    <span className="swatches" role="radiogroup" aria-label={label}>
      {PALETTE.map((color) => (
        <button
          key={color}
          type="button"
          role="radio"
          aria-checked={value === color}
          aria-label={t(color)}
          className={`swatch c-${color} ${value === color ? "on" : ""}`}
          onClick={() => onChange(color)}
        />
      ))}
    </span>
  );
}

// One day of an agenda. Teaching days have a fixed slot template with a morning and an afternoon
// course; free days (exams, career day, the week's extra section) have typed-in times and rows.
export default function AgendaDay({ day, index, courses, edit }) {
  const set = (change) => edit((days) => change(days[index]));
  const label = day.free ? t("Day {n}", { n: index + 1 }) : t("Class day {n}", { n: index + 1 });
  return (
    <section className={`agenda-day ${day.free ? "free" : ""}`} aria-label={label}>
      {"heading" in day ? (
        <input
          className="agenda-heading"
          value={day.heading}
          placeholder={t("Section title (optional), e.g. Week 7 preview")}
          aria-label={t("Section title")}
          onChange={(e) => set((d) => (d.heading = e.target.value))}
        />
      ) : null}
      <div className="agenda-day-head">
        <label className="field inline">
          <span>{label}</span>
          <input type="date" value={day.date} onChange={(e) => set((d) => (d.date = e.target.value))} />
        </label>
        {day.free ? (
          <label className="field inline">
            <span>{t("Colour")}</span>
            <Swatches value={day.tracks[0]?.color} label={t("Colour")} onChange={(c) => set((d) => (d.tracks[0].color = c))} />
          </label>
        ) : (
          day.tracks.map((track, ti) => (
            <div key={ti} className="field inline track-field">
              <span>{t(TRACK_LABELS[ti] || "Course")}</span>
              <select value={track.course} onChange={(e) => set((d) => (d.tracks[ti].course = e.target.value))} aria-label={t(TRACK_LABELS[ti] || "Course")}>
                <option value="">{t("— choose a course —")}</option>
                {courses.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                {track.course && !courses.includes(track.course) ? <option value={track.course}>{track.course}</option> : null}
              </select>
              <Swatches value={track.color} label={t("Colour")} onChange={(c) => set((d) => (d.tracks[ti].color = c))} />
            </div>
          ))
        )}
      </div>
      <div className="agenda-rows">
        {day.rows.map((row, ri) => {
          const track = row.track != null ? day.tracks[row.track] : null;
          const pause = !day.free && row.track == null;
          return (
            <div key={ri} className={`agenda-row ${pause ? "pause" : ""}`}>
              <span className={`stripe ${track ? `c-${track.color}` : ""}`} aria-hidden="true" />
              <input
                className="agenda-time"
                value={row.time}
                placeholder={t("Time")}
                aria-label={t("Time")}
                onChange={(e) => set((d) => (d.rows[ri].time = e.target.value))}
              />
              <input
                className="agenda-text"
                value={row.text}
                placeholder={pause ? "" : t("Topic or activity")}
                aria-label={t("Topic or activity at {time}", { time: row.time })}
                onChange={(e) => set((d) => (d.rows[ri].text = e.target.value))}
              />
              {!day.free && track?.course ? <span className="agenda-course">{track.course}</span> : null}
              {day.free ? (
                <button type="button" className="icon-button" aria-label={t("Remove row")} title={t("Remove row")} onClick={() => set((d) => d.rows.splice(ri, 1))}>
                  <Icon name="trash" size={16} />
                </button>
              ) : null}
            </div>
          );
        })}
        {day.free ? (
          <button
            type="button"
            className="button small ghost add-row"
            onClick={() => set((d) => d.rows.push({ time: "", text: "", track: d.tracks.length ? 0 : null }))}
          >
            <Icon name="plus" size={14} /> {t("Add row")}
          </button>
        ) : null}
      </div>
    </section>
  );
}
