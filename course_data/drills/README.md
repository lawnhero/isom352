# The verification-drill bank

One JSON file per drill. **Never write or edit these by hand, and never let
an LLM write one** — every file here is a build product of
`scripts/build_drills.py`, which executes a documented recipe
(`drill_recipes/*.py`) against a clean master dataset and stores the real
output. That is how the course rules are kept:

- **B3** — a planted flaw must run without error, produce plausible output,
  and be findable from what has been taught. Execution is the proof of the
  first two; the `debut_session` field (gated by `utils/drills.py` against
  `[schedule]` in `facts.toml`) is the third.
- **D3** — clean-with-caveats artifacts (`"status": "clean"`) live in the
  same bank and stay in rotation; correctly certifying one is a scored win,
  and a false alarm on one is a scored error.
- **Working rule** — answer keys describe mechanisms, never figures, so a
  re-parameterized master can't leave a stale number asserted anywhere.

`spine: "demo"` drills are development fixtures built from the synthetic
`demo/demo_homes.csv`; students never see them (`load_bank` excludes them
unless instructor diagnostics are unlocked via `?debug=1`).

To build real drills once a session's dirt-script trap exists:

```bash
python scripts/build_drills.py --spine eastville --master path/to/eastville.csv
```

Add a recipe per disease per spine in `drill_recipes/`; the module contract
is documented in `scripts/build_drills.py`. Each session build should export
1–2 re-parameterized variants of its Verify trap plus one clean control —
the bank grows as diseases debut, and `python -m pytest tests -q` validates
every checked-in drill on every run.
