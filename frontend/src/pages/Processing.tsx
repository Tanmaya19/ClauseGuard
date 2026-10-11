import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { STAGE_COPY, api, type AnalysisStatus, type ContractStatus } from "../api/client";

const STAGES: ContractStatus[] = [
  "uploaded",
  "extracting",
  "segmenting",
  "classifying",
  "scoring",
];

const POLL_MS = 1500;

export default function Processing() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const timer = useRef<number>();

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function poll() {
      try {
        const next = await api.status(id!);
        if (cancelled) return;
        setStatus(next);

        if (next.status === "complete") {
          navigate(`/contracts/${id}/report`, { replace: true });
          return;
        }
        if (next.status === "failed") return; // stop polling; show the reason

        timer.current = window.setTimeout(poll, POLL_MS);
      } catch (caught) {
        if (!cancelled) setError((caught as Error).message);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer.current);
    };
  }, [id, navigate]);

  if (error) {
    return <Problem title="Could not check progress" body={error} />;
  }

  if (status?.status === "failed") {
    return (
      <Problem
        title="We could not analyse this contract"
        body={status.error_message ?? "Something went wrong while reading the file."}
      />
    );
  }

  const current = status?.status ?? "uploaded";
  const currentIndex = STAGES.indexOf(current);

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-xl font-semibold tracking-tight text-slate-900">
        Analysing your contract
      </h1>
      <p className="mt-1 text-sm text-slate-600">
        This usually takes a few seconds. You can leave this page open.
      </p>

      <div className="cg-card mt-6 p-6">
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-slate-900 transition-all duration-500"
            style={{ width: `${status?.progress ?? 5}%` }}
          />
        </div>

        <ol className="mt-6 space-y-3">
          {STAGES.map((stage, index) => {
            const done = currentIndex > index;
            const active = currentIndex === index;
            return (
              <li key={stage} className="flex items-center gap-3 text-sm">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] ${
                    done
                      ? "border-safe-fg bg-safe-fg text-white"
                      : active
                        ? "border-slate-900 text-slate-900"
                        : "border-slate-300 text-slate-400"
                  }`}
                >
                  {done ? "✓" : index + 1}
                </span>
                <span className={active ? "font-medium text-slate-900" : "text-slate-500"}>
                  {STAGE_COPY[stage]}
                </span>
              </li>
            );
          })}
        </ol>

        {status?.status_detail && (
          <p className="mt-4 text-xs text-slate-500">{status.status_detail}</p>
        )}
      </div>
    </div>
  );
}

function Problem({ title, body }: { title: string; body: string }) {
  return (
    <div className="mx-auto max-w-xl">
      <div className="cg-card border-danger-border p-6">
        <h1 className="text-lg font-semibold text-danger-fg">{title}</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">{body}</p>
        <div className="mt-5 flex gap-3">
          <Link to="/" className="cg-btn-primary">
            Try another file
          </Link>
          <Link to="/dashboard" className="cg-btn-secondary">
            My contracts
          </Link>
        </div>
      </div>
    </div>
  );
}
