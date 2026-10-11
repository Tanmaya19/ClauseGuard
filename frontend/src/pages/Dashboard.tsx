import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ContractRow, type Dashboard as DashboardData } from "../api/client";

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [rows, setRows] = useState<ContractRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.dashboard(), api.history()])
      .then(([overview, history]) => {
        setData(overview);
        setRows(history);
      })
      .catch((caught) => setError((caught as Error).message));
  }, []);

  useEffect(load, [load]);

  async function remove(id: string) {
    if (!window.confirm("Delete this contract and its report? This cannot be undone.")) {
      return;
    }
    await api.remove(id);
    load();
  }

  if (error) {
    return <p className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger-fg">{error}</p>;
  }
  if (!data) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">My contracts</h1>

      {/* --- Totals ---------------------------------------------------- */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Contracts reviewed" value={data.total_contracts} />
        <Stat label="Clauses analysed" value={data.total_clauses} />
        <Stat
          label="Need attention"
          value={data.risk_totals.high_risk ?? 0}
          tone="text-danger-fg"
        />
        <Stat
          label="Worth a look"
          value={data.risk_totals.caution ?? 0}
          tone="text-caution-fg"
        />
      </div>

      {/* --- Reviewed over time (SRS 2.2) ----------------------------- */}
      {data.reviewed_over_time.length > 1 && (
        <section className="cg-card mt-6 p-5">
          <h2 className="text-sm font-semibold text-slate-900">Contracts reviewed over time</h2>
          <ActivityChart points={data.reviewed_over_time} />
        </section>
      )}

      {/* --- History (REQ-6.3) ---------------------------------------- */}
      <section className="cg-card mt-6 overflow-hidden">
        {rows.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-600">You have not analysed a contract yet.</p>
            <Link to="/" className="cg-btn-primary mt-4">
              Analyse a contract
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {rows.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-900">{row.filename}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {new Date(row.uploaded_at).toLocaleDateString()}
                    {row.clause_count != null && ` · ${row.clause_count} clauses`}
                  </p>
                </div>

                {row.status === "complete" ? (
                  <div className="flex items-center gap-2 text-xs">
                    {(row.high_risk_count ?? 0) > 0 && (
                      <span className="rounded-full bg-danger-bg px-2 py-0.5 font-medium text-danger-fg">
                        {row.high_risk_count} need attention
                      </span>
                    )}
                    {(row.caution_count ?? 0) > 0 && (
                      <span className="rounded-full bg-caution-bg px-2 py-0.5 font-medium text-caution-fg">
                        {row.caution_count} to review
                      </span>
                    )}
                  </div>
                ) : (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      row.status === "failed"
                        ? "bg-danger-bg text-danger-fg"
                        : "bg-muted-bg text-muted-fg"
                    }`}
                  >
                    {row.status === "failed" ? "Could not be read" : "In progress"}
                  </span>
                )}

                <div className="flex gap-2">
                  {/* REQ-6.4: re-open a past report without re-uploading. */}
                  {row.status === "complete" && (
                    <Link to={`/contracts/${row.id}/report`} className="cg-btn-secondary">
                      Open
                    </Link>
                  )}
                  <button
                    onClick={() => void remove(row.id)}
                    className="cg-btn text-slate-500 hover:text-danger-fg"
                    aria-label={`Delete ${row.filename}`}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="cg-card p-4">
      <p className={`text-2xl font-semibold ${tone ?? "text-slate-900"}`}>{value}</p>
      <p className="mt-0.5 text-sm text-slate-600">{label}</p>
    </div>
  );
}

/**
 * Minimal inline bar chart. Deliberately not a charting library: a dozen bars
 * is not worth 150 kB of bundle, and this keeps the build dependency-free.
 */
function ActivityChart({ points }: { points: { date: string; count: number }[] }) {
  const recent = points.slice(-14);
  const max = Math.max(...recent.map((p) => p.count), 1);

  return (
    <div className="mt-4 flex h-28 items-end gap-1.5">
      {recent.map((point) => (
        <div key={point.date} className="group flex flex-1 flex-col items-center gap-1">
          <div
            className="w-full rounded-t bg-slate-300 transition group-hover:bg-slate-900"
            style={{ height: `${Math.max((point.count / max) * 100, 6)}%` }}
            title={`${point.date}: ${point.count}`}
          />
          <span className="text-[10px] text-slate-400">
            {new Date(point.date).getDate()}
          </span>
        </div>
      ))}
    </div>
  );
}
