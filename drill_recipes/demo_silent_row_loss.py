"""Demo recipe: silent row loss via a blanket dropna().

The trap: dropna() removes any row with a missing value in ANY column. The
analysis uses price only, but rows are lost for a missing year_built the
code never touches -- and the prose claims a citywide figure. Findable: the
output states both the loaded count and the analyzed count; a careful reader
sees homes vanish with no decision recorded.

DEMO SPINE ONLY. Never served to students (utils/drills.load_bank excludes
spine "demo"); exists so the drill door and grader can be exercised before
the eastville master arrives.
"""

DISEASE = "cleaning-silent-row-loss"
DISEASE_LABEL = "Cleaning/manipulation — Silent row loss"
DEBUT_SESSION = 3
SPINE = "demo"
DISPLAY_FILENAME = "demo_homes.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("demo_homes.csv")
print("Homes loaded:", len(homes))

# Clean the data before analysis
clean = homes.dropna()

avg_price = clean["price"].mean()
print("Citywide average home price:", round(avg_price))
print("Based on", len(clean), "homes")
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "dirty",
        "code": _CODE,
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": (
                "The dropna() line. It silently removes every home with a "
                "missing value in ANY column -- here, homes missing "
                "year_built -- even though the analysis only uses price, "
                "which is complete. Compare 'Homes loaded' with 'Based on N "
                "homes': homes disappeared and nothing in the code decided "
                "they should."
            ),
            "mechanism": (
                "dropna() with no arguments is a row-level filter on every "
                "column at once. A 'citywide average' is then computed on a "
                "subset nobody chose, and the homes excluded are not a "
                "random sample -- they are whichever homes happen to have a "
                "gap in an unrelated field."
            ),
            "consequence": (
                "The reported citywide price represents only the homes with "
                "complete records. Anyone pricing, budgeting, or comparing "
                "against this number is acting on a figure whose coverage "
                "was never stated or intended."
            ),
            "caveats": [],
        },
    }
