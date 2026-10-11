import { Link, useLocation } from "react-router-dom";
import { LiquidMetal } from "@paper-design/shaders-react";

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

        {/* Logo — liquid-metal shimmer in a rounded square with shield */}
        <Link to="/" className="group relative inline-flex items-center gap-2.5">
          <div className="relative h-9 w-9 overflow-hidden rounded-xl shadow-sm">
            <LiquidMetal
              colorBack="#0a0f1e"
              colorTint="#3b82f6"
              speed={0.4}
              scale={0.85}
              distortion={0.05}
              repetition={1.6}
              shiftRed={0.04}
              shiftBlue={0.48}
              contour={0.5}
              softness={0.12}
              style={{ width: "100%", height: "100%" }}
            />
            {/* Shield icon */}
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="absolute inset-0 m-auto h-5 w-5"
              style={{ color: "#bae6fd" }}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
              />
            </svg>
          </div>
          <span className="text-lg font-semibold tracking-tight text-slate-900 transition group-hover:text-slate-700">
            Clause<span className="text-slate-400">Guard</span>
          </span>
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
          <button onClick={onSignOut} className="text-slate-600 hover:text-slate-900 transition">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
