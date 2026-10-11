import { Link, useLocation } from "react-router-dom";

interface Props {
  email: string;
  onSignOut: () => void;
}

const LINKS = [
  { to: "/", label: "Analyse a contract" },
  { to: "/dashboard", label: "My contracts" },
];

export default function Nav({ email, onSignOut }: Props) {
  const { pathname } = useLocation();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link to="/" className="text-lg font-semibold tracking-tight text-slate-900">
          Clause<span className="text-slate-400">Guard</span>
        </Link>

        <nav className="flex gap-1">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`rounded-lg px-3 py-1.5 text-sm transition ${
                pathname === link.to
                  ? "bg-slate-100 font-medium text-slate-900"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="hidden text-slate-500 sm:inline">{email}</span>
          <button onClick={onSignOut} className="text-slate-600 hover:text-slate-900">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
