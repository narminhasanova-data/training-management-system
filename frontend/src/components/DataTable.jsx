import { useMemo, useState } from "react";
import { t } from "../i18n/index.js";

// columns: [{ key, label, render?(row), className? }]; rows: objects. Search over `searchKeys`, paged.
export default function DataTable({ columns, rows, query = "", searchKeys = [], pageSize = 50, rowKey = (r) => r.id, rowClass }) {
  const [page, setPage] = useState(0);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => searchKeys.some((k) => String(r[k] ?? "").toLowerCase().includes(q)));
  }, [rows, query, searchKeys]);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const current = Math.min(page, pages - 1);
  const visible = filtered.slice(current * pageSize, (current + 1) * pageSize);
  return (
    <div className="table-wrap">
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} className={c.className}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={rowKey(row)} className={rowClass ? rowClass(row) : undefined}>
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render ? c.render(row) : row[c.key]}
                  </td>
                ))}
              </tr>
            ))}
            {!visible.length ? (
              <tr>
                <td colSpan={columns.length} className="muted center">
                  {t("Nothing matches the search.")}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {pages > 1 ? (
        <div className="pager">
          <span className="muted">{t("{from}–{to} of {total}", { from: current * pageSize + 1, to: current * pageSize + visible.length, total: filtered.length })}</span>
          <button type="button" className="button small" disabled={current === 0} onClick={() => setPage(current - 1)}>
            {t("Previous")}
          </button>
          <button type="button" className="button small" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}>
            {t("Next")}
          </button>
        </div>
      ) : null}
    </div>
  );
}
