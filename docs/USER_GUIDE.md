# ClauseGuard user guide

For the business owner or staff member using ClauseGuard. No legal or
technical background assumed.

Satisfies the user-documentation requirements in SRS section 2.6: a step-by-step
guide, a plain-language glossary matching SRS Appendix A, and an FAQ that states
the tool's boundaries.

---

> **ClauseGuard is not a lawyer.** It points out clauses that are commonly
> one-sided so you can decide what is worth paying someone to look at properly.
> It can miss things, and it can flag things that are perfectly fine in your
> situation. Have a licensed professional review anything significant before
> you sign.

---

## 1. What this tool is for

You have been sent a contract — a supply agreement, a service contract, an NDA.
It is fifteen pages long, and you need to sign it this week. You do not have a
lawyer on retainer, and paying one to read all fifteen pages is not worth it.

ClauseGuard reads the contract and tells you which two or three clauses are the
ones that actually matter. That is the whole idea: **triage, not advice.** You
end up either reassured, or with a short list of specific questions to ask.

## 2. Getting a contract reviewed

### Step 1 — Create an account
Email and a password of at least 8 characters. Contracts you upload are visible
only to your account.

### Step 2 — Upload the contract
Drag the file onto the upload box, or click **Choose a file**.

**It must be a text-based PDF or a Word `.docx` file, under 10 MB.**

This matters more than it sounds. The file your counterparty emailed you is
almost always fine. A photo of a printed contract, or a scan from an office
machine, is a *picture* of text — there are no words in the file for software to
read, so ClauseGuard will tell you it cannot process it. If that happens, ask
the other side to email you the original document.

### Step 3 — Wait a few seconds
You will see the stages as they happen: reading the document, splitting it into
clauses, identifying what each clause does, checking them against the rubric.

### Step 4 — Read the report

Clauses are grouped into four buckets:

| | What it means | What to do |
|---|---|---|
| **Needs attention** | A clause we would raise before signing | Read these first. Ask about each one. |
| **Worth a look** | Worth understanding, possibly negotiable | Read if you have time, or if the contract is large. |
| **Looks standard** | Nothing in our rubric flagged it | Skim. |
| **Not assessed** | We could not confidently tell what the clause does | Read it yourself — we have no opinion, which is not the same as it being fine. |

Click any of the four summary tiles to filter the list.

Every flagged clause has a **"Why this is flagged"** panel. It explains the
commercial consequence in plain English and usually suggests what to ask for.
That wording is what you can take into a conversation with the other side.

### Step 5 — Download the PDF
**Download PDF** produces a print-ready version with the clauses, the flags and
the explanations. Useful for taking into a meeting or forwarding to a lawyer —
if you do send it to a lawyer, it tells them where to focus, which should reduce
what they charge you.

## 3. Reading a flag well

Three things worth keeping in mind:

**A flag is a question, not a verdict.** "Needs attention" means *ask about
this*, not *refuse to sign*. A one-sided clause may be entirely normal in your
industry, or a reasonable price for other terms you are getting.

**Absence is often the problem.** Many flags are about something *missing* — no
cap on liability, no cure period, no notice window before auto-renewal. These
are easy to miss when reading yourself, because there is nothing on the page to
notice.

**Check the "Missing from this contract" panel.** If it appears, it lists
protections we expected and could not find anywhere in the document.

## 4. Glossary

Matches SRS Appendix A.

| Term | What it means |
|---|---|
| **Clause** | One numbered provision in a contract — a single paragraph or section dealing with one topic. |
| **Clause type** | What a clause *does*: indemnity, termination, payment terms, and so on. ClauseGuard recognises 20 types. |
| **Risk level** | Our judgement of how one-sided a clause is: Needs attention, Worth a look, Looks standard, or Not assessed. |
| **Rubric** | The written list of criteria we check against. Every flag comes from a named rule in it, and the rubric is published in `docs/RUBRIC.md`. |
| **Indemnity** | A promise to cover someone else's losses. If you indemnify them, you pay when things go wrong — even for problems you did not cause, depending on the wording. |
| **Liability cap** | A ceiling on how much you can be made to pay. Without one, your exposure is open-ended. Usually set at the total fees paid over the previous twelve months. |
| **Termination for convenience** | The right to end the contract without a reason. Fine if both sides have it; a problem if only they do. |
| **Cure period** | Time you get to fix a breach before the other side can terminate. Without one, a small slip can cost you the whole contract. |
| **Auto-renewal** | The contract renews itself unless you opt out in time. Note the deadline in your calendar the day you sign. |
| **Force majeure** | Covers events outside anyone's control — floods, strikes, government restrictions. Without such a clause, you can still be held to your obligations when something genuinely stops you performing. |
| **Governing law / jurisdiction** | Which country's law applies, and whose courts decide. Pursuing a claim abroad is far more expensive than doing so in India. |
| **Arbitration** | Private dispute resolution instead of court. Faster than litigation, but where it takes place matters a great deal to the cost. |
| **MSMED Act, 2006** | Indian law that entitles a registered micro or small enterprise to be paid within 45 days. A longer period written into a contract does not remove that right. |
| **Confidence** | How sure the system is that it identified a clause type correctly. Never 100%. |

## 5. FAQ

**Is this legal advice?**
No. ClauseGuard is an educational triage tool. It has no knowledge of your
business, your relationship with the other party, or your commercial priorities
— all of which change what a clause actually means for you. Use it to decide
*what to ask about*, and get a licensed professional for anything significant.

**How accurate is it?**
It identifies clause types with a trained model, which is good but not perfect,
and it flags risks using a fixed, published rubric, which catches what it was
written to catch and nothing else. It will miss unusual drafting, and it will
sometimes flag a clause that is fine in context. Treat "Looks standard" as *we
found nothing*, not as *this is safe*.

**Why does it flag a clause that seems fine to me?**
Probably because you have context the tool does not. A one-sided indemnity may
be the industry norm for your line of work, or something you accepted in return
for better pricing. The flag is still worth reading — then you can dismiss it
knowingly rather than by not having noticed.

**It says a clause is "Not assessed". Is that bad?**
It means we could not confidently tell what the clause does, so we did not
judge it. We report that honestly rather than calling it safe. Read those
clauses yourself.

**Can it read a scanned contract?**
No. A scan is an image, and there is no text in the file to read. We detect this
and say so rather than guessing. Ask for the original document.

**Does it work on contracts in Hindi or other Indian languages?**
Not in this version — English only.

**Who can see my contracts?**
Only your account. Uploads are tied to your user and every request is checked
against it. You can delete a contract and its report at any time from **My
contracts**, which removes the stored file as well as the analysis.

**Why does the report mention a "rubric version"?**
So a report stays explainable later. If we change the criteria, your old report
still records which version of the rules produced it — otherwise an old flag
could no longer be traced to any rule.

**The clause text looks wrong or runs into the next clause.**
Some contracts are formatted unusually and the splitting is imperfect. Where we
know a clause was hard to separate, we say so under the clause text. Read those
in the original document too.

**Can I re-run a contract after the rubric improves?**
Yes. The original file is kept against your account, so re-analysis does not
need a re-upload.
