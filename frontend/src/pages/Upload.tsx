import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, ContractRow, MAX_UPLOAD_MB, api } from "../api/client";

const ACCEPTED = [".pdf", ".docx"];

const HIGH_RISK = [
  { name: "Limitation of Liability", desc: "Caps what you can recover if the other side damages your business." },
  { name: "Indemnification", desc: "Makes you pay their legal costs — even when you're not at fault." },
  { name: "IP Assignment", desc: "Silently transfers ownership of your work or inventions to them." },
  { name: "Unilateral Termination", desc: "Lets them walk away with 2 days' notice; you need 90." },
];

const WATCH = [
  { name: "Non-Compete / Non-Solicit", desc: "Restricts who you can work with after the contract ends." },
  { name: "Automatic Renewal", desc: "Locks you in unless you cancel on a specific date." },
  { name: "Governing Law", desc: "Forces disputes into their home city's courts, not yours." },
  { name: "Payment Terms", desc: "Late payment penalties or unusually long payment cycles." },
];

const INFO = [
  { name: "Force Majeure", desc: "Excuses performance during extraordinary events." },
  { name: "Confidentiality / NDA", desc: "Limits what you can share with third parties." },
  { name: "Warranties", desc: "Guarantees about what each party promises to deliver." },
  { name: "Dispute Resolution", desc: "How disagreements are handled — arbitration or court." },
];

export default function Upload() {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<ContractRow[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.history().then((items) => setHistory(items.slice(0, 3))).catch(() => {});
  }, []);

  async function send(file: File) {
    setError(null);

    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (!ACCEPTED.includes(extension)) {
      setError("Only PDF and Word (.docx) files can be analysed.");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`This file is larger than the ${MAX_UPLOAD_MB} MB limit.`);
      return;
    }

    setBusy(true);
    try {
      const { contract_id } = await api.upload(file);
      navigate(`/contracts/${contract_id}/processing`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Upload failed.");
      setBusy(false);
    }
  }

  function formatDate(iso: string) {
    try {
      return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
    } catch {
      return iso;
    }
  }

  return (
    <div className="space-y-8">

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="rounded-2xl bg-slate-900 px-8 py-7 text-white">
        <h1 className="text-2xl font-semibold tracking-tight">Analyse a contract</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-300">
          Upload a vendor, supply, service or NDA agreement. ClauseGuard flags the clauses that
          are commonly one-sided — so you know exactly what to push back on.
        </p>
      </div>

      {/* ── Drop zone ───────────────────────────────────────────────────── */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void send(file);
        }}
        className={`rounded-2xl border-2 border-dashed p-14 text-center transition-colors ${
          dragging
            ? "border-blue-500 bg-blue-100"
            : "border-blue-300 bg-blue-50 hover:border-blue-400 hover:bg-blue-100"
        }`}
      >
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-sm">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
            className="h-7 w-7 text-blue-600">
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>

        <p className="text-base font-semibold text-slate-900">
          {busy ? "Uploading…" : "Drag your contract here"}
        </p>
        <p className="mt-1 text-sm text-slate-600">
          PDF or Word (.docx) · up to {MAX_UPLOAD_MB} MB
        </p>

        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="cg-btn-primary mt-6"
        >
          Choose a file
        </button>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void send(file);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-danger-border bg-danger-bg px-4 py-3">
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5 shrink-0 text-danger-fg">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <p className="text-sm font-medium text-danger-fg">{error}</p>
        </div>
      )}

      {/* ── Two-column ──────────────────────────────────────────────────── */}
      <div className="grid gap-6 md:grid-cols-2">

        {/* Before you upload */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Before you upload</h2>
          <ul className="mt-4 space-y-4">
            {[
              { icon: "📝", strong: "Use a text-based file.", rest: " A scan or photo has no readable text — use the PDF your counterparty emailed you." },
              { icon: "🌐", strong: "English only", rest: " for now. Hindi and regional language support is planned." },
              { icon: "🔒", strong: "Your contract stays private.", rest: " Only your account can see it. Delete at any time from My contracts." },
              { icon: "⚡", strong: "~3 second analysis", rest: " for a typical 20-page agreement." },
            ].map((item) => (
              <li key={item.strong} className="flex gap-3">
                <span className="mt-0.5 shrink-0 text-lg leading-none">{item.icon}</span>
                <p className="text-sm leading-relaxed text-slate-700">
                  <strong className="font-semibold text-slate-900">{item.strong}</strong>
                  {item.rest}
                </p>
              </li>
            ))}
          </ul>
        </div>

        {/* Recent analyses */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Recent analyses</h2>
            <Link to="/dashboard"
              className="text-xs font-medium text-slate-500 transition hover:text-slate-900">
              View all →
            </Link>
          </div>

          {history.length === 0 ? (
            <div className="mt-6 flex flex-col items-center py-6 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
                  className="h-6 w-6 text-slate-400">
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <p className="mt-3 text-sm font-medium text-slate-700">No contracts yet</p>
              <p className="mt-1 text-xs text-slate-500">Upload one above to get started.</p>
            </div>
          ) : (
            <ul className="mt-4 divide-y divide-slate-100">
              {history.map((item) => {
                const flagCount = (item.high_risk_count ?? 0) + (item.caution_count ?? 0);
                return (
                  <li key={item.id} className="py-3 first:pt-0 last:pb-0">
                    <Link to={`/contracts/${item.id}/report`}
                      className="group flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800 group-hover:text-slate-900">
                          {item.filename}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">{formatDate(item.uploaded_at)}</p>
                      </div>
                      <div className="shrink-0">
                        {flagCount > 0 ? (
                          <span className="rounded-full bg-danger-bg px-2.5 py-1 text-xs font-semibold text-danger-fg">
                            {flagCount} flag{flagCount !== 1 ? "s" : ""}
                          </span>
                        ) : item.status === "complete" ? (
                          <span className="rounded-full bg-safe-bg px-2.5 py-1 text-xs font-semibold text-safe-fg">
                            Clean
                          </span>
                        ) : (
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                            {item.status}
                          </span>
                        )}
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* ── What we check — dark panel ──────────────────────────────────── */}
      <div className="rounded-2xl bg-slate-900 p-7">
        <h2 className="text-base font-semibold text-white">What ClauseGuard checks</h2>
        <p className="mt-1 text-sm text-slate-400">
          Every clause is matched against 20 types using a documented rubric — not a black box.
        </p>

        <div className="mt-6 grid gap-6 sm:grid-cols-3">
          {/* High risk */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-danger-fg" />
              <span className="text-xs font-bold uppercase tracking-widest text-danger-fg">High risk</span>
            </div>
            <ul className="space-y-2">
              {HIGH_RISK.map((c) => (
                <li key={c.name} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3">
                  <p className="text-sm font-semibold text-white">{c.name}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{c.desc}</p>
                </li>
              ))}
            </ul>
          </div>

          {/* Watch */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-caution-fg" />
              <span className="text-xs font-bold uppercase tracking-widest text-caution-fg">Watch</span>
            </div>
            <ul className="space-y-2">
              {WATCH.map((c) => (
                <li key={c.name} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3">
                  <p className="text-sm font-semibold text-white">{c.name}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{c.desc}</p>
                </li>
              ))}
            </ul>
          </div>

          {/* Info */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-slate-500" />
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Standard</span>
            </div>
            <ul className="space-y-2">
              {INFO.map((c) => (
                <li key={c.name} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3">
                  <p className="text-sm font-semibold text-white">{c.name}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{c.desc}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

    </div>
  );
}
