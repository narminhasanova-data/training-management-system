import { Badge, Card, Empty, Kpi, scoreTone, stamp } from "../../components/ui.jsx";
import Icon from "../../components/Icon.jsx";
import { t } from "../../i18n/index.js";

function Distribution({ title, first, columns, rows }) {
  if (!rows.length) return null;
  return (
    <Card title={title} aside={<span className="muted">{t("average on a 1–5 scale")}</span>}>
      <div className="table-scroll">
        <table className="table compact">
          <thead>
            <tr>
              <th>{first}</th>
              {columns.map((c) => (
                <th key={c} className="center">
                  {c}
                </th>
              ))}
              <th className="center">{t("Average")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const total = row.counts.reduce((a, b) => a + b, 0);
              const top = Math.max(...row.counts);
              return (
                <tr key={row.label}>
                  <td className="strong">{row.label}</td>
                  {row.counts.map((n, i) => (
                    <td key={i} className={`center ${n && n === top ? "top-cell" : ""}`}>
                      {n ? (
                        <>
                          {n} <small className="muted">{Math.round((100 * n) / total)}%</small>
                        </>
                      ) : (
                        <span className="muted">0</span>
                      )}
                    </td>
                  ))}
                  <td className="center">{row.average == null ? <span className="muted">—</span> : <Badge tone={scoreTone(row.average)}>{row.average.toFixed(2)}</Badge>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows.some((r) => r.comments?.length) ? (
        <div className="comments">
          {rows
            .filter((r) => r.comments?.length)
            .map((r) => (
              <details key={r.label}>
                <summary>{r.comments.length === 1 ? t("{label}: 1 comment", { label: r.label }) : t("{label}: {n} comments", { label: r.label, n: r.comments.length })}</summary>
                <ul>
                  {r.comments.map((c, i) => (
                    <li key={i}>
                      <b>{c.name}:</b> {c.text}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
        </div>
      ) : null}
    </Card>
  );
}

export default function SurveyResults({ results, scales, canRemind, onRemind }) {
  if (!results) return <Empty>{t("This week's survey has not been saved or sent yet.")}</Empty>;
  const waiting = results.people.filter((p) => !p.answered_at);
  const { understanding, agreement, not_applicable: notApplicable } = scales;
  return (
    <div className="stack">
      <div className="kpis">
        <Kpi icon="send" label={t("Links sent")} value={results.invited} />
        <Kpi
          icon="check"
          tone="success"
          label={t("Answered")}
          value={`${results.answered}${results.invited ? ` · ${Math.round((100 * results.answered) / results.invited)}%` : ""}`}
        />
        <Kpi icon="clock" tone="warning" label={t("Waiting for an answer")} value={waiting.length} />
      </div>
      {!results.answered ? <Empty>{t("No answers yet.")}</Empty> : null}
      <Distribution title={t("Courses: how well students understood the topics")} first={t("Course")} columns={understanding} rows={results.blocks} />
      <Distribution title={t("Trainers")} first={t("Name")} columns={agreement} rows={results.trainers} />
      <Distribution title={t("Mentors")} first={t("Name")} columns={[...agreement, notApplicable]} rows={results.mentors} />
      <Distribution title={t("Materials")} first={t("Material")} columns={agreement} rows={results.materials} />
      {results.notes.length ? (
        <Card title={t("Other comments")}>
          <ul className="notes">
            {results.notes.map((n, i) => (
              <li key={i}>
                <b>{n.name}:</b> {n.text}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
      {results.people.length ? (
        <Card
          title={t("Who has answered")}
          aside={
            waiting.length && canRemind ? (
              <button type="button" className="button small" onClick={() => onRemind(waiting.map((p) => p.id))}>
                {t("Remind those who have not answered ({n})", { n: waiting.length })}
              </button>
            ) : null
          }
        >
          <div className="table-scroll">
            <table className="table compact">
              <thead>
                <tr>
                  <th>{t("Student")}</th>
                  <th>{t("Link sent")}</th>
                  <th>{t("Answer")}</th>
                </tr>
              </thead>
              <tbody>
                {results.people.map((p) => (
                  <tr key={p.id}>
                    <td className="strong">{p.name}</td>
                    <td>{p.sent_at ? `${stamp(p.sent_at)} · ${p.channels.replace("whatsapp", "WhatsApp").replace(",", ", ")}` : "—"}</td>
                    <td>
                      {p.answered_at ? (
                        <span className="status ok">
                          <Icon name="check" size={14} /> {stamp(p.answered_at)}
                        </span>
                      ) : (
                        <span className="muted">{t("waiting")}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
