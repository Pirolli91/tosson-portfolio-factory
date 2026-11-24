# AGENTS.md — Sprint 5 workspace (Job-Hunt Portfolio Factory + Auction Intelligence v2)
Read this and SPRINT5-SPEC-2026-11-23.md before any work. Owner: Temitope Soneye. Builder: Antigravity. Adjudicator/operator: Muse.

## Non-negotiable rules (owner's standing rules — do not soften, do not re-litigate)
- Plan mode first: ONE implementation plan → STOP → Muse adjudicates → only then code. Gemini default; Claude only for a named hard problem. Max 2 parallel agents.
- NO Progressive Insurance data, systems, or proprietary material in any form. Portfolio data = public EPA data only.
- NO fabricated experience: every artifact must actually run (dbt green, DAG executes, numbers reconcile). Claim language stays precise (dialect-only SQL is labelled dialect-only; the Power BI claim rests on the DAX library + model spec — no .pbix in this sprint).
- NOTHING submits, applies, bids, buys, or sends. No account creation. Auction modules are read-only analysis.
- UCMR 5 = occurrence/screening vs the MCL benchmark, NEVER a violation claim. Legal name: "Tosson Services LLC dba Tosson Environmental Analytics".
- Source use (MASTER LAYER, 2026-11-02): public domain / CC BY / CC0 verified on the source's own page, or use-by-citing with full URL. Unverifiable = excluded and named as excluded. The phrase "reuse terms unverified" never appears in any output.
- No credentials or env VALUES in this workspace — variable NAMES only. Owner-staged fixtures/ are read-only, are the owner's own professional documents, and are NEVER re-included in the deliverable zip.
- Declare every dependency with exact versions in the plan; venv-isolated installs only. A SKILL.md runbook per build is a required deliverable (.agents/skills/<build>/SKILL.md). The shipped test suite must pass with NO fixtures folder present (synthetic mini-fixtures under tests/ or injectable paths).
- Commit/save every deliverable into this folder at receipt. When done, zip the folder (excluding fixtures/) for Muse's shadow run.
