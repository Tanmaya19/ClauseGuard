import { useState } from "react";
import { ApiError, api, auth } from "../api/client";

interface Props {
  onAuthenticated: (email: string) => void;
}

export default function Auth({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password);
      auth.set(result.access_token);
      onAuthenticated(email);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <h1 className="text-center text-2xl font-semibold tracking-tight text-slate-900">
          Clause<span className="text-slate-400">Guard</span>
        </h1>
        <p className="mt-2 text-center text-sm text-slate-600">
          Find the clauses in your contract that deserve a closer look.
        </p>

        <div className="cg-card mt-6 p-6">
          <div className="mb-5 flex gap-1 rounded-lg bg-slate-100 p-1">
            {(["login", "register"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => {
                  setMode(option);
                  setError(null);
                }}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm transition ${
                  mode === option
                    ? "bg-white font-medium text-slate-900 shadow-sm"
                    : "text-slate-600"
                }`}
              >
                {option === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="cg-label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="cg-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="cg-label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className="cg-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {mode === "register" && (
                <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>
              )}
            </div>

            {error && (
              <p className="rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
                {error}
              </p>
            )}

            <button type="submit" disabled={busy} className="cg-btn-primary w-full">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs leading-relaxed text-slate-500">
          ClauseGuard is an educational triage tool and does not provide legal advice.
          Your contracts are visible only to your account.
        </p>
      </div>
    </div>
  );
}
