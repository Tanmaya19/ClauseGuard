import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
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
  const [shaking, setShaking] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);

  // Remove the shake class once the animation finishes so it can re-trigger
  useEffect(() => {
    if (!shaking) return;
    const t = setTimeout(() => setShaking(false), 420);
    return () => clearTimeout(t);
  }, [shaking]);

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
      const msg = caught instanceof ApiError ? caught.message : "Something went wrong.";
      setError(msg);
      setShaking(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Mini nav */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-slate-900">
            Clause<span className="text-slate-400">Guard</span>
          </Link>
          <Link to="/" className="text-sm text-slate-500 transition hover:text-slate-900">
            ← Back
          </Link>
        </div>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-6 text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h1>
            <p className="mt-1.5 text-sm text-slate-500">
              {mode === "login"
                ? "Sign in to access your contracts."
                : "Free. No credit card required."}
            </p>
          </div>

          {/* Shake wrapper */}
          <div ref={formRef} className={shaking ? "cg-shake" : ""}>
            <div className="cg-card p-6">
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
                        : "text-slate-500 hover:text-slate-700"
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
                    className={`cg-input ${error ? "border-danger-border" : ""}`}
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setError(null); }}
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
                    className={`cg-input ${error ? "border-danger-border" : ""}`}
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setError(null); }}
                  />
                  {mode === "register" && !error && (
                    <p className="mt-1 text-xs text-slate-400">At least 8 characters.</p>
                  )}
                </div>

                {error && (
                  <div className="flex items-start gap-2.5 rounded-lg border border-danger-border bg-danger-bg px-3 py-3">
                    {/* Warning icon */}
                    <svg
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className="mt-0.5 h-4 w-4 shrink-0 text-danger-fg"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <div>
                      <p className="text-sm font-medium text-danger-fg">
                        {mode === "login" ? "Sign-in failed" : "Could not create account"}
                      </p>
                      <p className="mt-0.5 text-xs text-danger-fg opacity-80">{error}</p>
                    </div>
                  </div>
                )}

                <button type="submit" disabled={busy} className="cg-btn-primary w-full">
                  {busy
                    ? "Please wait…"
                    : mode === "login"
                      ? "Sign in"
                      : "Create account"}
                </button>
              </form>
            </div>
          </div>

          <p className="mt-6 text-center text-xs leading-relaxed text-slate-400">
            ClauseGuard is an educational triage tool and does not provide legal advice.
            Your contracts are visible only to your account.
          </p>
        </div>
      </div>
    </div>
  );
}
