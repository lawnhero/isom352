"""The drill bank contract, session gating, selection, and scoring.

The rules under test are course rules, not implementation details: B3 (a
drill runs, looks plausible, and is findable from what has been taught),
D3 (clean controls stay in rotation and calibration is scored), and the
repo rule that drills are engineered from recipes, never hand-made.
"""

import json
import random
from datetime import date

import pytest

from utils import drills


def _dirty(**overrides):
    drill = {
        "id": "cleaning-silent-row-loss-demo-01",
        "disease": "cleaning-silent-row-loss",
        "disease_label": "Cleaning — Silent row loss",
        "status": "dirty",
        "debut_session": 3,
        "spine": "eastville",
        "artifact": {"code": "print(len(df))", "output": "90"},
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": "dropna() removes rows the analysis never decided to drop.",
            "mechanism": "Row-level filter on every column at once.",
            "consequence": "The average covers a subset nobody chose.",
            "caveats": [],
        },
        "provenance": {"recipe": "drill_recipes/x.py", "master": "m.csv", "built_at": "t"},
    }
    drill.update(overrides)
    return drill


def _clean(**overrides):
    drill = _dirty(
        id="aggregation-clean-demo-01",
        disease="aggregation-small-group-extremes",
        status="clean",
        answer_key={
            "verdict": "sign",
            "flaw": "",
            "mechanism": "Counts shown, column complete, claim matches computation.",
            "consequence": "",
            "caveats": ["Averages hide spread."],
        },
    )
    drill.update(overrides)
    return drill


# ---- validation ------------------------------------------------------------
def test_valid_drills_pass():
    assert drills.validate(_dirty()) == []
    assert drills.validate(_clean()) == []


def test_b3_output_must_exist():
    bad = _dirty()
    bad["artifact"]["output"] = "  "
    assert any("output" in e for e in drills.validate(bad))


def test_hand_made_drills_are_rejected():
    bad = _dirty()
    bad["provenance"] = {"recipe": ""}
    assert any("engineered" in e for e in drills.validate(bad))


def test_verdict_must_match_status():
    assert any("dont_sign" in e for e in drills.validate(_dirty(answer_key={
        "verdict": "sign", "flaw": "x", "mechanism": "y", "consequence": "z"})))
    wrong_clean = _clean()
    wrong_clean["answer_key"]["verdict"] = "dont_sign"
    assert any("sign" in e for e in drills.validate(wrong_clean))


def test_dirty_needs_a_complete_key():
    bad = _dirty()
    bad["answer_key"]["mechanism"] = ""
    assert any("mechanism" in e for e in drills.validate(bad))


# ---- bank loading ----------------------------------------------------------
def test_load_bank_skips_invalid_files_with_reasons(tmp_path):
    (tmp_path / "good.json").write_text(json.dumps(_dirty()), encoding="utf-8")
    bad = _dirty(id="bad")
    bad["artifact"]["output"] = ""
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    bank, problems = drills.load_bank(tmp_path)
    assert [d["id"] for d in bank] == ["cleaning-silent-row-loss-demo-01"]
    assert len(problems) == 2


def test_demo_spine_is_hidden_from_students(tmp_path):
    (tmp_path / "demo.json").write_text(json.dumps(_dirty(spine="demo")), encoding="utf-8")
    assert drills.load_bank(tmp_path)[0] == []
    assert len(drills.load_bank(tmp_path, include_demo=True)[0]) == 1


def test_shipped_demo_bank_is_valid():
    """The checked-in drills must always validate; a bad build fails here."""
    bank, problems = drills.load_bank(include_demo=True)
    assert problems == []
    assert len(bank) >= 3
    assert any(d["status"] == "clean" for d in bank), "D3: bank needs clean controls"


# ---- session gating (B3) ---------------------------------------------------
def test_current_session_unconfigured_is_conservative():
    assert drills.current_session(None) == 1
    assert drills.current_session({}) == 1
    assert drills.current_session({"schedule": {"first_class": "not-a-date"}}) == 1


def test_current_session_counts_class_meetings():
    facts = {"schedule": {"first_class": "2026-08-25"}}  # a Tuesday, Tue/Thu default
    assert drills.current_session(facts, today=date(2026, 8, 24)) == 1   # pre-term
    assert drills.current_session(facts, today=date(2026, 8, 25)) == 1
    assert drills.current_session(facts, today=date(2026, 8, 27)) == 2
    assert drills.current_session(facts, today=date(2026, 8, 31)) == 2   # Monday
    assert drills.current_session(facts, today=date(2026, 9, 3)) == 4


def test_eligible_gates_on_debut_session():
    bank = [_dirty(debut_session=3), _clean(debut_session=5)]
    assert [d["debut_session"] for d in drills.eligible(bank, 3)] == [3]
    assert len(drills.eligible(bank, 5)) == 2
    assert drills.eligible(bank, 1) == []


# ---- selection (D3) --------------------------------------------------------
def test_select_returns_none_when_nothing_has_debuted():
    assert drills.select([_dirty(debut_session=9)], session=3) is None


def test_select_prefers_least_practised_disease():
    bank = [_dirty(), _clean()]
    history = [{"drill_id": "x", "disease": "cleaning-silent-row-loss", "status": "dirty"}]
    picked = drills.select(bank, session=9, history=history, rng=random.Random(1))
    assert picked["disease"] == "aggregation-small-group-extremes"


def test_select_serves_a_clean_control_after_two_dirty():
    bank = [_dirty(), _dirty(id="d2"), _clean()]
    history = [
        {"drill_id": "a", "disease": "x", "status": "dirty"},
        {"drill_id": "b", "disease": "y", "status": "dirty"},
    ]
    picked = drills.select(bank, session=9, history=history, rng=random.Random(1))
    assert picked["status"] == "clean"


def test_select_avoids_repeats_until_variants_are_spent():
    bank = [_dirty(), _dirty(id="variant-02")]
    history = [{"drill_id": "cleaning-silent-row-loss-demo-01",
                "disease": "cleaning-silent-row-loss", "status": "dirty"}]
    picked = drills.select(bank, session=9, history=history, rng=random.Random(1))
    assert picked["id"] == "variant-02"


# ---- session state and scoring --------------------------------------------
def test_exam_conditions_allow_no_hints():
    lab = drills.start(_dirty(), "lab")
    exam = drills.start(_dirty(), "exam")
    assert drills.hints_left(lab) == drills.MAX_DRILL_HINTS
    assert drills.hints_left(exam) == 0
    drills.record_hint(lab)
    assert drills.hints_left(lab) == drills.MAX_DRILL_HINTS - 1


@pytest.mark.parametrize(
    "status, verdict, correct, false_alarm, miss",
    [
        ("dirty", "dont_sign", True, False, False),
        ("dirty", "sign", False, False, True),
        ("clean", "sign", True, False, False),
        ("clean", "dont_sign", False, True, False),
    ],
)
def test_score_computes_the_calibration_outcomes(status, verdict, correct, false_alarm, miss):
    drill = _dirty() if status == "dirty" else _clean()
    session = drills.start(drill, "lab")
    session["verdict"] = verdict
    outcome = drills.score(session)
    assert outcome["verdict_correct"] is correct
    assert outcome["false_alarm"] is false_alarm
    assert outcome["miss"] is miss
    assert outcome["disease"] == drill["disease"]


# ---- display blocks --------------------------------------------------------
def test_artifact_never_names_the_disease():
    """Naming "silent row loss" on the artifact does the locating for the
    student -- the disease label may appear only in the grading debrief."""
    session = drills.start(_dirty(), "exam")
    block = drills.artifact_markdown(session)
    assert "row loss" not in block.lower()
    assert "print(len(df))" in block
    assert "exam conditions" in block


def test_answer_key_block_carries_the_key():
    block = drills.answer_key_block(_dirty())
    assert "DO NOT SIGN" in block and "dropna" in block
    clean_block = drills.answer_key_block(_clean())
    assert "SIGN" in clean_block and "Averages hide spread." in clean_block
