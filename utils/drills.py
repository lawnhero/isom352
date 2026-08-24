"""Verification drills: the artifact bank, session gating, and drill state.

WHY THIS EXISTS

    The signature assessed skill of ISOM 352 -- 25% of the grade -- is
    locate / explain-in-business-English / sign-or-don't-sign on a fluent,
    flawed analytics artifact. `generate_practice` free-generates
    compute-and-interpret questions, which drills the wrong exam. This module
    serves ENGINEERED artifacts instead: real code, really executed on a
    known master, with a documented recipe as provenance.

THE RULES THIS MODULE ENFORCES (course rules B3 / D3 / E1)

    B3 -- a planted flaw must run without error, produce plausible output,
    and be findable from what has been taught. So: artifacts are loaded from
    the bank, never generated at request time; every drill carries executed
    output and a recipe provenance; and `eligible()` gates on
    `debut_session` so a week-3 student is never drilled on leakage.

    D3 -- wherever students hunt flaws, clean-with-caveats material exists
    too. So: `status: "clean"` drills are first-class citizens, `select()`
    keeps them in rotation, and a false alarm on one is a recorded outcome,
    not a shrug.

    E1 -- individual skill is measured in the room; this ledger is formative
    only. The hard outcomes (verdict correct, false alarm, miss) are computed
    in Python from the student's own button click, logged per self-asserted
    handle, and never surface at individual grain outside the student's own
    session.

WHO WRITES WHAT

    Like utils/practice.py: pure dict functions, no Streamlit import. app.py
    owns the session state and the ledger write; chains_lcel grades AROUND
    the artifact; nothing here calls a model.

    The bank itself is written only by scripts/build_drills.py from recipe
    files -- never by hand, never by an LLM. See course_data/drills/README.md.
"""

import json
import random
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DRILLS_DIR = Path("course_data/drills")

STATUSES = ("dirty", "clean")
CONDITIONS = ("lab", "exam")

# Lab conditions allow nudges; after this many the student should submit a
# verdict rather than collect a third hint. Exam conditions allow none.
MAX_DRILL_HINTS = 2

# One clean control roughly every third drill. D3: a bank served 100% dirty
# teaches crying wolf; a student who has just seen two dirty artifacts in a
# row is due a clean one.
CLEAN_EVERY = 3

_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
DEFAULT_CLASS_DAYS = ("tue", "thu")


# --------------------------------------------------------------------------
# Bank loading and validation
# --------------------------------------------------------------------------
def validate(drill: Dict[str, Any]) -> List[str]:
    """Reasons this drill may not be served, empty when it is valid.

    Structural enforcement of the bank's contract: a drill with no executed
    output cannot satisfy B3's "plausible output", and one with no recipe in
    its provenance is by definition hand-made, which the course rules forbid.
    """
    errors = []
    for field in ("id", "disease", "disease_label", "status", "artifact", "answer_key"):
        if not drill.get(field):
            errors.append(f"missing {field}")
    if drill.get("status") not in STATUSES:
        errors.append(f"status must be one of {STATUSES}")
    if not isinstance(drill.get("debut_session"), int) or drill.get("debut_session", 0) < 1:
        errors.append("debut_session must be an int >= 1")

    artifact = drill.get("artifact") or {}
    if not (artifact.get("code") or "").strip():
        errors.append("artifact.code is empty")
    if not (artifact.get("output") or "").strip():
        errors.append("artifact.output is empty (B3: output must exist and look plausible)")

    key = drill.get("answer_key") or {}
    if drill.get("status") == "dirty":
        if key.get("verdict") != "dont_sign":
            errors.append("dirty drill must have verdict 'dont_sign'")
        for field in ("flaw", "mechanism", "consequence"):
            if not (key.get(field) or "").strip():
                errors.append(f"dirty drill missing answer_key.{field}")
    elif drill.get("status") == "clean":
        if key.get("verdict") != "sign":
            errors.append("clean drill must have verdict 'sign'")

    if not ((drill.get("provenance") or {}).get("recipe") or "").strip():
        errors.append("provenance.recipe is required (drills are engineered, never hand-made)")
    return errors


def load_bank(
    drills_dir: Path = DRILLS_DIR, *, include_demo: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """All valid drills, plus one human-readable line per file skipped.

    Demo drills (spine == "demo") exist so the door can be exercised before
    the first spine-based drills are built; they are development fixtures and
    never reach students unless diagnostics are unlocked.
    """
    drills, problems = [], []
    directory = Path(drills_dir)
    if not directory.is_dir():
        return drills, problems
    for path in sorted(directory.glob("*.json")):
        try:
            drill = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            problems.append(f"{path.name}: unreadable ({exc})")
            continue
        errors = validate(drill)
        if errors:
            problems.append(f"{path.name}: {'; '.join(errors)}")
            continue
        if drill.get("spine") == "demo" and not include_demo:
            continue
        drills.append(drill)
    return drills, problems


# --------------------------------------------------------------------------
# Session gating (B3: findable from what has been taught SO FAR)
# --------------------------------------------------------------------------
def current_session(facts: Optional[Dict[str, Any]], today: Optional[date] = None) -> int:
    """Which class session number today falls on (1-based), conservatively.

    Counts class meetings from `[schedule] first_class` in facts.toml at the
    configured cadence (default Tue/Thu). Unconfigured or pre-term returns 1:
    when the app cannot know what has been taught, it assumes almost nothing
    has, which can under-serve drills but can never violate B3.
    """
    today = today or date.today()
    schedule = (facts or {}).get("schedule") or {}
    first = schedule.get("first_class")
    if isinstance(first, datetime):
        first = first.date()
    elif isinstance(first, str):
        try:
            first = date.fromisoformat(first.strip())
        except ValueError:
            first = None
    if not isinstance(first, date):
        return 1

    day_names = schedule.get("class_days") or list(DEFAULT_CLASS_DAYS)
    class_days = {_WEEKDAYS[d.strip().lower()[:3]] for d in day_names if d.strip().lower()[:3] in _WEEKDAYS}
    if not class_days or today < first:
        return 1

    sessions = 0
    span_days = (today - first).days
    for offset in range(span_days + 1):
        weekday = (first.weekday() + offset) % 7
        if weekday in class_days:
            sessions += 1
    return max(sessions, 1)


def eligible(bank: List[Dict[str, Any]], session: int) -> List[Dict[str, Any]]:
    """Drills whose disease has debuted by the given session."""
    return [d for d in bank if int(d.get("debut_session", 0)) <= session]


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------
def select(
    bank: List[Dict[str, Any]],
    session: int,
    history: Optional[List[Dict[str, Any]]] = None,
    rng: Optional[random.Random] = None,
) -> Optional[Dict[str, Any]]:
    """Pick the next drill, or None when nothing is eligible.

    `history` is the student's ledger, most recent last: dicts with at least
    `drill_id`, `disease`, `status`. Preferences, in order:

    1. A clean control when the last CLEAN_EVERY-1 graded drills were all
       dirty (D3: calibration is half the skill).
    2. The least-practised disease, so drilling spreads across the taxonomy
       instead of grooving one topic.
    3. Within that, a drill id the student has not seen; repeats only when
       every variant is spent.
    """
    history = history or []
    rng = rng or random.Random()
    pool = eligible(bank, session)
    if not pool:
        return None

    recent = history[-(CLEAN_EVERY - 1):]
    want_clean = (
        len(recent) == CLEAN_EVERY - 1
        and all(row.get("status") == "dirty" for row in recent)
        and any(d["status"] == "clean" for d in pool)
    )
    if want_clean:
        pool = [d for d in pool if d["status"] == "clean"]

    practised = {}
    for row in history:
        practised[row.get("disease")] = practised.get(row.get("disease"), 0) + 1
    least = min(practised.get(d["disease"], 0) for d in pool)
    pool = [d for d in pool if practised.get(d["disease"], 0) == least]

    seen_ids = {row.get("drill_id") for row in history}
    unseen = [d for d in pool if d["id"] not in seen_ids]
    return rng.choice(unseen or pool)


# --------------------------------------------------------------------------
# Drill session state (mirrors utils/practice.py)
# --------------------------------------------------------------------------
def start(drill: Dict[str, Any], conditions: str = "lab") -> Dict[str, Any]:
    return {
        "drill": drill,
        "conditions": conditions if conditions in CONDITIONS else "lab",
        "hints_given": 0,
        # The student's button click, held until their written explanation
        # arrives: "sign" | "dont_sign" | "".
        "verdict": "",
        "graded": False,
    }


def is_active(session: Optional[Dict[str, Any]]) -> bool:
    return bool(session and session.get("drill"))


def drill_of(session: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return (session or {}).get("drill") or {}


def record_hint(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if is_active(session):
        session["hints_given"] = int(session.get("hints_given") or 0) + 1
    return session


def hints_left(session: Optional[Dict[str, Any]]) -> int:
    """Hints remaining, honouring conditions: exam conditions allow none."""
    if not is_active(session) or session.get("conditions") == "exam":
        return 0
    return max(MAX_DRILL_HINTS - int(session.get("hints_given") or 0), 0)


def score(session: Dict[str, Any]) -> Dict[str, Any]:
    """The hard outcomes, computed from the click -- no model in the loop.

    A false alarm is refusing to sign clean work; a miss is signing flawed
    work. These are the two numbers the calibration curve in the weekly
    report is made of, so they must not depend on parsing model prose.
    """
    drill = drill_of(session)
    truth = (drill.get("answer_key") or {}).get("verdict") or ""
    verdict = session.get("verdict") or ""
    return {
        "drill_id": drill.get("id", ""),
        "disease": drill.get("disease", ""),
        "status": drill.get("status", ""),
        "conditions": session.get("conditions", ""),
        "verdict": verdict,
        "verdict_correct": bool(verdict) and verdict == truth,
        "false_alarm": drill.get("status") == "clean" and verdict == "dont_sign",
        "miss": drill.get("status") == "dirty" and verdict == "sign",
        "hints_given": int(session.get("hints_given") or 0),
    }


# --------------------------------------------------------------------------
# Prompt / display blocks
# --------------------------------------------------------------------------
def artifact_markdown(session: Dict[str, Any]) -> str:
    """The drill as the student sees it. Never names the disease -- naming
    "silent row loss" on the artifact does the locating for them."""
    drill = drill_of(session)
    artifact = drill.get("artifact") or {}
    conditions = session.get("conditions", "lab")
    header = (
        "**Verification drill** · "
        + ("lab conditions — field guide open, hints allowed"
           if conditions == "lab"
           else "exam conditions — no guide, no hints")
    )
    return (
        f"{header}\n\n"
        "An analyst produced this. It ran without errors. Decide whether you "
        "would **sign it** — put your name on the number — or **not sign it**.\n"
        "If you would not sign: name where it goes wrong and say, in business "
        "English, what the mistake is and what acting on the number would cost.\n"
        "If you would sign: say what you checked before trusting it.\n\n"
        f"```python\n{artifact.get('code', '').strip()}\n```\n"
        f"Output:\n```\n{artifact.get('output', '').strip()}\n```"
    )


def answer_key_block(drill: Dict[str, Any]) -> str:
    """The key, rendered for the grading prompt (never for the student
    directly -- the grading chain decides what feedback reveals)."""
    key = drill.get("answer_key") or {}
    lines = [
        f"Status: {drill.get('status', '')}",
        f"Disease: {drill.get('disease_label', '')}",
        f"Correct verdict: {'SIGN — the work is sound' if key.get('verdict') == 'sign' else 'DO NOT SIGN'}",
    ]
    if (key.get("flaw") or "").strip():
        lines.append(f"The flaw: {key['flaw']}")
    if (key.get("mechanism") or "").strip():
        lines.append(f"Mechanism: {key['mechanism']}")
    if (key.get("consequence") or "").strip():
        lines.append(f"Consequence of acting on it: {key['consequence']}")
    caveats = [c for c in (key.get("caveats") or []) if (c or "").strip()]
    if caveats:
        lines.append("Honest caveats a careful signer would note:")
        lines.extend(f"  - {c}" for c in caveats)
    return "\n".join(lines)
