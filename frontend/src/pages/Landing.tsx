import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { LiquidMetal } from "@paper-design/shaders-react";

// ── Scroll-reveal wrapper ─────────────────────────────────────────────────────
function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVis(true);
          io.unobserve(el);
        }
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: vis ? 1 : 0,
        transform: vis ? "none" : "translateY(26px)",
        transition: `opacity 0.65s cubic-bezier(.4,0,.2,1) ${delay}ms,
                     transform 0.65s cubic-bezier(.4,0,.2,1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

// ── Logo badge — liquid shimmer behind a floating shield ─────────────────────
function LiquidLogoBadge() {
  return (
    <div className="relative mx-auto mb-8 flex h-28 w-28 items-center justify-center">
      {/* Ambient liquid-metal glow behind the icon */}
      <div className="absolute inset-0 overflow-hidden rounded-3xl opacity-70">
        <LiquidMetal
          colorBack="#0a0f1e"
          colorTint="#3b82f6"
          speed={0.5}
          scale={0.8}
          distortion={0.06}
          repetition={1.6}
          shiftRed={0.05}
          shiftBlue={0.45}
          contour={0.5}
          softness={0.12}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
      {/* Shield icon rendered large over the shimmer */}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        className="relative z-10 h-14 w-14 drop-shadow-lg"
        style={{ color: "#e0f2fe" }}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    </div>
  );
}

// ── Data ─────────────────────────────────────────────────────────────────────

const STEPS = [
  {
    num: "01",
    title: "Upload your contract",
    body: "Drop a PDF or Word file. The system reads it in seconds. Your document is stored privately — only your account can see it.",
  },
  {
    num: "02",
    title: "AI identifies every clause",
    body: "ClauseGuard splits the document into individual clauses and classifies each one against 20 common commercial clause types.",
  },
  {
    num: "03",
    title: "Plain-English flags, instantly",
    body: "Each risky clause gets a plain-English explanation — so you know which 2–3 to raise with a lawyer.",
  },
];

const CLAUSE_TYPES = [
  { name: "Limitation of Liability", risk: "high", desc: "Caps what you can recover if the other side damages your business." },
  { name: "Indemnification", risk: "high", desc: "Makes you pay their legal costs — even when you're not at fault." },
  { name: "IP Assignment", risk: "high", desc: "Silently transfers ownership of your work or inventions to them." },
  { name: "Unilateral Termination", risk: "high", desc: "Lets them walk away with 2 days' notice; you need 90." },
  { name: "Non-Compete", risk: "caution", desc: "Restricts who you can work with after the contract ends." },
  { name: "Automatic Renewal", risk: "caution", desc: "Locks you in unless you cancel on a specific date." },
  { name: "Governing Law", risk: "caution", desc: "Forces disputes into their home city's courts, not yours." },
  { name: "Audit Rights", risk: "caution", desc: "Lets them inspect your books and operations on short notice." },
];

const PAIN_POINTS = [
  { icon: "📄", text: "You receive a 25-page vendor agreement from a large buyer." },
  { icon: "🔴", text: "Clause 14 assigns all IP you create to them — forever." },
  { icon: "🔴", text: "Clause 18 caps your damages at ₹5,000 even if they owe you ₹50 lakh." },
  { icon: "🔴", text: "Clause 23 lets them terminate with 2 days' notice; you need 90 days." },
  { icon: "✅", text: "ClauseGuard flags all three before you sign." },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function TrustItem({ icon, text }: { icon: string; text: string }) {
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden="true">{icon}</span>
      <span>{text}</span>
    </span>
  );
}

function StepCard({ step, delay }: { step: (typeof STEPS)[0]; delay: number }) {
  return (
    <Reveal delay={delay}>
      <div className="group rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
        <div className="text-4xl font-black text-slate-100 transition group-hover:text-slate-200">
          {step.num}
        </div>
        <h3 className="mt-4 text-lg font-semibold text-slate-900">{step.title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
      </div>
    </Reveal>
  );
}

function ClauseCard({ ct, delay }: { ct: (typeof CLAUSE_TYPES)[0]; delay: number }) {
  const dotColor =
    ct.risk === "high" ? "bg-danger-fg" : ct.risk === "caution" ? "bg-caution-fg" : "bg-safe-fg";
  const labelColor =
    ct.risk === "high"
      ? "text-danger-fg"
      : ct.risk === "caution"
        ? "text-caution-fg"
        : "text-safe-fg";
  const labelText =
    ct.risk === "high" ? "High risk" : ct.risk === "caution" ? "Caution" : "Standard";

  return (
    <Reveal delay={delay}>
      <div className="h-full rounded-xl border border-slate-700 bg-slate-800 p-4 transition hover:border-slate-500">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${dotColor}`} />
          <span className={`text-xs font-semibold uppercase tracking-wide ${labelColor}`}>
            {labelText}
          </span>
        </div>
        <p className="mt-2 text-sm font-semibold text-white">{ct.name}</p>
        <p className="mt-1 text-xs leading-relaxed text-slate-400">{ct.desc}</p>
      </div>
    </Reveal>
  );
}

function PainPointRow({ icon, text }: { icon: string; text: string }) {
  const isGood = icon === "✅";
  const isDoc = text.startsWith("You receive");
  const borderBg = isGood
    ? "border-safe-border bg-safe-bg"
    : isDoc
      ? "border-slate-200 bg-white"
      : "border-danger-border bg-danger-bg";
  return (
    <div className={`flex items-start gap-3 rounded-xl border p-4 transition hover:shadow-sm ${borderBg}`}>
      <span className="text-base leading-none">{icon}</span>
      <p className="text-sm leading-relaxed text-slate-700">{text}</p>
    </div>
  );
}

// ── Landing page ─────────────────────────────────────────────────────────────

export default function Landing() {
  const [heroVis, setHeroVis] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setHeroVis(true), 80);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Public nav ────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-800/40 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="text-lg font-semibold tracking-tight text-white">
            Clause<span className="text-slate-400">Guard</span>
          </span>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-slate-300 transition hover:text-white">
              Sign in
            </Link>
            <Link
              to="/login"
              className="rounded-lg bg-white px-4 py-1.5 text-sm font-medium text-slate-900 transition hover:bg-slate-100"
            >
              Get started free
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────────────── */}
      <section
        className="relative overflow-hidden px-4 pb-24 pt-20 text-center"
        style={{
          minHeight: "88vh",
          background: "linear-gradient(160deg, #0a0f1e 0%, #0f1f3d 50%, #060c18 100%)",
        }}
      >

        {/* Hero content */}
        <div className="relative z-10 flex flex-col items-center">

          {/* Liquid-metal shield badge */}
          <div
            style={{
              opacity: heroVis ? 1 : 0,
              transform: heroVis ? "scale(1)" : "scale(0.8)",
              transition: "opacity 0.6s ease 0ms, transform 0.6s ease 0ms",
            }}
          >
            <LiquidLogoBadge />
          </div>

          <div
            style={{
              opacity: heroVis ? 1 : 0,
              transform: heroVis ? "none" : "translateY(22px)",
              transition: "opacity 0.7s ease 120ms, transform 0.7s ease 120ms",
            }}
          >
            <span className="inline-block rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs font-medium text-slate-300 backdrop-blur">
              Built for Indian MSMEs
            </span>

            <h1 className="mt-5 text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl">
              Know which clauses
              <br />
              <span className="text-sky-400">to fight for.</span>
            </h1>
          </div>

          <div
            style={{
              opacity: heroVis ? 1 : 0,
              transform: heroVis ? "none" : "translateY(22px)",
              transition: "opacity 0.7s ease 260ms, transform 0.7s ease 260ms",
            }}
          >
            <p className="mx-auto mt-5 max-w-lg text-base leading-relaxed text-slate-200">
              Upload a contract. Get plain-English flags on the clauses that are one-sided — so you know exactly what to push back on.
            </p>
          </div>

          <div
            style={{
              opacity: heroVis ? 1 : 0,
              transform: heroVis ? "none" : "translateY(22px)",
              transition: "opacity 0.7s ease 380ms, transform 0.7s ease 380ms",
            }}
            className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center"
          >
            <Link
              to="/login"
              className="rounded-xl bg-white px-7 py-3.5 text-base font-semibold text-slate-900 shadow-lg transition hover:bg-slate-100"
            >
              Analyse your first contract →
            </Link>
            <span className="text-sm text-slate-500">
              No credit card · Free to use
            </span>
          </div>
        </div>
      </section>

      {/* ── Trust bar ─────────────────────────────────────────────── */}
      <div className="border-y border-slate-200 bg-white py-5">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-10 gap-y-3 px-4 text-sm text-slate-600">
          <TrustItem icon="🔍" text="20 clause types checked" />
          <TrustItem icon="🛡️" text="Rule-based scoring — not a black box" />
          <TrustItem icon="🔒" text="Private to your account" />
          <TrustItem icon="⚡" text="~3 second analysis" />
        </div>
      </div>

      {/* ── How it works ──────────────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-4 py-20">
        <Reveal>
          <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900">
            How it works
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-slate-500">
            From "I need to sign this by Friday" to "I know exactly which 2 clauses to push back on" — in under a minute.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <StepCard key={step.num} step={step} delay={i * 100} />
          ))}
        </div>
      </section>

      {/* ── What gets flagged — dark section ──────────────────────── */}
      <section className="bg-slate-900 px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-center text-3xl font-bold tracking-tight text-white">
              What ClauseGuard looks for
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-center text-slate-400">
              Every clause is checked against a documented rubric. Here's a sample of what we surface.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {CLAUSE_TYPES.map((ct, i) => (
              <ClauseCard key={ct.name} ct={ct} delay={i * 55} />
            ))}
          </div>

          <Reveal delay={200}>
            <p className="mt-8 text-center text-sm text-slate-500">
              And 12 more clause types — payment terms, governing law, force majeure, warranties, and more.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── Why MSME ──────────────────────────────────────────────── */}
      <section className="mx-auto max-w-5xl px-4 py-20">
        <div className="grid gap-14 md:grid-cols-2 md:items-start">
          <Reveal>
            <h2 className="text-3xl font-bold tracking-tight text-slate-900">
              Built for the business owner who can't afford a lawyer on retainer
            </h2>
            <p className="mt-4 leading-relaxed text-slate-600">
              You're a manufacturer, a supplier, a consultant, or a software shop. A large client sends you a vendor agreement — 20 pages, dense legalese, "sign by next week." You can't afford ₹50,000 for a full review every time.
            </p>
            <p className="mt-3 leading-relaxed text-slate-600">
              ClauseGuard doesn't replace your lawyer. It tells you <em>which</em> 2–3 clauses are worth spending that money on.
            </p>
          </Reveal>

          <Reveal delay={120}>
            <div className="space-y-3">
              {PAIN_POINTS.map((p) => (
                <PainPointRow key={p.text} icon={p.icon} text={p.text} />
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Disclaimer ────────────────────────────────────────────── */}
      <div className="border-y border-amber-200 bg-amber-50 px-4 py-6">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm leading-relaxed text-amber-900">
            <strong>Not legal advice.</strong> ClauseGuard is an automated triage tool. It can miss things and can flag things that are fine in context. Always have a licensed professional review anything significant before you sign.
          </p>
        </div>
      </div>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 bg-white px-4 py-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
          <span>
            <span className="font-semibold text-slate-800">ClauseGuard</span>
            <span className="ml-2 text-slate-500">· 24BPS1042 · VIT Chennai</span>
          </span>
          <span>Educational triage tool · Not a commercial legal product</span>
        </div>
      </footer>
    </div>
  );
}
