# CLAUDE.md — ISOM 352 Virtual TA (Peyton)

Virtual TA for **ISOM 352: Applied Data Analytics with Coding**, Emory BBA, Fall 2026.
Streamlit app, forked from the ISOM 550 tutor. Architecture (router → 7 tools →
streamed chains → 3 knowledge tiers) is documented in `docs/dev_reference.md` and
is accurate for this repo.

**Read before designing anything:**
- `docs/course_alignment_investigation.md` — repo-vs-course gap analysis
- `docs/vta_companion_design_v2.md` — the validated redesign (roles, phases, metrics)

Those docs cite course rules by ID (B3, C1–C3, D1–D3, E1, S20). The IDs are defined
in the instructor's course-design project, not in this repo — the section below is
the self-contained summary an implementation session needs.

---

## The course this TA serves (background you must not contradict)

**Thesis.** LLMs removed the bottleneck of writing analytics code. What stays
defensible: verification, specification, code literacy (reading, not writing),
and accountability for the number. Agent output is fluent, plausible, and wrong
in ways only a capable reader catches. Students graduate able to *sign the number*.
The TA exists to serve this thesis — it is not a homework solver.

**Architecture.** One cycle — Ask → Acquire → Analyze → Answer — run twice over
28 sessions of 75 min. Cycle 1 (s1–14): guided, statistical inference, real-estate
spine (`eastville.csv`, 108 homes); Verification Exam 1 at s14. Cycle 2 (s15–28):
teams' own questions, prediction/ML, loan-default spine (~149K loans, risk-desk
framing, dollarized error costs); s23 lab 2 · s25 triage · s26 agentic session ·
s27–28 presentations + defense. SQL appears in the cycle-2 Acquire stage.

**Session rhythm** (six beats, 75 min): Where are we (5) · Read & Predict (10,
screens down, AI forbidden) · Teach (15, ≤2 new ideas) · Do (25) · Verify (10) ·
So what (5, one ledger sentence in business English). Every default session
plants one findable flaw in Verify.

**Python is a reading language.** In scope: variables, types, booleans, for
loops, dicts, functions, pandas. **Cut and stays cut: `while`, `try/except`, OOP,
`.loc`/`.iloc`, comprehensions, boosting/SVM/neural nets.** Models: logistic,
decision tree, random forest. Excel anchors where twins exist (filter → mask,
pivot → groupby, trendline → regression). Notebooks are two-tier: **Understand**
vs **Recipe 🔧** ("you're not expected to understand every character").
→ *Any code the TA emits or explains must respect this subset; when a student
pastes out-of-scope constructs, name them, translate to the in-scope equivalent
where one exists, label Recipe 🔧 where none does.*

**AI norms (the rules students live under):**
- **C1** — norms are per-beat, never blanket. Students meet AI in four named
  relationships: *forbidden* (Read & Predict), *assistant* (with disclosure),
  *adversary* (attacks their drafts), *auditee* (they audit AI output).
  Choosing the mode is itself the judgment being taught.
- **C2** — disclosure is never penalized; non-disclosure is an integrity issue.
- **C3** — every AI-assisted artifact carries one graded "checking sentence":
  what we checked before trusting it.

**Disease taxonomy** (18 topics, one headline trap each — the backbone of drills,
the field guide, and the exam; `common_mistake` rows in `concepts.csv` map here):

| Topic | Headline trap |
|---|---|
| Framing | Undefined outcome |
| Loading files | Type confusion |
| Cleaning/manipulation | Silent row loss |
| Joins (pandas + SQL) | Fan-out duplication |
| Aggregation/groupby | Small-group extremes |
| 1-variable description | Mean under skew |
| 2-variable comparison | Confounded gap |
| Visualization | Truncated axis |
| Correlation/simple regression | Correlation-as-causation |
| Multiple regression | Coefficient misreading |
| API/web acquisition | Partial pull treated as complete |
| SQL-specific | NULL surprise |
| LLM-as-extractor | Confident misextraction |
| Logistic regression | Threshold naïveté |
| Train/test discipline | Leakage |
| Model comparison | Test-set shopping |
| Model evaluation | Accuracy on imbalance |
| Answering | Overclaiming |

**Rules that constrain this app directly:**
- **B3** — a planted flaw must (a) run without error, (b) produce plausible
  output, (c) be findable from what has been taught so far. → *Drill artifacts
  are engineered from clean masters via dirt-script recipes, never free-generated
  by an LLM at request time; never drill a disease that hasn't debuted yet
  (`debut_session` gating).*
- **D3** — wherever students hunt flaws, clean-with-caveats material exists too;
  false positives cost, certifying clean work earns. → *The drill bank contains
  clean controls; calibration is scored.*
- **D1** — the field guide is allowed in verification labs, not exams. → *Drills
  offer lab-conditions vs exam-conditions.*
- **E1** — individual skill is measured in the room; take-home artifacts are
  never evidence of individual skill. → *This TA is constitutionally formative:
  its logs and ledgers must never become grading evidence; lightweight
  self-asserted identity is sufficient and intentional.*
- **E3** — exams are verification exams on unseen, un-famous datasets.
  → *Never index exam bodies, exam flaw lists, or the exam spec into any tier.*

**Grading (Fall 2026 syllabus, final):** Cycle 1 15% · Cycle 2 15% · Rhythm
portfolio 10% · Participation Quizzes 5% · Peer/process eval 5% · Verification
Exam 1 25% · Final Group Project 25%. **There is no Exam 2.**

---

## Current status & phase plan (2026-08-24)

Done: `facts.toml` filled and verified against the Fall 2026 syllabus (parses,
sums to 100). Canvas topology settled: **one shell, 165126** — section 1102
(165131) is cross-listed into it; sync 165126 only.

**Phase 0 (done 2026-08-24):** persona re-pointed Dayton→Peyton across router,
chains, tools, UI, sidebar, app greeting; software route rewritten JMP/Excel →
Python/Colab (cut-list line in the prompt, "never invent an API" rule); starter
prompts rewritten, each verified answerable from current course data; synced
165126 → built Tier C (1 chunk — term hasn't started) → built Tier B from the
550-seed `concepts.csv` (46 chunks; Phase 1 replaces it) → probe clean (margin
0.362, abstain 1.58). Smoke turn verified end-to-end. Outstanding: "Semester
Start Pulse Check" in Canvas carries a stale 2025 due date — fix in Canvas,
re-sync.

**Phase 1 (by s3):** `read_code` tool (two-tier reading, cut-list policy, Excel
anchors); rebuild `concepts.csv` from the 352 concept map + disease taxonomy with
a `debut_session` column; re-index Tier B.

**Phase 2 (infrastructure done 2026-08-24; content awaits session builds):**
drill door shipped — modal, router-free (`utils/drills.py`, drill chains in
`chains_lcel.py`, door flow in `app.py`); sign/don't-sign verdict is a button
click so verdict-correct / false-alarm / miss are computed in Python, never
parsed from model prose; lab/exam conditions toggle (exam = no hints);
handle-based ledger as `event_type: "drill"` Mongo events (formative only,
E1); bank format + validation in `course_data/drills/README.md`; factory is
`scripts/build_drills.py` + `drill_recipes/*.py` — executes recipe code on a
clean master, real output stored, B3 enforced structurally. Three demo drills
(spine "demo", students never see them; visible under `?debug=1`) verified
end-to-end in the browser: serve, hint, correct-locate debrief, miss debrief,
ledger writes. **Blocked on content:** the eastville master + per-session
dirt recipes (each session's trap exports 1–2 variants + a clean control),
and `first_class` in facts.toml `[schedule]` (commented template; unset, the
gate conservatively assumes session 1 and serves nothing). Phase 1
(`read_code`, concepts.csv rebuild) was deliberately skipped past — still
open.

**Phase 3 (by s15):** `attack_spec` adversary tool — ends by exporting a
transcript artifact the *team* attaches to scoping materials (export, don't
surveil). Portfolio exports (disclosure line + checking sentence).

**Phase 4 (by s24/s26):** s26 agent-run + audit scaffold (organic flaws, no
planting); defense-rehearsal mode if capacity allows.

Continuous: weekly golden-set regression via `scripts/smoke_turn.py`; metrics
per `docs/vta_companion_design_v2.md` §3.

---

## Working rules for this repo

- **Verify numbers in data before asserting them.** Any figure the TA's prompts,
  seeds, or docs state gets computed on the actual file first. No invented figures.
- **Traps/drills come from documented dirt scripts on clean masters**, never
  hand-edited artifacts.
- `course_data/facts.toml` is hand-maintained and human-owned; sync never touches
  it. **Lint it after every edit** (`python -c "import tomllib; tomllib.load(open('course_data/facts.toml','rb'))"`) —
  a parse failure is swallowed silently by `course_context.load()` and empties
  Tier A without warning. (This happened; a loud failure path is wanted.)
- Retrieval abstains instead of guessing — preserve this posture in any new tool.
- The router is a dispatcher, not a writer; tools return receipts, chains write
  the answer. Don't collapse this.
- Run `python -m pytest tests -q` (no keys needed) before and after changes;
  `python scripts/smoke_turn.py "..."` for one real turn (needs `.env` keys).
- Open design decisions get flagged and asked, never silently resolved.

## Commands

```bash
pip install -r requirements.txt
streamlit run app.py                      # needs .env: MONGODB_URI, OPENAI_API_KEY, DEEPSEEK_API_KEY
python -m pytest tests -q                 # no keys or index needed
python scripts/smoke_turn.py "hi"         # one real headless turn
python scripts/sync_canvas.py --course-id 165126
python scripts/build_documents.py         # Tier C index
python scripts/build_concepts.py --dry-run  # lint concepts.csv, then run without flag
python scripts/calibrate_retrieval.py --probe
```

Add `?debug=1` to the app URL for instructor diagnostics.
