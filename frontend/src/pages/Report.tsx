import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  RISK_META,
  api,
  type Clause,
  type Report,
  type RiskLevel,
} from "../api/client";

const ORDER: RiskLevel[] = ["high_risk", "caution", "safe", "unassessable"];

export default function ReportView() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<RiskLevel | "all">("all");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .report(id)
      .then(setReport)
      .catch((caught) => setError((caught as Error).message));
  }, [id]);

  const visible = useMemo(() => {
    if (!report) return [];
    return filter === "all"
      ? report.clauses
      : report.clauses.filter((clause) => clause.risk === filter);
  }, [report, filter]);

  if (error) {
    return (
      <div className="cg-card border-danger-border p-6">
        <p className="text-sm text-danger-fg">{error}</p>
        <Link to="/dashboard" className="cg-btn-secondary mt-4">
          My contracts
        </Link>
      </div>
    );
  }

  if (!report) {
    return <p className="text-sm text-slate-500">Loading the report…</p>;
  }

  const counts = report.summary.risk_counts;

  return (
    <div>
      {/* --- Header ---------------------------------------------------- */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            {report.filename}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {report.summary.clause_count} clauses · checked against rubric v
            {report.rubric_version}
          </p>
        </div>

        <button
          className="cg-btn-primary"
          disabled={downloading}
          onClick={async () => {
            setDownloading(true);
            try {
              await api.downloadPdf(report.contract_id, report.filename);
            } finally {
              setDownloading(false);
            }
          }}
        >
          {downloading ? "Preparing…" : "Download PDF"}
        </button>
      </div>

      {/* --- Summary (REQ-5.4) ----------------------------------------- */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {ORDER.map((level) => {
          const count = counts[level] ?? 0;
          if (level === "unassessable" && count === 0) return null;
          const meta = RISK_META[level];
          return (
            <button
              key={level}
              onClick={() => setFilter(filter === level ? "all" : level)}
              className={`rounded-xl border p-4 text-left transition ${meta.className} ${
                filter === level ? "ring-2 ring-slate-900 ring-offset-1" : ""
              }`}
            >
              <p className="text-2xl font-semibold">{count}</p>
              <p className="text-sm font-medium">{meta.label}</p>
              <p className="mt-1 text-xs opacity-80">{meta.blurb}</p>
            </button>
          );
        })}
      </div>

      {filter !== "all" && (
        <button
          onClick={() => setFilter("all")}
          className="mt-3 text-sm text-slate-600 underline hover:text-slate-900"
        >
          Show all {report.summary.clause_count} clauses
        </button>
      )}

      {/* --- Contract-level gaps --------------------------------------- */}
      {report.summary.contract_findings.length > 0 && (
        <section className="cg-card mt-6 border-caution-border bg-caution-bg/40 p-5">
          <h2 className="text-sm font-semibold text-slate-900">
            Missing from this contract
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            Protections we expected to find and could not.
          </p>
          <ul className="mt-3 space-y-2">
            {report.summary.contract_findings.map((finding) => (
              <li key={finding.rule_id} className="text-sm leading-relaxed text-slate-700">
                • {finding.explanation}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* --- Clause list (REQ-5.1, REQ-5.2) --------------------------- */}
      <div className="mt-8 space-y-3">
        {visible.map((clause) => (
          <ClauseCard key={clause.id} clause={clause} />
        ))}
      </div>

      <p className="mt-8 text-xs text-slate-400">
        Rubric v{report.rubric_version} · model {report.model_version} · generated{" "}
        {new Date(report.generated_at).toLocaleString()}
      </p>
    </div>
  );
}

function ClauseCard({ clause }: { clause: Clause }) {
  // High-risk clauses start expanded: the point of the product is to draw the
  // eye to what matters, not to make the user click to find it.
  const [open, setOpen] = useState(clause.risk === "high_risk");
  const meta = RISK_META[clause.risk];

  return (
    <article className="cg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 p-4 text-left hover:bg-slate-50"
      >
        <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${meta.dot}`} />

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900">
              {clause.heading ?? `Clause ${clause.ordinal + 1}`}
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${meta.className}`}
            >
              {meta.label}
            </span>
          </span>

          <span className="mt-1 block text-xs text-slate-500">
            {clause.predictions.length > 0
              ? clause.predictions.map((p) => p.display).join(", ")
              : "Uncategorized"}
          </span>

          {!open && (
            <span className="mt-2 block line-clamp-2 text-sm text-slate-600">
              {clause.text}
            </span>
          )}
        </span>

        <span className="mt-1 shrink-0 text-xs text-slate-400">{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3">
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
            {clause.text}
          </p>

          {clause.findings.length > 0 && (
            <div className={`mt-4 rounded-lg border p-3 ${meta.className}`}>
              <p className="text-xs font-semibold uppercase tracking-wide">
                Why this is flagged
              </p>
              <ul className="mt-2 space-y-2">
                {clause.findings.map((finding) => (
                  <li key={finding.rule_id} className="text-sm leading-relaxed">
                    {finding.explanation}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {clause.predictions.length > 0 && (
            <p className="mt-3 text-xs text-slate-400">
              {/* SRS 5.2: never assert certainty. */}
              Confidence:{" "}
              {clause.predictions
                .map((p) => `${p.display} ${Math.round(p.confidence * 100)}%`)
                .join(" · ")}
            </p>
          )}

          {clause.needs_manual_review && (
            <p className="mt-3 rounded-lg bg-muted-bg px-3 py-2 text-xs text-muted-fg">
              We could not cleanly separate this clause from the ones around it, so read
              it in the original document as well.
            </p>
          )}
        </div>
      )}
    </article>
  );
}
