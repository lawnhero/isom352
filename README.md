# ISOM 352 Virtual TA

Virtual TA for Applied Data Analytics with Coding (Python + SQL, undergraduate).

This is a fork of the [ISOM 550 tutor](https://github.com/lawnhero/isom550-dda)
codebase (branch `prototype-trim`), sharing its architecture: a tool-calling
router, seven tutoring tools, three tiers of course knowledge, retrieval that
abstains instead of guessing, and a held practice question. See
`docs/dev_reference.md` for the full turn pipeline — it documents the shared
architecture and is accurate for this repo too.

## Status: forked, not yet re-pointed

The code runs and all 102 tests pass, but the course surface is still the
550 original. Before this faces students:

1. **`course_data/facts.toml`** — fill every TODO (meeting times, office
   hours, grading, the `[software]` block for the Python/SQL toolchain).
   Decide the two-section question first (Canvas 165126 vs 165131).
2. **`course_data/concepts.csv`** — currently the 550 seed (descriptive
   stats, regression, decision analysis). The stats rows genuinely overlap
   this course; replace the JMP-flavored ones and add Python/pandas/SQL
   concepts, especially `common_mistake` rows. Then build the index:
   `python scripts/build_concepts.py --dry-run` (lint) and without the flag.
3. **Sync Canvas and build Tier C**: `python scripts/sync_canvas.py
   --course-id 165126 && python scripts/build_documents.py`, then re-derive
   retrieval thresholds: `python scripts/calibrate_retrieval.py --probe`.
4. **Re-point the prompts** (`utils/chains_lcel.py`, `utils/ta_tools.py`
   docstrings, `utils/router.py` system prompt, `utils/ui.py` labels and
   starter prompts, `utils/sidebar.py`): persona, JMP/Excel → Python/SQL,
   and add the `debug_code` tool for pasted tracebacks.

Already re-pointed: app title, the MongoDB collection (`ISOM 352`), and
script defaults.

The old app (flat router, FAISS/ada-002 syllabus FAQ) lives on `main`. The
untracked `data/chroma_db/` directory is its ada-002 index and can be deleted
once this branch replaces it.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py            # needs .env: MONGODB_URI, OPENAI_API_KEY, DEEPSEEK_API_KEY
python -m pytest tests -q      # no keys or index needed
python scripts/smoke_turn.py "hi"   # one real headless turn, needs keys
```

Add `?debug=1` to the URL for instructor diagnostics (router decision,
per-tool trace, retrieved chunks).
