import Icon from "../../components/Icon.jsx";
import { t } from "../../i18n/index.js";

// Question texts, kept identical to the server-side form (training/services/surveys.py).
export const blockLabel = (b) => `${b.course}${b.day ? ` · Day ${b.day}` : ""}${b.trainer ? ` (${b.trainer})` : ""}`;
const QUESTIONS = {
  understanding: (b, weeks) =>
    `Week ${b.week}: how well did you understand the ${blockLabel(b)} topics (course week ${b.course_week}${weeks ? ` of ${weeks}` : ""})?`,
  comment: (b) => `Anything to add about ${blockLabel(b)}? What worked, what should change?`,
  trainers: (w) => `Week ${w}: the trainer explained the topics clearly, knew the subject well and kept the class engaged.`,
  mentors: (w) => `Week ${w}: my mentor's support was helpful.`,
  materials: (w) => `Week ${w}: these materials were useful and of good quality.`,
};

export const daysOf = (course, courseWeek) =>
  course && (course.day_split === "all" || (course.day_split === "some" && course.split_weeks.includes(courseWeek))) ? [1, 2] : [];

export default function SurveyEditor({ form, survey, week, edit }) {
  const byName = Object.fromEntries(survey.courses.map((c) => [c.name, c]));
  const { understanding, agreement, not_applicable: notApplicable } = survey.scales;

  const setCourse = (i, name) =>
    edit((f) => {
      const block = f.blocks[i];
      const course = byName[name];
      block.course = name;
      block.course_week = Math.min(block.course_week || 1, course?.weeks || 1);
      const split = daysOf(course, block.course_week).length > 0;
      block.day = split ? 1 : 0;
      const next = f.blocks[i + 1];
      if (split && !(next && next.course === name && next.day === 2)) f.blocks.splice(i + 1, 0, { ...block, day: 2 });
    });
  const setCourseWeek = (i, value) =>
    edit((f) => {
      const block = f.blocks[i];
      block.course_week = value;
      if (block.day && !daysOf(byName[block.course], value).includes(block.day)) block.day = 0;
    });
  const addBlock = () =>
    edit((f) => f.blocks.push({ course: survey.courses[0]?.name || "", course_week: 1, day: 0, trainer: "", week }));
  const gridWeek = (key) => form.grid_weeks?.[key] || week;
  const setGridWeek = (key) => (value) => edit((f) => (f.grid_weeks = { ...f.grid_weeks, [key]: value }));

  return (
    <div className="form-editor">
      <section className="q-card q-head">
        <input
          className="q-title"
          value={form.title}
          aria-label={t("Survey title")}
          onChange={(e) => edit((f) => (f.title = e.target.value))}
        />
        <p className="muted">{t("Students see a short introduction here, and their own name (taken from the personal link).")}</p>
      </section>

      {form.blocks.map((block, i) => {
        const course = byName[block.course];
        const days = daysOf(course, block.course_week);
        return (
          <section key={i} className="q-card" aria-label={blockLabel(block)}>
            <div className="q-controls">
              <label>
                <span>{t("Course")}</span>
                <select value={block.course} onChange={(e) => setCourse(i, e.target.value)}>
                  {survey.courses.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                  {!course ? <option value={block.course}>{block.course}</option> : null}
                </select>
              </label>
              <label>
                <span>{t("Course week")}</span>
                <select value={block.course_week} onChange={(e) => setCourseWeek(i, Number(e.target.value))}>
                  {Array.from({ length: course?.weeks || block.course_week }, (_, k) => k + 1).map((w) => (
                    <option key={w} value={w}>
                      {w} / {course?.weeks || "?"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t("Day")}</span>
                <select value={block.day} onChange={(e) => edit((f) => (f.blocks[i].day = Number(e.target.value)))}>
                  <option value={0}>{t("Whole week")}</option>
                  {days.map((d) => (
                    <option key={d} value={d}>
                      {t("Day {n}", { n: d })}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grow">
                <span>{t("Trainer (optional)")}</span>
                <input list="known-trainers" value={block.trainer} placeholder={t("shown in brackets")} onChange={(e) => edit((f) => (f.blocks[i].trainer = e.target.value))} />
              </label>
              <label className="narrow">
                <span>{t("Cohort week")}</span>
                <input type="number" min={1} max={52} value={block.week} onChange={(e) => edit((f) => (f.blocks[i].week = Number(e.target.value) || week))} />
              </label>
            </div>
            <p className="q-text">
              {QUESTIONS.understanding(block, course?.weeks)}
              <span className="req">{t("Required")}</span>
            </p>
            <div className="q-options" aria-hidden="true">
              {understanding.map((o) => (
                <span key={o}>
                  <i className="radio" />
                  {o}
                </span>
              ))}
            </div>
            <p className="q-text sub">{QUESTIONS.comment(block)}</p>
            <div className="q-answer">{t("Long answer")}</div>
            <div className="q-foot">
              <button type="button" className="button small ghost" onClick={() => edit((f) => f.blocks.splice(i + 1, 0, { ...f.blocks[i] }))}>
                <Icon name="copy" size={15} /> {t("Duplicate")}
              </button>
              <button type="button" className="button small ghost danger" onClick={() => edit((f) => f.blocks.splice(i, 1))}>
                <Icon name="trash" size={15} /> {t("Remove")}
              </button>
            </div>
          </section>
        );
      })}
      <button type="button" className="button add-block" onClick={addBlock}>
        <Icon name="plus" size={16} /> {t("Add a course block")}
      </button>

      <datalist id="known-trainers">
        {survey.known_trainers.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
      <Grid
        title={QUESTIONS.trainers(gridWeek("trainers"))}
        what={t("Trainer")}
        listId="known-trainers"
        rows={form.trainers}
        columns={agreement}
        week={gridWeek("trainers")}
        onWeek={setGridWeek("trainers")}
        onChange={(change) => edit((f) => change(f.trainers))}
      />
      <Grid
        title={QUESTIONS.mentors(gridWeek("mentors"))}
        what={t("Mentor")}
        listId="known-mentors"
        suggestions={survey.known_mentors}
        rows={form.mentors}
        columns={[...agreement, notApplicable]}
        week={gridWeek("mentors")}
        onWeek={setGridWeek("mentors")}
        onChange={(change) => edit((f) => change(f.mentors))}
      />
      <Grid
        title={QUESTIONS.materials(gridWeek("materials"))}
        what={t("Material")}
        listId="known-materials"
        suggestions={survey.default_materials}
        rows={form.materials}
        columns={agreement}
        week={gridWeek("materials")}
        onWeek={setGridWeek("materials")}
        onChange={(change) => edit((f) => change(f.materials))}
      />
      <section className="q-card">
        <p className="q-text">Anything else you would like the training team to know?</p>
        <div className="q-answer">{t("Long answer")}</div>
      </section>
    </div>
  );
}

// A rating grid as students will see it; the rows (trainers, mentors, materials) are typed in place.
function Grid({ title, what, listId, suggestions, rows, columns, week, onWeek, onChange }) {
  return (
    <section className="q-card">
      <div className="q-controls">
        <label className="narrow">
          <span>{t("Cohort week")}</span>
          <input type="number" min={1} max={52} value={week} onChange={(e) => onWeek(Number(e.target.value) || 1)} />
        </label>
      </div>
      <p className="q-text">
        {title}
        <span className="req">{t("Required")}</span>
      </p>
      {suggestions ? (
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      ) : null}
      <div className="q-grid-scroll">
        <table className="q-grid" style={{ "--cols": columns.length }}>
          <thead>
            <tr>
              <th />
              {columns.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td>
                  <input
                    list={listId}
                    value={row}
                    aria-label={`${what} ${i + 1}`}
                    placeholder={t("{what} name", { what })}
                    onChange={(e) => onChange((list) => (list[i] = e.target.value))}
                  />
                </td>
                {columns.map((c) => (
                  <td key={c} aria-hidden="true">
                    <i className="radio" />
                  </td>
                ))}
                <td>
                  <button type="button" className="icon-button" aria-label={t("Remove {what}", { what })} onClick={() => onChange((list) => list.splice(i, 1))}>
                    <Icon name="x" size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length ? <p className="muted small">{t("Empty: this question will not appear in the survey.")}</p> : null}
      <button type="button" className="button small ghost" onClick={() => onChange((list) => list.push(""))}>
        <Icon name="plus" size={14} /> {t("Add {what}", { what: what.toLowerCase() })}
      </button>
    </section>
  );
}
