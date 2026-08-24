"""Demo recipe: clean control -- a sound groupby with its counts shown.

Rule D3: wherever students hunt flaws, clean-with-caveats material exists
too, and certifying clean work must be a passing answer. This artifact does
the things the dirty ones fail to do: complete column, adequate group sizes
printed next to the averages, and a claim no bigger than the computation.

DEMO SPINE ONLY -- see demo_silent_row_loss.py.
"""

DISEASE = "aggregation-small-group-extremes"
DISEASE_LABEL = "Aggregation/groupby — Small-group extremes"
DEBUT_SESSION = 3
SPINE = "demo"
DISPLAY_FILENAME = "demo_homes.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("demo_homes.csv")

avg_size = homes.groupby("neighborhood")["sqft"].mean().round(0)
counts = homes.groupby("neighborhood")["sqft"].count()

print("Average home size (sqft) by neighborhood:")
print(avg_size)
print()
print("Homes per neighborhood:")
print(counts)
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "clean",
        "code": _CODE,
        "answer_key": {
            "verdict": "sign",
            "flaw": "",
            "mechanism": (
                "The sqft column is complete, each neighborhood average "
                "rests on a group of thirty homes, and the group sizes are "
                "printed beside the averages so the reader can judge them. "
                "The claim -- average size by neighborhood -- is exactly "
                "what was computed."
            ),
            "consequence": "",
            "caveats": [
                "An average hides spread: two neighborhoods with the same "
                "mean sqft can have very different mixes of homes.",
                "Size is not value -- nothing here says which neighborhood "
                "is more expensive per square foot.",
            ],
        },
    }
