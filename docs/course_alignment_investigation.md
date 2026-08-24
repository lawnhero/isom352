# Virtual TA × ISOM 352 redesign — investigation report

*2026-08-24 · investigation only, nothing implemented. Repo state examined: branch `revamp-550-fork`, the fork of the ISOM 550 tutor described in `README.md`.*

---

## 1 · What the repo is today

The architecture is sound and largely course-agnostic: one tool-calling router (`utils/router.py`) dispatches to seven tools (`utils/ta_tools.py`), each of which prepares a streamed answer chain (`utils/chains_lcel.py`) over three tiers of course knowledge — Tier A hand-written facts (`facts.toml` + synced `schedule.json`), Tier B a concept index built from `concepts.csv`, Tier C Canvas documents. Retrieval abstains instead of guessing; a held practice-question session survives the chat window; hint-coaching escalates to a worked step after three hints; everything is logged to MongoDB with a weekly-report script. `?debug=1` gives instructor diagnostics.

[Certain] The course *surface* is still ISOM 550: the router persona is "Dayton, the Virtual TA for ISOM 550"; the software tool answers JMP/Excel menu paths; `concepts.csv` (113 rows) is the 550 seed — JMP fit reports, decision trees, data tables, TreePlan; starter prompts reference "regression in JMP". The README's own checklist says exactly this.

## 2 · Defects found during investigation

**`facts.toml` does not parse.** [Certain — reproduced with `tomllib`] Line 62 closes `late_policy` with `""` instead of `"""`, so parsing fails at line 64. `course_context.load()` swallows `TOMLDecodeError` and returns `facts = None`, which means **Tier A is silently empty right now**: every question about office hours, grading, materials, or policies abstains, and the office-hours starter prompt fails on first click. The edits made 8/23 broke the file. One-character fix, but it demonstrates a design gap: a hand-maintained file whose parse failure is silent needs a loud failure path (banner in `?debug=1`, or a lint in `sync_canvas.py`/CI).

**The grading table contradicts the settled course design.** [Certain that they conflict; open which is authoritative] `facts.toml` says HW 15 / In-class 10 / Quizzes 10 / Midterm 25 / Final 30 / Participation 10. The settled design says cycle-1 15 · cycle-2 15 · final + defense 20 · exams 25 · portfolio 15 · peer 10 — no midterm/final pair, no quizzes, and Exam 2 is cut. If the TA states the `facts.toml` table to students, it asserts a grading scheme the course doesn't have. This looks pasted from an older syllabus. **Do not fill further TODOs until the Fall 2026 syllabus is the single source.**

**Scope contradiction: SQL and the toolchain.** [Likely a stale paste, but genuinely ambiguous] `facts.toml` lists AWS MySQL, the Learning SQL textbook, and conventions naming beautifulsoup/statsmodels/scikit-learn. The course design's in-scope list is variables, types, booleans, for loops, dicts, functions, pandas — yet the disease taxonomy contains "SQL-specific: NULL surprise" and "Joins (pandas + SQL)". Either SQL survived the redesign in a reading-only role, or the taxonomy rows and the toolchain block are both stale. This decides whether the TA's code tool must read SQL at all. Flagged, not assumed.

**Persona split.** [Certain] Router says Dayton/550; `facts.toml` says "Virtual TA Peyton". Trivial, but it will leak to students on the first no-tool turn.

## 3 · The central redesign argument

The README's re-pointing plan (fill facts, swap concepts, sync Canvas, rename persona, add `debug_code`) treats this as a **content swap**. I disagree that a content swap is sufficient, because the course redesign changes what a TA is *for*. The 550 TA is an answer-explainer: it tells you what R² means and coaches you to compute-and-interpret. ISOM 352's thesis is that explanation and code generation are exactly what students already have infinite free access to — the defensible skills are verification, specification, code reading, and signing the number. A TA that only explains and debugs is a slightly worse version of the tools the course teaches students to distrust. The risk in the content-swap approach is that you ship a fluent generic tutor that actively pulls against the course: students outsource reading to it, and the practice it generates drills the wrong exam.

What the fork gets right, and should keep unchanged: the abstain-don't-guess retrieval posture (it *models* the course thesis), the facts/documents/schedule machinery, the held-question session state, the hint-escalation policy, the compound-turn design, and the logging spine. The redesign is concentrated in four places.

### 3.1 Practice engine → verification drills (highest value)

Current `practice_chain` free-generates compute-and-interpret questions. The signature assessed skill — 25% of the grade — is locate / explain-in-business-English / sign-or-don't-sign on a fluent flawed artifact. The TA should drill exactly that: serve a short code+output artifact with one planted disease from the 18-topic taxonomy; the student names the flaw; `coach_practice` escalates hint → locate → explain → consequence (the exam's own tiers, replacing the current easier/same/harder ladder for this mode); `check_attempt` grades the sign/don't-sign call *and the checking sentence* (rule C3 — one sentence, graded, so students rehearse it all term).

Two design constraints follow from the course rules, and both argue against free generation of drill artifacts:

- Flaws must run, look plausible, and be findable from what's been taught (B3). An LLM generating a flawed snippet per request can't guarantee any of the three. The item bank should be **engineered, not generated**: the `dirt_injection.py` pattern already in the course project is the right factory — curated recipes per disease, applied to the teaching spines, with the artifact (code + real output) stored, and the LLM used only for coaching *around* a verified artifact.
- Calibration is half the skill (D3): the bank must contain clean-with-caveats artifacts too, and correctly certifying clean work must be a passing answer. A drill bank that is 100% dirty teaches crying wolf.

Mechanically this is cheap: the held-session machinery (`practice.py`) carries over nearly unchanged; the drill is just a question whose text is an artifact and whose grading rubric is locate/explain/sign.

### 3.2 Tier B → the concept map + field guide, gated by session

Replace the 550 seed with two row families: (a) the 352 concept map (the five Python doses, pandas constructs, the inference and ML concepts actually in scope), keeping the schema — `managerial_phrasing` maps to the ledger-sentence/business-English discipline, and `common_mistake` is where each disease's mechanism-plus-detection-test lives; (b) one row per field-guide disease (18 headliners + secondaries), so `answer_concept` can answer "what is leakage" in the course's own framing and `generate_practice` can ground drills on it.

Add one column the 550 schema lacks: **`debut_session`**. "Findable from what has been taught" is a hard rule; the TA currently has no notion of course progress. Gate concept retrieval and drill selection on the current session number (derivable from `schedule.json`, which `course_context` already parses for its span). Without this, in week 3 the TA will happily drill leakage — a cycle-2 disease — and explain constructs from the cut list.

The cut list itself belongs in the prompts as policy, not just absent from the index: *while, try/except, OOP, .loc/.iloc, comprehensions* are cut-and-stay-cut, but agent-generated code students paste will be full of them. Rule: the TA answers in the course subset; when a pasted snippet uses an out-of-scope construct it names it, translates it to the in-scope equivalent where one exists, and says "Recipe 🔧 — you're not expected to write this" where one doesn't. The Understand-vs-Recipe two-tier convention should be the code-explanation output format.

### 3.3 `answer_software` → `read_code` (+ a narrower `debug_code` than planned)

Challenge to the stated feature list: "debug code" is the generic-TA framing. In this course students mostly won't be *writing* the code that breaks — they'll be reading agent output, and their Do-beat code starts from code already on screen. The higher-value tool is **`read_code`**: paste a cell → line-by-line business-English reading, two-tier format, Excel anchors where twins exist (mask ↔ filter, groupby ↔ pivot), out-of-scope constructs flagged per above. Debugging should exist but coach traceback-*reading* first (bottom line first, name the line, say what the message claims in business English, then the fix) rather than emitting corrected code — a TA that silently returns fixed code trains paste-and-pray. The JMP/Excel `software_context` block becomes Python/Colab/pandas conventions carrying the cut list; the existing "never invent a menu path" honesty rule has a clean analog: never invent an API or argument.

### 3.4 The TA as a named AI relationship (norms, adversary mode, integrity)

The TA is itself the AI students meet, so it must model the norms it lives under, visibly. Three concrete pieces:

- **Norm signage, not enforcement.** The TA can't know which beat a student is in, so per-beat prohibition is unenforceable — don't pretend otherwise. Instead: the onboarding dialog states where the TA sits in the four relationships, every substantive answer footer reminds that using it on an artifact means disclosure + a checking sentence, and Read-&-Predict-style questions during class time are met with a nudge, not a refusal. [Likely the right call; enforcement theater would be discovered and mocked.]
- **An explicit adversary mode.** Ask-stage rules require AI to attack the team's question draft (C1). A new tool — `attack_spec`: paste the draft question/spec, get an adversarial critique hunting the framing diseases (undefined outcome, dataset-first drift) plus feasibility pressure. Hosting the adversary pass inside the TA makes it *loggable*: the instructor gets evidence per team that the pass happened before the s16 scoping meeting, and the transcript is portfolio material. This is the one genuinely new capability the course design demands that the 550 architecture has no seat for.
- **Refusal boundary and exam integrity.** SHARED_POLICY gains: never produce a complete analysis for a graded deliverable (offer the reading/verification framing instead — and note the asymmetry: free agents will do this anyway, so the value is the TA *saying why it won't*, which is the thesis restated). Keep exam bodies, the exam flaw lists, and the exam-spec doc out of the Tier C sync allowlist; drills use the spines, exams stay unseen and un-famous.

## 4 · Smaller alignments

**Tier C / Canvas.** Sync the 352 course id(s) and build the documents index; until then date questions abstain (correct behavior, already designed). Two sections (165126 / 165131 per README; facts.toml lists 1101 + 1102) is an unresolved question that decides whether you run one deployment with section-aware facts or two synced course ids. The schedule-reliability advisory machinery carries over untouched and is worth keeping exactly as is.

**Starter prompts and chips.** Rewrite to teach the 352 routes on first click: an office-hours fact, a "what did we cover" recap, a `read_code` invitation ("paste a cell you can't read"), and — the differentiator — "Give me a verification drill." Every starter must be answerable from current course data (the repo's own hard-learned rule); today several would abstain.

**Instrumentation.** The build backlog lists an instrumentation plan as still-to-build. The TA's MongoDB log is that plan's natural substrate: tag drill events with disease ids and outcomes, and `generate_weekly_report.py` becomes per-disease hit/miss rates — direct input to the s25 triage session and exam calibration. This is the strongest instructor-side reason to build the drill bank keyed to taxonomy ids rather than free-text topics.

**Feasibility.** [Guessing on load, but the shape is right] ~120 students × a light DeepSeek-first model stack is the cheap part; the real capacity question is the drill bank (18 topics × a few artifacts each × clean controls ≈ 60–80 curated artifacts). Generating them from dirt-script recipes on the spines amortizes work the course project already does for sessions and exams — same recipes, three consumers.

## 5 · What I'd do first (ordering, not implementation)

1. Fix and lint `facts.toml`; add a loud parse-failure path. Then resolve the grading table and SQL/toolchain contradictions against the Fall 2026 syllabus before filling any TODO.
2. Rebuild `concepts.csv` from the concept map + field guide with `debut_session`; re-index; re-calibrate retrieval thresholds (the calibration script exists).
3. Re-point prompts/persona/UI (the README's step 4) — but to the *roles* in §3, not just find-replace JMP→Python.
4. Build the verification-drill bank + drill mode (§3.1) — the highest-value, highest-effort item, and the one worth doing before `read_code` polish because it's what no free tool gives students.
5. `attack_spec` before s15; it has a hard calendar deadline (scoping meeting is s16).

## 6 · Open questions (ask, don't assume)

1. Which grading table is authoritative — and does `facts.toml` get the settled six-category scheme now, or wait for the final syllabus?
2. Is SQL in Fall 2026 scope in any form (reading-only? cut entirely?), given the taxonomy's SQL rows vs. the concept map's silence?
3. Persona: is "Peyton" the decided name?
4. Drill-bank sourcing: bless reusing `dirt_injection.py` recipes on the teaching spines as the artifact factory?
5. Session gating: should the TA hard-refuse to drill un-debuted diseases, or serve them with a "not yet covered" label? (Hard gate matches B3; the label is friendlier near exam review.)
6. Adversary logs: are `attack_spec` transcripts *evidence* (instructor-visible per team) or *practice* (private)? This changes what students will honestly paste into it.
