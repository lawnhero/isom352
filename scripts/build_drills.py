#!/usr/bin/env python3
"""
Build verification-drill artifacts from recipe modules on a clean master.

THE CONTRACT (course rule B3, and this repo's working rules)

    Drills are ENGINEERED, never generated: a recipe is a documented Python
    module that states the disease, the code students will read, and the
    answer key; this harness EXECUTES that code on the real master and stores
    the real output. A drill whose code raises is rejected -- a planted flaw
    must run without error and produce plausible output. No LLM anywhere in
    this path, and no hand-edited artifacts: the JSON files this writes are
    build products, like the vector indexes.

    Answer keys describe mechanisms, not figures, so a re-parameterized
    master never leaves a stale number asserted in a key.

RECIPE MODULES (drill_recipes/*.py)

    DISEASE          = "cleaning-silent-row-loss"     # taxonomy id
    DISEASE_LABEL    = "Cleaning/manipulation — Silent row loss"
    DEBUT_SESSION    = 3
    SPINE            = "eastville"                    # or "demo"
    DISPLAY_FILENAME = "eastville.csv"                # name the code reads

    def variants():
        yield {
            "id_suffix": "01",
            "status": "dirty",                        # or "clean"
            "code": "...",                            # what the student reads
            "answer_key": {...},                      # see utils/drills.validate
        }

    The code is executed in a temp directory holding a copy of the master
    under DISPLAY_FILENAME, with only stdout captured -- exactly what a
    student running the cell would see.

USAGE
    python scripts/build_drills.py --demo               # demo master + demo recipes
    python scripts/build_drills.py --master path.csv    # spine recipes on a real master
    python scripts/build_drills.py --demo --dry-run     # execute + validate, write nothing
"""

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.drills import validate  # noqa: E402

RECIPES_DIR = ROOT / "drill_recipes"
OUT_DIR = ROOT / "course_data" / "drills"
DEMO_MASTER = OUT_DIR / "demo" / "demo_homes.csv"


def load_recipes(recipes_dir: Path, spine: str):
    """Import every recipe module for the given spine."""
    recipes = []
    for path in sorted(recipes_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if getattr(module, "SPINE", "") == spine:
            recipes.append((path, module))
    return recipes


def execute(code: str, master: Path, display_filename: str) -> str:
    """Run the drill code against a copy of the master; return its stdout.

    Raises if the code raises: B3 says a drill must run without error, so a
    failing variant is a build failure, not a warning.
    """
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(master, Path(tmp) / display_filename)
        stdout = io.StringIO()
        namespace = {"__name__": "__main__"}
        cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp)
            with contextlib.redirect_stdout(stdout):
                exec(compile(code, "<drill>", "exec"), namespace)
        finally:
            os.chdir(cwd)
        return stdout.getvalue().strip()


def build_demo_master(path: Path) -> None:
    """A deterministic synthetic housing table for exercising the pipeline.

    Development fixture only -- drills built on it carry spine "demo" and are
    never served to students (see utils/drills.load_bank). Seeded so rebuilds
    are byte-identical and the executed outputs in demo drills stay stable.
    """
    import random

    rng = random.Random(352)
    neighborhoods = ["Northside", "Riverview", "Oldtown"]
    rows = ["home_id,neighborhood,sqft,bedrooms,year_built,price"]
    for i in range(1, 91):
        hood = neighborhoods[i % 3]
        sqft = rng.randint(900, 3200)
        beds = max(1, round(sqft / 850) + rng.choice([-1, 0, 0, 1]))
        year = rng.randint(1955, 2018)
        base = sqft * rng.randint(140, 190)
        bump = {"Northside": 1.15, "Riverview": 1.0, "Oldtown": 0.88}[hood]
        price = int(base * bump)
        # A handful of luxury outliers and missing years make the demo master
        # a usable stage for skew and row-loss recipes.
        if i in (17, 53):
            price *= 4
        year_cell = "" if i in (5, 22, 41, 68, 77, 80, 84, 89) else str(year)
        rows.append(f"{i},{hood},{sqft},{beds},{year_cell},{price}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Build drill artifacts from recipes.")
    ap.add_argument("--recipes-dir", default=str(RECIPES_DIR))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--master", default="", help="clean master CSV for spine recipes")
    ap.add_argument("--spine", default="eastville", help="which recipes to build")
    ap.add_argument("--demo", action="store_true",
                    help="build the demo master and the spine='demo' recipes")
    ap.add_argument("--dry-run", action="store_true", help="execute + validate, write nothing")
    args = ap.parse_args()

    if args.demo:
        spine = "demo"
        master = DEMO_MASTER
        if not args.dry_run or not master.exists():
            build_demo_master(master)
            print(f"demo master: {master.relative_to(ROOT)}")
    else:
        spine = args.spine
        master = Path(args.master) if args.master else None
        if master is None or not master.exists():
            sys.exit(f"--master is required for spine '{spine}' and must exist "
                     "(the clean master never lives in this repo by accident)")

    recipes = load_recipes(Path(args.recipes_dir), spine)
    if not recipes:
        sys.exit(f"no recipes with SPINE == '{spine}' in {args.recipes_dir}")

    out_dir = Path(args.out)
    built, failed = 0, 0
    for path, module in recipes:
        for variant in module.variants():
            drill_id = f"{module.DISEASE}-{spine}-{variant['id_suffix']}"
            try:
                output = execute(variant["code"], master, module.DISPLAY_FILENAME)
            except Exception as exc:
                print(f"  FAIL {drill_id}: code raised: {exc}")
                failed += 1
                continue
            drill = {
                "id": drill_id,
                "disease": module.DISEASE,
                "disease_label": module.DISEASE_LABEL,
                "status": variant["status"],
                "debut_session": module.DEBUT_SESSION,
                "spine": spine,
                "artifact": {"code": variant["code"].strip(), "output": output},
                "answer_key": variant["answer_key"],
                "provenance": {
                    "recipe": str(path.relative_to(ROOT)),
                    "master": str(master.relative_to(ROOT)) if master.is_relative_to(ROOT) else str(master),
                    "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            }
            errors = validate(drill)
            if errors:
                print(f"  FAIL {drill_id}: {'; '.join(errors)}")
                failed += 1
                continue
            if args.dry_run:
                print(f"  ok   {drill_id} ({variant['status']}, output {len(output)} chars)")
            else:
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{drill_id}.json"
                out_path.write_text(json.dumps(drill, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
                print(f"  wrote {out_path.relative_to(ROOT)}")
            built += 1

    print(f"\n{built} drill(s) {'validated' if args.dry_run else 'written'}, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
