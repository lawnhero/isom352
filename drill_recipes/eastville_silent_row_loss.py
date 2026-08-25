"""Eastville drill: silent row loss — dropna() on biased missingness.

The teaching file's age column is missing mostly for OLDER homes (dirt 2 in
the course's dirt_injection.py, the session 4 trap). This artifact runs the
classic "drop incomplete records" move and then reports average age and
price. Findable from the output alone: homes loaded vs homes analyzed
disagree, and the claim covers the whole market anyway.
"""

DISEASE = "dz-silent-row-loss"
DISEASE_LABEL = "Cleaning/manipulation — Silent row loss"
DEBUT_SESSION = 4
SPINE = "eastville"
DISPLAY_FILENAME = "eastville_teaching.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("eastville_teaching.csv")
homes["price"] = pd.to_numeric(
    homes["price"].str.replace("$", "", regex=False).str.replace(",", "", regex=False)
)
print("Homes loaded:", len(homes))

# Drop incomplete records before analysis
homes = homes.dropna()
print("Homes analyzed:", len(homes))

print("Average age of an Eastville home:", round(homes["age"].mean(), 1), "years")
print("Average price:", round(homes["price"].mean()))
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "dirty",
        "code": _CODE,
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": (
                "The dropna() line. Compare 'Homes loaded' with 'Homes "
                "analyzed': homes vanished between the two lines, and the "
                "conclusion still claims to describe the Eastville market. "
                "The homes that are missing an age are not a random sample "
                "-- in this file they are mostly the OLDER homes -- so "
                "dropping them skews the average age young."
            ),
            "mechanism": (
                "dropna() removes any row with a missing value in any "
                "column. When missingness is concentrated in one kind of "
                "row -- here, older homes -- the surviving sample is "
                "systematically different from the market, and every "
                "statistic computed on it inherits that tilt. The price "
                "average also quietly loses those same homes, though price "
                "itself was complete for every row."
            ),
            "consequence": (
                "The market reads younger than it is, and any decision "
                "keyed to home age -- renovation demand, insurance, "
                "comparable selection -- starts from a biased figure that "
                "nobody chose to bias."
            ),
            "caveats": [],
        },
    }
