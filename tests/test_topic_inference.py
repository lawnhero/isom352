"""The curriculum taxonomy is derived from course_data/concepts.csv: pills,
topic inference and the `learning_objective` analytics label all read it.
These tests run against the real CSV — the 352 concept map (Ask → Acquire →
Analyze → Answer plus the Python reading doses) — so they double as a check
that the file still yields a usable pill tree."""

import re

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from utils import concept_taxonomy as tax
from utils.chains_lcel import (
    curriculum_topics,
    format_topic_focus,
    get_subtopics,
    infer_curriculum_topic,
    infer_learning_objective,
    infer_topic_from_history,
    is_new_question,
)


# ---- pills -----------------------------------------------------------------
def test_outline_is_modules_in_teaching_order_with_written_topics():
    out = tax.outline()
    ids = [m["id"] for m in out]
    # The cycle plus the reading language, in the order the file teaches them.
    assert ids[:1] == ["course-frame"]
    for module in ("ask", "python-reading", "acquire",
                   "analyze-describe", "analyze-inference",
                   "analyze-prediction", "answer"):
        assert module in ids
    by_id = {m["id"]: m for m in out}
    labels = [t["label"] for t in by_id["python-reading"]["topics"]]
    assert "Python: dose 1 (s3)" in labels and "Python: dose 5 (s10)" in labels


def test_curriculum_topics_are_module_labels():
    topics = curriculum_topics()
    assert "Acquire" in topics and "Analyze prediction" in topics
    # Nothing the index cannot answer from, and no 550 leftovers.
    assert "Sensitivity analysis" not in topics and "Decision basics" not in topics


def test_subtopics_resolve_by_label_or_id():
    subs = get_subtopics("Acquire")
    assert "Joins" in subs and "LLM-as-extractor" in subs
    assert tax.subtopics("acquire") == subs
    assert get_subtopics("Probability") == []


def test_topic_labels_read_as_labels():
    # Labels are instructor-written and varied ("Python: dose 1 (s3)",
    # "SQL-specific", "2-variable comparison"); the one thing that must never
    # leak through is a raw hyphenated module id posing as a pill.
    for module in tax.outline():
        for topic in module["topics"]:
            label = topic["label"]
            assert label == label.strip() and label
            assert not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", label), label


def test_split_focus_recovers_the_module_from_a_pill_focus():
    assert format_topic_focus("Acquire", "Joins") == "Acquire: Joins"
    assert tax.split_focus("Acquire: Joins") == ("acquire", "Joins")
    assert tax.split_focus("Analyze inference") == ("analyze-inference", "Analyze inference")
    assert tax.split_focus("Interpreting R-squared") == ("", "Interpreting R-squared")


def test_taxonomy_reads_follow_the_file(tmp_path):
    path = tmp_path / "concepts.csv"
    path.write_text(
        "id,title,topic,module,body,status\n"
        "a,Alpha thing,Alpha,mod-one,Body text here,core\n"
        "b,Beta thing,Beta,mod-one,,planned\n"
        "c,Gamma thing,Gamma,mod-two,,planned\n",
        encoding="utf-8",
    )
    assert tax.curriculum_topics(path) == ["Mod one"]          # mod-two has nothing written
    assert tax.subtopics("Mod one", path) == ["Alpha"]         # planned rows are not pills
    assert "mod-two — NOT WRITTEN YET" in tax.format_modules_for_prompt(path)


# ---- inference --------------------------------------------------------------
@pytest.mark.parametrize(
    "query, expected",
    [
        ("Why does my merge have more rows than before?", "Acquire"),
        ("how do I clean a csv file", "Acquire"),
        ("What is a boolean mask?", "Python reading"),
        ("what is a checking sentence", "Python reading"),
        ("what does this coefficient mean", "Analyze inference"),
        ("when should I use logistic regression", "Analyze prediction"),
        ("what is overfitting", "Analyze prediction"),
        ("tell me about the confusion matrix", "Analyze prediction"),
        ("What is train/test leakage?", "Analyze prediction"),
        ("what makes a good analytics question", "Course frame"),
        ("hello", ""),
        ("what is bayes theorem", ""),
    ],
)
def test_infer_curriculum_topic(query, expected):
    assert infer_curriculum_topic(query) == expected


def test_learning_objective_buckets_software_and_logistics():
    assert infer_learning_objective("how do I open a notebook in colab") == "Python / Colab workflows"
    assert infer_learning_objective("hello there") == "General data and decision analytics reasoning"
    # Logistics outranks topic inference: the concept map has a row titled
    # "Variables, assignment, and types", and a deadline question must not be
    # filed under Python reading because of the word "assignment".
    assert infer_learning_objective("when is the deadline") == "Course schedule and due date logistics"
    assert (
        infer_learning_objective("when is the next assignment due")
        == "Course schedule and due date logistics"
    )


def test_topic_from_history_prefers_latest_student_turn():
    history = [
        AIMessage("Hi, I'm Peyton, your virtual TA."),
        HumanMessage("What is train/test leakage?"),
        AIMessage("Leakage is when information from the test set reaches training."),
    ]
    assert infer_topic_from_history(history) == "Analyze prediction"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("multicollinearity", False),
        ("type I error", False),
        ("when is A3 due?", True),
        ("what is the midterm about", True),
        # Deliberately literal: only a leading question word counts.
        ("actually what is the midterm about", False),
        ("", False),
    ],
)
def test_is_new_question(text, expected):
    assert is_new_question(text) is expected


def test_index_drift_reports_a_csv_newer_than_the_build(tmp_path):
    csv_path = tmp_path / "concepts.csv"
    csv_path.write_text("id,title,topic,module,body,status\na,T,Topic,mod,Body,core\n", encoding="utf-8")
    prov = tmp_path / "provenance.json"
    assert "no build stamp" in tax.index_drift(csv_path, prov)
    import hashlib, json
    prov.write_text(json.dumps({"sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(), "built_at": "t"}))
    assert tax.index_drift(csv_path, prov) == ""
    csv_path.write_text("id,title,topic,module,body,status\na,T,Topic,renamed,Body,core\n", encoding="utf-8")
    assert "has changed since" in tax.index_drift(csv_path, prov)
