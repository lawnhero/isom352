# Virtual TA companion — design validation (v2)

*2026-08-24 · Re-evaluation of the from-scratch companion design (chat, 8/24) against the settled course rules, the repo's own logged evidence, and the calendar. Supersedes the chat version. Companion to `docs/course_alignment_investigation.md`.*

---

## 1 · Verdict summary

| Element (v1) | Verdict | Why |
|---|---|---|
| Artifact-as-unit-of-exchange | **Survives** | Matches the course's artifact economy; no counter-evidence |
| Verification-drill engine, engineered not generated | **Survives** | Direct B3/D3 compliance; nothing else clears "findable, plausible, runs" |
| Phased build on the fork's chassis | **Survives** | Calendar leaves no alternative; chassis is commodity |
| Instructor weekly brief | **Survives, sharpened** | Becomes the still-unbuilt instrumentation plan |
| Refusal list (no homework solver, no silent fixes, no beat enforcement) | **Survives** | Restates the thesis; no tension found |
| Four mode doors replacing the router | **Fails as stated — revised §2.1** | The repo's own usage data contradicts it |
| Identity + per-student mastery ledger | **Fails as stated — revised §2.2** | LTI infeasible this term; E1 removes the need for strong identity |
| Adversary logs as instructor evidence | **Fails as stated — revised §2.3** | Creates a surveillance instrument the course's own norms argue against |
| Auditee mode on team data via dirt recipes | **Overbuilt — simplified §2.4** | s26's settled mechanic doesn't need planted flaws |
| Drill bank as standalone build (60–80 artifacts) | **Infeasible — repriced §2.5** | Collides with the existing build backlog; becomes a session-build byproduct |
| Success criteria | **Missing in v1 — added §3** | A design with no failure test isn't validated |

## 2 · Revisions, with reasons

### 2.1 Mode doors: only where the choice is real

v1 said: kill the hidden router, make students choose among four named relationships on every interaction, because choosing the mode is the judgment being taught (C1).

[Certain] The repo's own logs refute the strong version. The 550 sidebar comment records 508 logged turns in which the old three-way response-mode control was left on default 459 times, used once for hint-first — students do not operate mode switches on routine questions, and the 550 team already collapsed the control for exactly this reason. Forcing a door on "when are office hours" is friction that teaches nothing.

**Revision:** two-lane interaction. *Lane 1 — ask:* free text, invisible router, exactly as the fork works today; covers logistics, concepts, recaps, read-code. *Lane 2 — submit an artifact:* explicit doors (Drill me · Attack my spec · Audit this notebook · Check my attempt), each opening with one line naming which AI relationship the student just chose. C1's meta-lesson lives where the choice is consequential — on artifacts — and nowhere else. The doors are also what gets a Canvas-page walkthrough; the ask lane needs no instruction.

### 2.2 Identity: the course design itself removes the hard problem

v1 made a per-student mastery ledger the core state, requiring login (Canvas LTI or magic link).

[Likely] Emory LTI approval is a security-review process measured in weeks to months — dead for this term. But the deeper point: settled rule E1 says individual skill is measured in the room, never via take-home artifacts. The companion is therefore **constitutionally formative** — its records can never be grading evidence. That collapses the identity requirement: formative analytics tolerate self-asserted identity.

**Revision:** a student enters a self-chosen handle (or NetID, honor-system) once per device; the mastery ledger keys on that. Good enough for spaced drill selection and section-level triage aggregates; never displayed to the instructor at individual grain (see §2.3). LTI becomes a next-year improvement, not a dependency. The risk accepted: a student can reset their handle and their drill history — tolerable, because nothing rides on it.

### 2.3 Adversary evidence: export, don't surveil

v1 sold `attack_spec` partly as instructor-side evidence that each team ran the adversary pass before s16.

I now think that's the wrong side of a line the course itself draws. C2's culture is disclosure-positive and self-reported; an instructor dashboard of who-ran-what turns the companion into a monitoring instrument, which (a) changes what students will honestly paste into it, (b) requires exactly the strong identity §2.2 just removed, and (c) hands students a box-ticking target (paste anything, get the checkmark).

**Revision:** the adversary session ends by generating a **student-exported artifact** — a one-page attack transcript with the three sharpest objections and the team's written responses — which the team attaches to their scoping-meeting materials themselves. The instructor grades the artifact in the meeting, not the log. Same evidentiary value, zero surveillance, and the team must *engage* with the objections to have anything to attach. The companion's own logs stay aggregate-only for everyone.

### 2.4 Auditee mode: s26 needs no planted flaws

v1 proposed the companion generate deliberately-flawed analyses of each team's own project data via dirt recipes.

[Likely] That fails B3 on contact with real team data: dirt recipes are written against known-clean masters with known schemas; on heterogeneous, already-dirty cycle-2 datasets a planted flaw may not apply, may be swamped by organic flaws, or may not be findable — and there's no capacity to hand-verify ~20 team-specific artifacts in week 13. More to the point, the settled s26 mechanic — teams verify an agent's work against their own completed analysis — doesn't require planted flaws at all: **a genuinely agent-built analysis supplies organic flaws for free**, and the team's completed work is the answer key.

**Revision:** planted flaws (dirt recipes) are for *spine-based* drills and exams only, where quality is controllable. For s26, the companion's role is to *be* the agent — run a scripted agentic analysis on the team's data — plus provide the audit scaffold (source-vs-output sampling, the field-guide checklist). Simpler, settled-decision-compliant, and it removes the hardest engineering item from the plan.

### 2.5 Drill bank: a byproduct, not a project

v1 priced the bank at 60–80 curated artifacts. [Certain] That collides head-on with the existing backlog (cycle-1 notebooks 6/8/9/10, lab 1, exam 1, field guide, s1 demo, cycle-2 notebooks…). It would be the first thing cut, and the design's centerpiece dies quietly.

**Revision:** every session build already engineers one Verify trap from a clean master via `dirt_injection.py`. Add one step to the session-build pipeline: **each trap exports 1–2 drill variants** (same disease, re-parameterized on the spine — different neighborhood, different column, different threshold) plus one clean-with-caveats control. The bank then grows automatically at the pace diseases debut; by s7 that's roughly 15–20 artifacts covering every disease taught so far, which is exactly the set B3 permits drilling anyway. Marginal cost per session: minutes, not days.

One addition while we're here: drills carry a **conditions toggle** mirroring D1 — *lab conditions* (field guide open, encouraged) vs. *exam conditions* (guide closed, sign/don't-sign under time pressure). The toggle teaches the guide's status: allowed in labs, absent in exams.

### 2.6 Two smaller additions

**Portfolio exports.** Portfolio collection is settled as weekly Canvas upload. Any assistant-mode session and any completed drill can emit a portfolio-ready snippet (disclosure line, the student's checking sentence, the drill verdict with the student's explanation). Student-initiated, student-owned — consistent with §2.3's export-don't-surveil stance.

**Defense rehearsal (late, optional).** For s24 dry runs and the s27–28 defense, an adversary variant that cold-calls: given the team's draft deck or memo, it asks attack-segment questions and any teammate practices answering. Cheap to build once `attack_spec` exists (same chain, different prompt), directly serves E5. Proposed, not committed — cut first if December arrives too fast.

## 3 · What v1 was missing entirely: a failure test

A design isn't validated until it says what failure looks like. Proposed instrumentation, all buildable on the existing MongoDB log + `generate_weekly_report.py`:

- **Adoption:** weekly active users per section; drill completions per week. Failure signal: drills < ~30 completions/section/week by s9 — means the drill loop isn't in the course's incentive path and needs a portfolio or participation hook (instructor decision, not a silent fix).
- **Calibration:** on drills, track hit rate on dirty artifacts *and* false-alarm rate on clean controls, per disease. The pedagogically interesting curve is false alarms falling over the term (D3's "not crying wolf"). This is also the instructor's s25 triage input and exam-difficulty evidence.
- **Integrity guard:** fraction of turns that are do-my-deliverable attempts, and whether the refusal-plus-reframe held. Rising trend = the boundary prompt is leaking.
- **Quality harness:** a golden question set (one per route, one per disease) run weekly through the existing `smoke_turn.py`/`export_queries.py` tooling before each content push — the repo already has the calibration muscle; point it at regression-testing the 352 surface.
- **The honest limit:** [Certain] with no prior cohort, no causal claim about exam impact is available this year. The best available check is within-cohort: do drill-active students locate planted flaws on Exam 1 at higher rates (directional, confounded, still worth computing).

## 4 · Revised phase plan (unchanged where not listed)

| Phase | Deadline | Contents | Change from v1 |
|---|---|---|---|
| 0 | this week (s1) | facts.toml fix + lint, syllabus-true facts, Canvas sync both sections, persona, starter prompts | unchanged; **blocked on**: grading table, SQL scope, section topology, persona name |
| 1 | by s3 | `read_code` with cut-list policy + Excel anchors; Tier B rebuilt with `debut_session` | unchanged |
| 2 | by s7 | drill door + bank-as-byproduct pipeline (§2.5), conditions toggle, handle-based ledger (§2.2) | bank repriced; identity lightened |
| 3 | by s15 | `attack_spec` with student-exported transcript (§2.3); portfolio exports | evidence model inverted |
| 4 | by s24/s26 | s26 agent-run + audit scaffold (§2.4); defense rehearsal if capacity allows | planted-flaw generation dropped |
| — | continuous | weekly golden-set run + §3 metrics in the weekly report | new |

## 5 · Standing risks the revision does not remove

The companion still competes with free frontier chat for explain/debug traffic, and should not pretend otherwise — its moat is curated wrongness, course grounding, and zero setup, and the syllabus framing should say so plainly. Streamlit hosting at ~120 students needs a real deployment target, not Community Cloud [Guessing on current hosting plan — unverified]. And Phase 0 remains blocked on the four open decisions above; every week they stay open, the TA either abstains on facts questions or asserts a stale syllabus.
