/**
 * SRS 5.2 and 5.5 require a *persistent* disclaimer that output is not legal
 * advice. It is rendered as a fixed footer on every screen rather than once at
 * sign-up, because a one-time notice is not persistent and the SRS treats this
 * as an informational-safety control, not a formality.
 */
export default function Disclaimer() {
  return (
    <footer className="sticky bottom-0 border-t border-amber-200 bg-amber-50/95 backdrop-blur">
      <p className="mx-auto max-w-5xl px-4 py-2 text-xs leading-relaxed text-amber-900">
        <strong>Not legal advice.</strong> ClauseGuard is an automated triage tool. It
        highlights clauses that are commonly one-sided so you can decide what deserves
        professional review. It can miss things and it can flag things that are fine in
        context — have a licensed professional review anything significant before you sign.
      </p>
    </footer>
  );
}
