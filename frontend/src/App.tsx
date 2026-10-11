import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, auth } from "./api/client";
import Disclaimer from "./components/Disclaimer";
import Nav from "./components/Nav";
import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Processing from "./pages/Processing";
import ReportView from "./pages/Report";
import Upload from "./pages/Upload";

export default function App() {
  const [email, setEmail] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  // Verify the stored token against the server on load. A token in
  // localStorage proves nothing about whether it is still valid.
  useEffect(() => {
    if (!auth.get()) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then((user) => setEmail(user.email))
      .catch(() => auth.clear())
      .finally(() => setChecking(false));
  }, []);

  const onAuthenticated = useCallback(
    (userEmail: string) => {
      setEmail(userEmail);
      navigate("/");
    },
    [navigate],
  );

  const signOut = useCallback(() => {
    auth.clear();
    setEmail(null);
    navigate("/");
  }, [navigate]);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading…
      </div>
    );
  }

  if (!email) {
    return <Auth onAuthenticated={onAuthenticated} />;
  }

  return (
    <div className="min-h-screen">
      <Nav email={email} onSignOut={signOut} />
      <main className="mx-auto w-full max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/contracts/:id/processing" element={<Processing />} />
          <Route path="/contracts/:id/report" element={<ReportView />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Disclaimer />
    </div>
  );
}
