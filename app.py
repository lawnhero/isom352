import time
import traceback
import uuid
from pathlib import Path

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.globals import set_verbose

import utils.chains_lcel as chains
import utils.ui as ui
from utils.router import build_ta_agent, run_ta_turn
from utils.attachments import (
    IMAGE_LIMIT_NOTICE,
    MAX_IMAGES,
    attachment_query_block,
    describe_images,
    extract_attachments,
)
from utils.course_context import (
    get_course_context,
    get_course_date_span,
    get_course_facts,
    get_course_links,
    get_software_context,
)
from utils import drills, practice
from utils.sidebar import diagnostics_unlocked, sidebar
import utils.llm_models as llms
from utils.ta_tools import TurnArtifacts

# Set the page_title
st.set_page_config(
    page_title="ISOM 352 Virtual TA",
    page_icon=":material/school:",
    layout="wide",
)

# cache the vectorized embedding database
from utils.utils import (
    load_db,
    query_db_connection,
    build_event_payload,
    store_event,
    store_feedback,
)

# Disable verbose chain debug logs in normal app use.
set_verbose(False)

# 1. Load the Vectorised database
#
# Tier A is deliberately absent here: course facts (dates, people, grading) are
# looked up from course_data/ by utils.course_context, not embedded. There used
# to be a `data/course` index of the same facts as Q&A rows; nothing had queried
# it since Tier A landed, and it had gone stale enough to contradict facts.toml
# (it still claimed Spring 2026 office hours), so it is gone rather than dormant.
contents_path = 'data/concepts'
documents_path = 'data/documents'
# Tier B: concept index from course_data/concepts.toml (scripts/build_concepts.py).
contents_db = load_db(db_path=contents_path, label='concepts')
# Tier C: class recaps + assignment briefs, built by scripts/build_documents.py.
# Missing until that runs; searches then return nothing and the tool abstains.
documents_db = load_db(db_path=documents_path, label='assignments and recaps')

# 2. MongoDB Atlas connection
mongo_db = query_db_connection()
collection = mongo_db['ISOM 352']

# 3. Setup LLM and chains
main_tutor = llms.deepseek_pro_with_fallback
# Facts, software steps and recaps: light, high-traffic work. Wrapped so a
# DeepSeek outage degrades to a slower answer rather than to no deadline answer.
light_tutor = llms.deepseek_flash_with_fallback
agent_llm = llms.openai_gpt56_luna

all_chains = chains.get_all_chains(
    main_tutor,
    light_tutor,
    # Screenshot turns are pinned here regardless of which model is
    # tutoring: reading a regression table out of a PNG is a different
    # capability from writing the explanation, and it should not change
    # every time the primary tutor is swapped.
    vision_llm=llms.openai_gpt56_luna_full,
)
class_chain = all_chains['class_chain']

TA_AVATAR = ":material/school:"


def _parse_chat_input(raw_input):
    """Normalize st.chat_input return value (str or ChatInputValue)."""
    if raw_input is None:
        return "", []
    if isinstance(raw_input, str):
        return raw_input.strip(), []
    text = (getattr(raw_input, "text", None) or raw_input.get("text") or "").strip()
    files = list(getattr(raw_input, "files", None) or raw_input.get("files") or [])
    return text, files


# A section whose chain failed while the others succeeded. The turn goes on;
# the student loses one part, not the whole answer, and is told which.
SECTION_FAILED = (
    "I couldn't write this part of the answer just now. Ask it again on its "
    "own and I'll try once more."
)


def _stream_sections(answerable, status):
    """Stream every prepared section, one after another, in router order.

    Returns `(texts, failures)`, one entry per step. Each section gets its own
    container so the badge and sources can be drawn under it once its text has
    finished; the same footer the transcript redraws (see _render_section), so
    the live turn and its replay cannot drift.
    """
    texts = []
    failures = []
    for position, step in enumerate(answerable):
        if position:
            st.space("small")
        with st.container():
            if step.stream_spec is None:
                text = step.static_answer
                ui.md(text)
                failures.append(None)
            else:
                chain = all_chains.get(step.stream_spec.chain_key)
                if chain is None:
                    raise ValueError(f"Unknown stream chain: {step.stream_spec.chain_key}")
                status.update(
                    label=f"Writing the {ui.route_meta(step.tool_name)['badge'].lower()} part..."
                    if len(answerable) > 1 else "Writing your answer..."
                )
                try:
                    text = ui.write_stream_md(chain.stream(step.stream_spec.payload))
                    failures.append(None)
                except Exception as exc:
                    traceback.print_exc()
                    text = SECTION_FAILED
                    ui.md(text)
                    failures.append(exc)
            ui.render_answer_footer(
                step.tool_name,
                step.retrieval_debug,
                key=f"sources_live_{position}",
                abstained=step.abstained,
                weak=step.retrieval_quality == "weak",
            )
            if step.abstained:
                ui.render_unresolved(get_course_links(), key=f"unresolved_live_{position}")
        texts.append(text)

    streamed = [i for i, step in enumerate(answerable) if step.stream_spec is not None]
    if streamed and all(failures[i] is not None for i in streamed):
        # Nothing reached the student. Let the turn's fallback path answer
        # instead of leaving only apologies on screen.
        raise failures[streamed[0]]
    return texts, failures


# --------------------------------------------------------------------------
# Per-message metadata
#
# Keyed by index into chat_history. Everything a finished turn needs to be
# redrawn after the closing st.rerun() lives here: provenance, sources,
# abstention, feedback id. Before this existed those were rendered live and
# then destroyed by the rerun -- sources in particular were computed on every
# turn and seen by nobody.
# --------------------------------------------------------------------------
def _set_meta(index: int, **fields) -> None:
    st.session_state.message_meta.setdefault(index, {}).update(fields)


def _get_meta(index: int) -> dict:
    return st.session_state.message_meta.get(index, {})


def _record_feedback(interaction_id: str, key: str) -> None:
    """st.feedback callback: log the rating without a second rerun."""
    value = st.session_state.get(key)
    if value is None:
        return
    store_feedback(
        collection=collection,
        session_id=st.session_state.session_id,
        interaction_id=interaction_id,
        helpful="Helpful" if value == 1 else "Not helpful",
        note="",
        mode="unified",
    )
    st.session_state.feedback_submitted_ids.append(interaction_id)
    st.toast("Thanks — that helps improve the tutor.", icon=":material/favorite:")


def _render_section(section: dict, *, key: str, trailing=None) -> None:
    """One answer section: its text, then one footer row (badge, sources,
    and `trailing` -- the rating thumbs on the last section)."""
    ui.md(section.get("text", ""))
    ui.render_answer_footer(
        section.get("route", ""),
        section.get("sources") or [],
        key=f"sources_{key}",
        abstained=section.get("abstained", False),
        weak=section.get("retrieval_quality") == "weak",
        trailing=trailing,
    )
    if section.get("abstained"):
        ui.render_unresolved(get_course_links(), key=f"unresolved_{key}")


def _feedback_widget(interaction_id: str):
    """The thumbs for one turn, or None when the turn has nothing to rate.

    Returned as a callable so the footer row can draw it inline, at the end
    of the badge + sources line, instead of as a third block underneath.
    """
    if not interaction_id:
        return None

    def draw():
        if interaction_id in st.session_state.feedback_submitted_ids:
            st.caption("Rating recorded.")
            return
        key = f"feedback_{interaction_id}"
        st.feedback(
            "thumbs",
            key=key,
            on_change=_record_feedback,
            args=(interaction_id, key),
        )

    return draw


def _render_ai_message(index: int, content: str, *, is_last: bool) -> None:
    """Draw one assistant turn plus everything hanging off it."""
    meta = _get_meta(index)
    with st.chat_message("AI", avatar=TA_AVATAR):
        # Sits where the live status sat, in the state it finished in.
        ui.render_progress(meta.get("progress"))

        if meta.get("attachment_notice"):
            st.warning(meta["attachment_notice"], icon=":material/image_not_supported:")

        # Thumbs sit at the end of the LAST footer row, so the strip under an
        # answer is one line: badge · sources · rating.
        trailing = _feedback_widget(meta.get("interaction_id")) if is_last else None

        sections = meta.get("sections") or []
        if sections:
            # Redraw the turn the way it streamed: each tool's answer with its
            # own badge, rather than one badge over everything.
            for position, section in enumerate(sections):
                if position:
                    st.space("small")
                last = position == len(sections) - 1
                _render_section(
                    section, key=f"{index}_{position}", trailing=trailing if last else None
                )
        elif meta.get("route"):
            # The ungrounded fallback answer.
            ui.md(content)
            ui.render_answer_footer(
                meta["route"],
                meta.get("sources") or [],
                key=f"sources_{index}",
                abstained=meta.get("abstained", False),
                weak=meta.get("retrieval_quality") == "weak",
                trailing=trailing,
            )
            if meta.get("abstained"):
                ui.render_unresolved(get_course_links(), key=f"unresolved_{index}")
        else:
            # Greeting or clarifying turn: nothing to badge or rate.
            ui.md(content)


        if is_last and st.session_state.get("show_diagnostics") and meta.get("diagnostics"):
            ui.render_diagnostics(meta["diagnostics"], key=f"diag_{index}")


# --------------------------------------------------------------------------
# Clarifying turns
# --------------------------------------------------------------------------
def _append_clarifying_turn(action_label: str, clarify_text: str, intent: str, needs: str):
    """Record a clarifying turn and wait for the missing topic/attempt."""
    st.session_state.chat_history.append(HumanMessage(action_label))
    st.session_state.chat_history.append(AIMessage(clarify_text))
    st.session_state.pending_intent = {
        "intent": intent,
        "label": action_label,
        "needs": needs,
    }


def _cancel_pending() -> None:
    st.session_state.pending_intent = None
    st.session_state.pop("clarify_topic_pills", None)
    st.session_state.pop("clarify_subtopic_pills", None)


def _conversation_started(chat_history) -> bool:
    """True once the student has sent at least one message."""
    return any("Human" in str(type(message)) for message in (chat_history or []))


def _resolve_action(action: dict):
    """Resolve a clicked chip into (user_query, display_text, did_clarify).

    did_clarify=True means we asked a question instead and should rerun.
    """
    if action.get("kind") == "query":
        return action["value"], action["label"], False

    intent = action["value"]

    if intent in {"explain", "practice", "check"}:
        _append_clarifying_turn(
            action["label"], action["clarify"], intent, action["needs"]
        )
        return "", "", True

    topic = (st.session_state.get("last_practice_topic") or "").strip()
    if not topic:
        topic = chains.infer_topic_from_history(st.session_state.chat_history)

    if intent == "practice_same":
        if topic:
            return chains.compose_quick_action_query("practice", topic=topic), action["label"], False
        _append_clarifying_turn(
            action["label"],
            "What would you like to practice? Pick a topic below or type it in the chat.",
            "practice",
            "topic",
        )
        return "", "", True

    return "", "", False


def _advance_to_subtopic_selection(pending: dict, parent_topic: str):
    """Move from topic selection to subtopic pills for the chosen parent topic."""
    parent_topic = (parent_topic or "").strip()
    clarify = (
        f"Which part of **{parent_topic}** do you want to focus on? "
        "Pick a subtopic below or type it in the chat."
    )
    st.session_state.chat_history.append(HumanMessage(parent_topic))
    st.session_state.chat_history.append(AIMessage(clarify))
    st.session_state.pending_intent = {
        "intent": pending["intent"],
        "label": pending.get("label", parent_topic),
        "needs": "subtopic",
        "parent_topic": parent_topic,
    }
    st.session_state.pop("clarify_topic_pills", None)
    st.session_state.pop("clarify_subtopic_pills", None)


def _resolve_pending_intent(pending, selected_value, typed_query, uploaded_files):
    """
    Resolve a pending clarify step.

    Returns (user_query, escaped, did_clarify_again).
      escaped=True          -> the student typed a new question instead of an
                               answer; abandon the pending intent and treat the
                               text as an ordinary question.
      did_clarify_again=True -> we advanced topic -> subtopic and should rerun.
    """
    intent = pending["intent"]
    needs = pending["needs"]

    if needs in {"topic", "subtopic"}:
        choice = (selected_value or typed_query or "").strip()
        if not choice:
            return "", False, False

        # A pill click is always an answer to the clarifying question. Only
        # typed text can be a change of subject.
        if not selected_value and chains.is_new_question(typed_query):
            return typed_query, True, False

        if needs == "topic":
            # Pill selection (or typed exact module label) -> ask for the
            # subtopic next, unless the module has only one, in which case the
            # second click would be a question with one answer.
            subtopics = chains.get_subtopics(choice) if choice in chains.curriculum_topics() else []
            if len(subtopics) > 1:
                _advance_to_subtopic_selection(pending, choice)
                return "", False, True
            if len(subtopics) == 1:
                choice = chains.format_topic_focus(choice, subtopics[0])
            return chains.compose_quick_action_query(intent, topic=choice), False, False

        focus = chains.format_topic_focus(pending.get("parent_topic", ""), choice)
        return chains.compose_quick_action_query(intent, topic=focus), False, False

    if needs == "attempt":
        if not typed_query and not uploaded_files:
            return "", False, False
        # A question with nothing attached is not an attempt to grade. Without
        # this, "when is A3 due?" became "Please check my attempt: when is A3 due?"
        if not uploaded_files and chains.is_new_question(typed_query):
            return typed_query, True, False
        return chains.compose_quick_action_query(intent, attempt_text=typed_query), False, False

    return typed_query, False, False


# --------------------------------------------------------------------------
# The verification-drill door
#
# Deliberately modal and router-free. The v2 design's two-lane rule: free
# text goes through the invisible router; submitting to an artifact goes
# through an explicit door that names the AI relationship the student chose.
# While a drill is open, app.py owns the turn -- the router never sees it.
#
# The hard outcomes (verdict correct, false alarm, miss) come from the
# student's own sign/don't-sign click, computed in utils.drills.score --
# never parsed out of model prose. The chains only coach and debrief.
#
# Rule E1: everything logged here is formative. Events carry a self-asserted
# handle and feed the weekly report's calibration curve; they are never
# grading evidence, which is why a resettable handle is sufficient identity.
# --------------------------------------------------------------------------
DRILL_DOOR_LINE = (
    "**You chose: auditee mode.** I produced work; you verify it. "
    "That is the relationship — I will not hint unless you ask (lab "
    "conditions only), and your verdict is yours to sign."
)

NO_DRILLS_MESSAGE = (
    "The drill bank has nothing for where the course is right now — drills "
    "arrive as class sessions do. Ask me to explain or practice a concept "
    "in the meantime."
)

DRILL_VERDICT_NEEDED = (
    "Pick a verdict first — **I'd sign it** or **Don't sign** below — or "
    "take a hint. Your reasoning comes right after the click."
)


def _drill_turn(human_text: str, ai_text: str, *, route: str,
                interaction_id: str = "") -> None:
    """Append one finished drill exchange to history with its meta.

    Drill turns replay through the same section renderer as router turns, so
    the transcript shows the drill badge and the rating thumbs like any
    other answer.
    """
    st.session_state.chat_history.append(HumanMessage(human_text))
    st.session_state.chat_history.append(AIMessage(ai_text))
    _set_meta(
        len(st.session_state.chat_history) - 1,
        sections=[{"text": ai_text, "route": route, "sources": [],
                   "abstained": False, "retrieval_quality": ""}],
        route=route,
        sources=[],
        abstained=False,
        interaction_id=interaction_id,
        diagnostics={},
        attachment_notice="",
        retrieval_quality="",
        progress={"label": ui.route_meta(route)["done"], "state": "complete"},
    )


def _log_drill_event(route: str, metadata: dict, *, query: str = "") -> str:
    payload = build_event_payload(
        event_type="drill",
        session_id=st.session_state.session_id,
        mode="drill",
        response_mode=st.session_state.get("response_mode", ""),
        query=query,
        route_label=route,
        learning_objective=metadata.get("disease", ""),
        resolved=True,
        metadata={**metadata, "handle": st.session_state.get("drill_handle", "")},
    )
    try:
        return str(store_event(collection, payload))
    except Exception:
        traceback.print_exc()
        return ""


def _serve_drill(conditions: str) -> None:
    """Pick from the bank and put the artifact on screen, or say why not."""
    bank, problems = drills.load_bank(include_demo=diagnostics_unlocked())
    for line in problems:
        print(f"[drills] skipped: {line}")
    session_number = drills.current_session(get_course_facts())
    picked = drills.select(
        bank, session_number, history=st.session_state.get("drill_history") or []
    )
    if picked is None:
        st.session_state.drill_session = None
        _drill_turn("Give me a verification drill", NO_DRILLS_MESSAGE,
                    route="drill_serve")
        return
    st.session_state.drill_session = drills.start(picked, conditions)
    st.session_state.drill_session["prior_hints"] = []
    label = "lab" if conditions == "lab" else "exam"
    artifact = (
        DRILL_DOOR_LINE + "\n\n"
        + drills.artifact_markdown(st.session_state.drill_session)
    )
    interaction_id = _log_drill_event(
        "drill_serve",
        {"drill_id": picked["id"], "disease": picked["disease"],
         "status": picked["status"], "conditions": conditions,
         "session_number": session_number},
    )
    _drill_turn(
        f"Give me a verification drill ({label} conditions)",
        artifact,
        route="drill_serve",
        interaction_id=interaction_id,
    )


def _drill_hint() -> None:
    """One streamed nudge, lab conditions only. Never reveals clean/dirty."""
    session = st.session_state.drill_session
    drill = drills.drill_of(session)
    session["prior_hints"] = session.get("prior_hints") or []
    payload = {
        "artifact_block": drills.artifact_markdown(session),
        "answer_key": drills.answer_key_block(drill),
        "hint_number": int(session.get("hints_given") or 0) + 1,
        "max_hints": drills.MAX_DRILL_HINTS,
        "prior_hints": "\n".join(session["prior_hints"]) or "(none yet)",
    }
    with st.chat_message("Human"):
        ui.md("Hint, please")
    with st.chat_message("AI", avatar=TA_AVATAR):
        status = st.status("Writing a hint...", type="compact")
        text = ui.write_stream_md(all_chains["drill_hint_chain"].stream(payload))
        status.update(label=ui.route_meta("drill_hint")["done"], state="complete")
    session["prior_hints"].append(text)
    drills.record_hint(session)
    interaction_id = _log_drill_event(
        "drill_hint",
        {"drill_id": drill.get("id", ""), "disease": drill.get("disease", ""),
         "status": drill.get("status", ""),
         "hints_given": session["hints_given"]},
    )
    _drill_turn("Hint, please", text, route="drill_hint",
                interaction_id=interaction_id)


def _grade_drill(attempt_text: str) -> None:
    """Score the click in Python, stream the debrief, write the ledger."""
    session = st.session_state.drill_session
    drill = drills.drill_of(session)
    outcome = drills.score(session)

    truth = "sign" if drill.get("status") == "clean" else "dont_sign"
    verdict_words = {"sign": "SIGN it", "dont_sign": "DO NOT sign it"}
    outcome_text = (
        f"The correct verdict was {verdict_words[truth]}. "
        f"The student clicked {verdict_words[outcome['verdict']]} — "
        + ("the RIGHT call." if outcome["verdict_correct"] else "the WRONG call.")
    )
    if outcome["false_alarm"]:
        outcome_text += " This is a false alarm on clean work."
    if outcome["miss"]:
        outcome_text += " This is a miss on flawed work."

    verdict_label = ("I'd sign it. " if outcome["verdict"] == "sign"
                     else "Don't sign. ")
    payload = {
        "artifact_block": drills.artifact_markdown(session),
        "answer_key": drills.answer_key_block(drill),
        "outcome": outcome_text,
        "conditions": session.get("conditions", "lab"),
        "attempt_text": attempt_text or "(the student wrote nothing)",
    }
    with st.chat_message("Human"):
        ui.md(verdict_label + attempt_text)
    with st.chat_message("AI", avatar=TA_AVATAR):
        status = st.status("Grading your verdict...", type="compact")
        text = ui.write_stream_md(all_chains["drill_grade_chain"].stream(payload))
        status.update(label=ui.route_meta("drill_grade")["done"], state="complete")

    interaction_id = _log_drill_event("drill_grade", outcome, query=attempt_text)
    history = st.session_state.setdefault("drill_history", [])
    history.append(outcome)
    st.session_state.drill_session = None
    _drill_turn(verdict_label + attempt_text, text, route="drill_grade",
                interaction_id=interaction_id)


def _render_drill_chooser() -> None:
    """The door itself: name the mode, take a handle, pick the conditions."""
    with st.container(border=True):
        st.markdown("**Verification drill** — an artifact that ran without "
                    "errors. Decide whether you would sign it.")
        # Copied to a plain state key on purpose: Streamlit discards
        # widget-keyed state on any rerun where the widget is not drawn, and
        # this chooser vanishes the moment a drill is served -- a handle
        # bound only to the widget key would be gone before the first grade
        # event logs it.
        handle = st.text_input(
            "Drill handle (optional — keeps your practice record across visits)",
            value=st.session_state.get("drill_handle", ""),
            key="drill_handle_input",
            placeholder="any name or your NetID",
        )
        st.session_state.drill_handle = (handle or "").strip()
        with st.container(horizontal=True):
            lab = st.button(
                "Lab conditions", icon=":material/science:",
                help="Field guide open, hints allowed.",
            )
            exam = st.button(
                "Exam conditions", icon=":material/timer:",
                help="No guide, no hints — sign or don't.",
            )
            never_mind = st.button("Never mind", type="tertiary",
                                   icon=":material/close:")
    if never_mind:
        st.session_state.drill_session = None
        st.rerun()
    if lab or exam:
        _serve_drill("lab" if lab else "exam")
        st.rerun()


# 4. Build an app with streamlit
def main():
    st.session_state.setdefault("session_id", str(uuid.uuid4()))
    st.session_state.setdefault("feedback_submitted_ids", [])
    st.session_state.setdefault("pending_intent", None)
    st.session_state.setdefault("last_practice_topic", "")
    st.session_state.setdefault("message_meta", {})

    st.title("ISOM 352 Virtual TA")
    sidebar_settings = sidebar()
    # Instructor-only: the concept index is a frozen copy of concepts.csv, and
    # a renamed module makes the router's filter miss. Students are covered by
    # the widening in retrieval.search_concepts; this is the nudge to rebuild.
    if sidebar_settings["show_diagnostics"]:
        from utils.concept_taxonomy import index_drift

        drift = index_drift()
        if drift:
            st.warning(drift, icon=":material/sync_problem:")
    initial_text = (
        "Hi, I'm Peyton, your virtual TA."
    )

    # Initialize chat history in session state
    if "chat_history" not in st.session_state or not st.session_state.chat_history:
        st.session_state.chat_history = [AIMessage(initial_text)]

    # display previous conversation history
    last_index = len(st.session_state.chat_history) - 1
    for idx, message in enumerate(st.session_state.chat_history):
        if isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                ui.md(message.content)
        elif isinstance(message, AIMessage):
            _render_ai_message(idx, message.content, is_last=(idx == last_index))

    pending = st.session_state.pending_intent
    conversation_started = _conversation_started(st.session_state.chat_history)

    # Starter prompts fill the empty main area before the first question.
    starter_choice = None
    if not conversation_started and not pending:
        st.caption("Try asking")
        starter_choice = st.pills(
            "Example questions",
            options=ui.STARTER_PROMPTS,
            selection_mode="single",
            key="starter_prompt_pills",
            label_visibility="collapsed",
        )

    # Topic / subtopic pills while waiting for a clarifying detail.
    selected_topic = None
    selected_subtopic = None
    if pending and pending.get("needs") == "topic":
        st.caption("Suggested topics")
        selected_topic = st.pills(
            "Course topics",
            options=chains.curriculum_topics(),
            selection_mode="single",
            key="clarify_topic_pills",
            label_visibility="collapsed",
        )
    elif pending and pending.get("needs") == "subtopic":
        parent = pending.get("parent_topic", "")
        subtopics = chains.get_subtopics(parent)
        st.caption(f"Subtopics in {parent}" if parent else "Suggested subtopics")
        if subtopics:
            selected_subtopic = st.pills(
                "Course subtopics",
                options=subtopics,
                selection_mode="single",
                key="clarify_subtopic_pills",
                label_visibility="collapsed",
            )

    # The drill door: the chooser panel while conditions are being picked,
    # and a flag for the rest of the turn once an artifact is on screen.
    drill_state = st.session_state.get("drill_session")
    if drill_state and drill_state.get("choosing"):
        _render_drill_chooser()
        drill_state = st.session_state.get("drill_session")
    drill_open = drills.is_active(drill_state)

    # An explicit way out of the clarify state. Typing a new question also
    # works (see _resolve_pending_intent), but the student should be able to
    # see that backing out is allowed rather than having to discover it.
    if pending:
        with st.container(horizontal=True, horizontal_alignment="left"):
            if st.button(
                "Never mind",
                icon=":material/close:",
                key="cancel_pending",
                type="tertiary",
            ):
                _cancel_pending()
                st.rerun()

    # Pin composer controls so students always see them while scrolling history.
    selected_action = None
    drill_clicks = {}
    with st.bottom:
        if drill_open:
            # An open drill replaces the chips: the verdict IS the interface,
            # and the click is what drills.score() trusts.
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                if not drill_state.get("verdict"):
                    drill_clicks["dont_sign"] = st.button(
                        "Don't sign — I found a problem",
                        icon=":material/report:", key="drill_dont_sign",
                    )
                    drill_clicks["sign"] = st.button(
                        "I'd sign it", icon=":material/verified:", key="drill_sign",
                    )
                    hints_left = drills.hints_left(drill_state)
                    if hints_left:
                        drill_clicks["hint"] = st.button(
                            f"Hint ({hints_left} left)",
                            icon=":material/lightbulb:", key="drill_hint_btn",
                        )
                else:
                    drill_clicks["change"] = st.button(
                        "Change verdict", icon=":material/undo:", key="drill_change",
                    )
                drill_clicks["exit"] = st.button(
                    "Exit drill", type="tertiary", icon=":material/close:",
                    key="drill_exit",
                )
        elif not pending:
            if not conversation_started:
                st.caption("Quick actions")
                selected_action = ui.render_action_row(
                    ui.QUICK_ACTIONS, key_prefix="quick_action"
                )
            else:
                st.caption("What next?")
                selected_action = ui.render_action_row(
                    ui.FOLLOW_UPS, key_prefix="follow_up"
                )

        chat_placeholder = "Ask a question, or attach a screenshot of your work..."
        if drill_open:
            verdict = drill_state.get("verdict")
            if verdict == "dont_sign":
                chat_placeholder = (
                    "Name where it goes wrong, what the mistake is in business "
                    "terms, and what acting on it would cost..."
                )
            elif verdict == "sign":
                chat_placeholder = (
                    "Your checking sentence: what did you check before "
                    "trusting this?"
                )
            else:
                chat_placeholder = "Pick a verdict above, or take a hint..."
        elif pending and pending.get("needs") == "topic":
            chat_placeholder = "Pick a topic above, or type one..."
        elif pending and pending.get("needs") == "subtopic":
            chat_placeholder = "Pick a subtopic above, or type one..."
        elif pending and pending.get("needs") == "attempt":
            chat_placeholder = "Paste your attempt, or attach a screenshot..."

        raw_input = st.chat_input(
            chat_placeholder,
            key="user_query",
            accept_file=True,
            file_type=["png", "jpg", "jpeg", "pdf", "txt", "csv"],
            submit_mode="stop",
        )
        st.caption("Do not include personal information. This tutor can make mistakes.")

    typed_query, uploaded_files = _parse_chat_input(raw_input)
    user_query = ""
    display_user_text = ""

    # 0) An open drill owns the turn. Nothing here reaches the router: the
    #    buttons move the drill's own state machine, and typed text is the
    #    student's reasoning (or a nudge back to the verdict buttons).
    if drill_open:
        if drill_clicks.get("exit"):
            st.session_state.drill_session = None
            st.rerun()
        if drill_clicks.get("change"):
            drill_state["verdict"] = ""
            st.rerun()
        if drill_clicks.get("hint"):
            _drill_hint()
            st.rerun()
        if drill_clicks.get("sign") or drill_clicks.get("dont_sign"):
            drill_state["verdict"] = (
                "sign" if drill_clicks.get("sign") else "dont_sign"
            )
            st.rerun()
        if typed_query:
            if drill_state.get("verdict"):
                _grade_drill(typed_query)
            else:
                _drill_turn(typed_query, DRILL_VERDICT_NEEDED, route="drill_serve")
            st.rerun()
        return

    # 0b) The drill chip: opens the door (conditions chooser), no query runs.
    if selected_action is not None and selected_action.get("kind") == "drill":
        _cancel_pending()
        st.session_state.drill_session = {"choosing": True}
        st.rerun()

    # 1) Chip click - quick action before the conversation starts, or a
    #    route-aware follow-up after it.
    if selected_action is not None:
        _cancel_pending()
        composed, label, did_clarify = _resolve_action(selected_action)
        if did_clarify:
            st.rerun()
        user_query = composed
        display_user_text = label

    # 2) Completing (or abandoning) a pending clarifying turn
    elif pending is not None:
        selected_value = None
        if pending.get("needs") == "topic":
            selected_value = selected_topic
        elif pending.get("needs") == "subtopic":
            selected_value = selected_subtopic

        composed, escaped, did_clarify_again = _resolve_pending_intent(
            pending, selected_value, typed_query, uploaded_files
        )
        if did_clarify_again:
            st.rerun()
        if escaped:
            _cancel_pending()
            user_query = composed
            display_user_text = composed
        elif composed:
            detail_text = selected_value or typed_query
            if pending.get("needs") == "subtopic":
                detail_text = chains.format_topic_focus(
                    pending.get("parent_topic", ""),
                    detail_text,
                )
            display_user_text = detail_text if detail_text else "Attached attempt for review"
            user_query = composed
            _cancel_pending()
            if detail_text:
                st.session_state.last_practice_topic = detail_text

    # 3) Normal free-form chat, or a starter prompt from the empty state
    else:
        user_query = typed_query
        display_user_text = typed_query
        if not user_query and starter_choice:
            user_query = starter_choice
            display_user_text = starter_choice
            st.session_state.pop("starter_prompt_pills", None)
        if uploaded_files and not user_query:
            user_query = "Please review the attached file(s) and help me with the next step."
            display_user_text = user_query

    if not user_query:
        return

    # ----------------------------------------------------------------------
    # Run the turn
    # ----------------------------------------------------------------------
    attachment_context, unreadable_names, images = extract_attachments(uploaded_files)
    attachment_note = ""
    readable_names = [
        f.name for f in uploaded_files if f.name not in set(unreadable_names)
    ]
    if readable_names:
        attachment_note = f"\n\n[Student attached: {', '.join(readable_names)}]"

    # The router reads this line instead of the pixels; the images themselves
    # go round the agent loop and straight to the chain (see build_ta_agent).
    query_for_model = (
        f"{user_query}{attachment_note}{describe_images(images)}"
        f"{attachment_query_block(attachment_context)}"
    )
    # Analytics label only (the weekly report groups turns by it); nothing
    # about the prompts depends on it.
    learning_objective = chains.infer_learning_objective(user_query)


    with st.chat_message("Human"):
        ui.md(display_user_text or user_query)
        for uploaded in uploaded_files:
            mime = (uploaded.type or "").lower()
            if mime.startswith("image/"):
                st.image(uploaded, caption=uploaded.name, width="stretch")
            else:
                st.caption(f"Attached: {uploaded.name}")

    route_label = "agent_direct"
    retrieval_debug = []
    tools_used = []
    abstained = False
    retrieval_quality = ""
    diagnostics = {}
    turn_result = {}
    # One entry per answer section. Empty on the fallback path, where a single
    # ungrounded answer is all there is.
    sections = []
    effective_response_mode = sidebar_settings["response_mode"]

    # Wall clock for the whole turn, routing included -- what the student
    # actually waited, not the sum of the parts we happened to measure.
    turn_started = time.perf_counter()

    with st.chat_message("AI", avatar=TA_AVATAR):
        # A status line rather than a bare skeleton: routing is a full LLM call
        # before a single token of the answer appears, and "Looking up the
        # course schedule" is both an honest progress signal and a chance for
        # the student to notice a misroute before reading a wrong answer. The
        # line is updated at three points: when the router has chosen, when
        # writing starts, and when the turn is done.
        status = st.status("Reading your question...", type="compact")
        status_label = ""
        status_state = "complete"
        try:
            artifacts = TurnArtifacts()
            agent = build_ta_agent(
                agent_llm=agent_llm,
                contents_db=contents_db,
                documents_db=documents_db,
                chains_dict=all_chains,
                chat_history=st.session_state.chat_history,
                response_mode=sidebar_settings["response_mode"],
                artifacts=artifacts,
                course_context=get_course_context(),
                software_context=get_software_context(),
                course_span=get_course_date_span(),
                memory_window=sidebar_settings["memory_window"],
                images=images,
                practice_session=st.session_state.get("practice_session"),
                attachment_text=attachment_context,
            )
            turn_result = run_ta_turn(
                agent=agent,
                query=query_for_model,
                chat_history=st.session_state.chat_history,
                artifacts=artifacts,
                memory_window=sidebar_settings["memory_window"],
                on_route=lambda names: status.update(label=f"{ui.working_label(names)}..."),
            )

            route_label = turn_result["route_label"]
            answerable = turn_result.get("answerable_steps") or []

            stream_started = time.perf_counter()
            texts = []

            if answerable:
                # One section per tool call, in the order the model asked for
                # them -- which mirrors the order the student asked. Each gets
                # its own badge and its own sources, so a coding walkthrough and a
                # concept explanation are never merged under one label.
                texts, _ = _stream_sections(answerable, status)
                ai_response = "\n\n".join(t for t in texts if t)
            elif turn_result.get("answer"):
                # The router called no tool; its own reply is the answer.
                ai_response = turn_result["answer"]
                ui.md(ai_response)
            else:
                status.update(label="Answering directly...")
                ai_response = ui.write_stream_md(
                    class_chain.stream(
                        chains.build_chain_payload(
                            query=query_for_model,
                            chat_history=st.session_state.chat_history,
                            response_mode=effective_response_mode,
                            memory_window=sidebar_settings["memory_window"],
                        )
                    )
                )

            stream_ms = int((time.perf_counter() - stream_started) * 1000)
            ai_response_for_history = ai_response
            sections = [
                {
                    "text": text,
                    "route": step.tool_name,
                    "sources": step.retrieval_debug,
                    "abstained": step.abstained,
                    "retrieval_quality": step.retrieval_quality,
                }
                for step, text in zip(answerable, texts)
            ]
            tools_used = turn_result["tools_used"]
            retrieval_debug = turn_result.get("retrieval_debug") or []
            abstained = bool(turn_result.get("abstained", False))
            retrieval_quality = turn_result.get("retrieval_quality") or ""
            diagnostics = {
                "tool_calls": turn_result.get("tool_calls") or [],
                "trace": turn_result.get("trace") or [],
                "retrieval_debug": retrieval_debug,
                "router_ms": turn_result.get("router_ms", 0),
                "router_text": turn_result.get("router_text", ""),
                "stream_ms": stream_ms,
                "route_label": route_label,
                "response_mode": effective_response_mode,
                "abstained": abstained,
                "retrieval_quality": retrieval_quality,
            }

            # The turn collapses to one verdict: what was consulted, how much
            # of it, and how long it took. This is also the label the stored
            # status keeps, so the transcript reads the same as the live turn.
            status_label = ui.completion_label(
                [section["route"] for section in sections] or [route_label],
                source_count=len(retrieval_debug),
                seconds=time.perf_counter() - turn_started,
                abstained=abstained,
            )
            status.update(label=status_label, state="complete")

        except Exception as e:
            # Full trace to stderr: the exception text is for whoever is
            # debugging, not the student. The label says the lookup failed and
            # the fallback answer arrives underneath it.
            traceback.print_exc()
            status.update(label="Course lookup failed", state="error")
            route_label = "fallback_class_chain"
            effective_response_mode = "Direct answer"
            diagnostics = {
                "tool_calls": [], "trace": [], "retrieval_debug": [],
                "router_ms": 0, "router_text": "",
                "stream_ms": 0, "route_label": "fallback_class_chain",
                "response_mode": effective_response_mode, "abstained": False,
                "error": str(e),
            }
            status_state = "error"
            try:
                status.update(label="Answering without course materials...", state="error")
                ai_response_for_history = ui.write_stream_md(
                    class_chain.stream(
                        chains.build_chain_payload(
                            query=query_for_model,
                            chat_history=st.session_state.chat_history,
                            response_mode=effective_response_mode,
                            memory_window=sidebar_settings["memory_window"],
                        )
                    )
                )
                status_label = ui.completion_label(
                    ["fallback_class_chain"],
                    seconds=time.perf_counter() - turn_started,
                )
                status.update(label=status_label, state="error")
            except Exception as fallback_error:
                # Both the router and the fallback failed. Say so in the
                # transcript rather than letting a NameError take the app down.
                print(fallback_error)
                abstained = True
                ai_response_for_history = (
                    "I could not reach the tutoring service for that question. "
                    "Please try again in a moment."
                )
                status_label = "Could not reach the tutoring service"
                status.update(label=status_label, state="error")
                ui.md(ai_response_for_history)

    # Said plainly, on the turn it applies to, rather than left for the student
    # to infer from an answer that quietly ignored their screenshot.
    attachment_notice = ""
    if unreadable_names:
        attachment_notice = "I could not read: " + ", ".join(unreadable_names)
        if len(images) >= MAX_IMAGES:
            attachment_notice += ". " + IMAGE_LIMIT_NOTICE

    practice_topic = (turn_result.get("practice_topic") or "") or chains.infer_topic_from_history(
        st.session_state.chat_history + [HumanMessage(query_for_model)]
    )
    if practice_topic:
        st.session_state.last_practice_topic = practice_topic

    # Practice session state is written HERE, not in the tool: generate_practice
    # returns stream_ready and the question text only exists once the stream has
    # produced it. Same split `last_practice_topic` already uses.
    _asked = next(
        (sec for sec in sections
         if sec["route"] == "generate_practice" and not sec["abstained"]),
        None,
    )
    if _asked:
        _difficulty = next(
            (t.get("difficulty") for t in (turn_result.get("trace") or [])
             if t.get("tool") == "generate_practice"),
            "same",
        )
        st.session_state.practice_session = practice.start(
            question=_asked["text"], topic=practice_topic, difficulty=_difficulty,
        )
    elif any(sec["route"] == "coach_practice" for sec in sections):
        st.session_state.practice_session = practice.record_hint(
            st.session_state.get("practice_session")
        )
    elif any(sec["route"] == "check_attempt" for sec in sections):
        # Deliberately does not clear the session: a student who has just been
        # given feedback is the most likely person to revise and resubmit.
        st.session_state.practice_session = practice.record_attempt(
            st.session_state.get("practice_session")
        )

    # append AI response to chat history
    history_user_text = (display_user_text or user_query) + attachment_note
    st.session_state.chat_history.append(HumanMessage(history_user_text))
    st.session_state.chat_history.append(AIMessage(ai_response_for_history))
    ai_index = len(st.session_state.chat_history) - 1

    # Two different questions, previously answered by one variable.
    #
    # `abstained` is structural: a tool declined, and the text the student sees
    # IS the refusal. That is what may show an orange badge and a recovery panel.
    #
    # `unresolved` is the analytics signal, and is deliberately looser -- a
    # chain can refuse in prose without the tool abstaining. Using the loose
    # version for the badge put "Not found in course materials" under genuine
    # answers that merely contained the phrase "not covered", which the
    # concept_chain prompt explicitly instructs the model to say when a topic is
    # out of scope.
    unresolved = (
        abstained
        or "don't have enough information" in ai_response_for_history.lower()
        or "not covered" in ai_response_for_history.lower()
    )
    event_payload = build_event_payload(
        event_type="query",
        session_id=st.session_state.session_id,
        mode="unified",
        response_mode=effective_response_mode,
        query=user_query,
        route_label=route_label,
        learning_objective=learning_objective,
        resolved=not unresolved,
        metadata={
            "tools_used": tools_used,
            "tool_calls": turn_result.get("tool_calls") or [],
            "source_count": len(retrieval_debug),
            "attachment_count": len(uploaded_files),
            "attachment_names": [f.name for f in uploaded_files],
            "attachment_text_chars": len(attachment_context),
            # Count only. The bytes are the student's own work and have no
            # business in the analytics store.
            "attachment_image_count": len(images),
            # Logged so the weak/abstain rate can be tracked per route in the
            # weekly report, and the thresholds retuned against real traffic.
            "retrieval_quality": retrieval_quality,
        },
    )
    interaction_id = str(store_event(collection, event_payload))

    _set_meta(
        ai_index,
        # Sections drive rendering. The flat fields below stay for the
        # single-answer fallback path and for the follow-up chips, which key
        # off the LAST thing the student read.
        sections=sections,
        route=sections[-1]["route"] if sections else route_label,
        sources=retrieval_debug,
        abstained=abstained,
        interaction_id=interaction_id,
        diagnostics=diagnostics,
        attachment_notice=attachment_notice,
        retrieval_quality=retrieval_quality,
        progress={"label": status_label, "state": status_state},
    )

    st.rerun()


if __name__ == '__main__':
    main()
