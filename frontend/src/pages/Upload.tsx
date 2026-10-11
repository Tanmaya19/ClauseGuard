import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, MAX_UPLOAD_MB, api } from "../api/client";

const ACCEPTED = [".pdf", ".docx"];

export default function Upload() {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  async function send(file: File) {
    setError(null);

    const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (!ACCEPTED.includes(extension)) {
      setError("Only PDF and Word (.docx) files can be analysed.");
      return;
    }

    // Client-side size check for a fast message. The server enforces the same
    // limit on the real bytes, because this check is a convenience and not a
    // control (REQ-1.2).
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

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
        Analyse a contract
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
        Upload a vendor, supply, service or NDA agreement. ClauseGuard splits it into
        clauses, works out what each one does, and flags the ones that are commonly
        one-sided — so you know which parts are worth paying a lawyer to look at.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void send(file);
        }}
        className={`mt-6 rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragging ? "border-slate-900 bg-slate-100" : "border-slate-300 bg-white"
        }`}
      >
        <p className="text-sm font-medium text-slate-700">
          {busy ? "Uploading…" : "Drag a contract here"}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          PDF or Word (.docx), up to {MAX_UPLOAD_MB} MB
        </p>

        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="cg-btn-secondary mt-4"
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
            // Reset so selecting the same file twice still fires onChange.
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger-fg">
          {error}
        </p>
      )}

      <div className="cg-card mt-8 p-5">
        <h2 className="text-sm font-semibold text-slate-900">Before you upload</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-600">
          <li>
            <strong className="font-medium text-slate-700">Use a text-based file.</strong>{" "}
            A scan or a photo of a contract has no readable text, so we cannot analyse it.
            Use the file your counterparty emailed you rather than a scanned printout.
          </li>
          <li>
            <strong className="font-medium text-slate-700">English only</strong> for now.
          </li>
          <li>
            <strong className="font-medium text-slate-700">Your contract stays private.</strong>{" "}
            Only your account can see it, and you can delete it at any time.
          </li>
        </ul>
      </div>
    </div>
  );
}
