/**
 * Typed API client.
 *
 * Types mirror backend/app/schemas/. The backend serves the clause taxonomy
 * and the disclaimer text through the API rather than the frontend hard-coding
 * them, so those cannot drift between the web view and the PDF export.
 */

export type ContractStatus =
  | "uploaded"
  | "extracting"
  | "segmenting"
  | "classifying"
  | "scoring"
  | "complete"
  | "failed";

export type RiskLevel = "safe" | "caution" | "high_risk" | "unassessable";
export type Severity = "caution" | "high";

export interface Prediction {
  label: string;
  display: string;
  confidence: number;
}

export interface Finding {
  rule_id: string;
  severity: Severity;
  explanation: string;
}

export interface Clause {
  id: string;
  ordinal: number;
  heading: string | null;
  text: string;
  risk: RiskLevel;
  predictions: Prediction[];
  findings: Finding[];
  needs_manual_review: boolean;
  segmentation_method: string;
}

export interface ContractFinding {
  rule_id: string;
  severity: Severity;
  explanation: string;
  criterion: string;
}

export interface ReportSummary {
  clause_count: number;
  risk_counts: Partial<Record<RiskLevel, number>>;
  needs_review_count: number;
  uncategorized_count: number;
  clause_type_counts: Record<string, number>;
  clause_type_labels: Record<string, string>;
  contract_findings: ContractFinding[];
}

export interface Report {
  contract_id: string;
  filename: string;
  uploaded_at: string;
  generated_at: string;
  rubric_version: string;
  model_version: string;
  summary: ReportSummary;
  clauses: Clause[];
  disclaimer: string;
}

export interface AnalysisStatus {
  contract_id: string;
  status: ContractStatus;
  status_detail: string | null;
  error_code: string | null;
  error_message: string | null;
  progress: number;
}

export interface ContractRow {
  id: string;
  filename: string;
  status: ContractStatus;
  uploaded_at: string;
  processed_at: string | null;
  clause_count: number | null;
  high_risk_count: number | null;
  caution_count: number | null;
}

export interface Dashboard {
  total_contracts: number;
  total_clauses: number;
  risk_totals: Record<string, number>;
  reviewed_over_time: { date: string; count: number }[];
  recent: ContractRow[];
}

const BASE = "/api/v1";
const TOKEN_KEY = "clauseguard.token";

export const auth = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = auth.get();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BASE}${path}`, { ...init, headers });

  if (response.status === 401) {
    // A stale token should land the user on the login screen rather than
    // leaving every panel showing an error.
    auth.clear();
    throw new ApiError(401, "Your session has expired. Please sign in again.");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        detail = body.detail[0].msg;
      }
    } catch {
      // Non-JSON error body; the generic message stands.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: string; email: string }>("/auth/me"),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ contract_id: string; poll_url: string }>("/contracts", {
      method: "POST",
      body: form,
    });
  },

  status: (id: string) => request<AnalysisStatus>(`/contracts/${id}/status`),
  report: (id: string) => request<Report>(`/reports/${id}`),
  history: () => request<ContractRow[]>("/contracts"),
  dashboard: () => request<Dashboard>("/contracts/dashboard/overview"),
  remove: (id: string) => request<void>(`/contracts/${id}`, { method: "DELETE" }),
  reanalyse: (id: string) =>
    request<{ contract_id: string }>(`/contracts/${id}/reanalyse`, { method: "POST" }),

  /** Fetches the PDF as a blob so the Authorization header is sent — a plain
   *  link would omit it and get a 401. */
  downloadPdf: async (id: string, filename: string) => {
    const token = auth.get();
    const response = await fetch(`${BASE}/reports/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new ApiError(response.status, "Could not generate the PDF.");

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ClauseGuard - ${filename.replace(/\.[^.]+$/, "")}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export const MAX_UPLOAD_MB = 10; // TBD-1; the server enforces it too

export const RISK_META: Record<
  RiskLevel,
  { label: string; blurb: string; className: string; dot: string }
> = {
  high_risk: {
    label: "Needs attention",
    blurb: "We would raise this before signing.",
    className: "bg-danger-bg text-danger-fg border-danger-border",
    dot: "bg-danger-fg",
  },
  caution: {
    label: "Worth a look",
    blurb: "Worth understanding, and possibly negotiable.",
    className: "bg-caution-bg text-caution-fg border-caution-border",
    dot: "bg-caution-fg",
  },
  safe: {
    label: "Looks standard",
    blurb: "Nothing in our rubric flagged this.",
    className: "bg-safe-bg text-safe-fg border-safe-border",
    dot: "bg-safe-fg",
  },
  unassessable: {
    label: "Not assessed",
    blurb: "We could not identify the clause type confidently.",
    className: "bg-muted-bg text-muted-fg border-muted-border",
    dot: "bg-muted-fg",
  },
};

export const STAGE_COPY: Record<ContractStatus, string> = {
  uploaded: "Queued",
  extracting: "Reading the document",
  segmenting: "Splitting it into clauses",
  classifying: "Identifying what each clause does",
  scoring: "Checking clauses against the rubric",
  complete: "Done",
  failed: "Could not be analysed",
};
