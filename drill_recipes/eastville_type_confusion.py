"""Eastville drill: type confusion — a "price summary" of text.

The teaching file stores price as "$249,310" strings (dirt 1 in the course's
dirt_injection.py, the session 3 trap). This artifact re-parameterizes that
trap for the drill bank: an analyst runs describe() on the raw column and
presents the result as a price summary. It runs, it prints a tidy block --
and it is a summary of TEXT: count/unique/top/freq, no mean, no spread.
Findable from the output alone: a price summary with no average in it.
"""

DISEASE = "dz-type-confusion"
DISEASE_LABEL = "Loading files — Type confusion"
DEBUT_SESSION = 3
SPINE = "eastville"
DISPLAY_FILENAME = "eastville_teaching.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("eastville_teaching.csv")

print("Homes in the file:", len(homes))
print()
print("Price summary for the Eastville market:")
print(homes["price"].describe())
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "dirty",
        "code": _CODE,
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": (
                "The price column was never converted to numbers -- the "
                "dollar signs and commas make it text -- so describe() "
                "returned text statistics: count, unique, top, freq. There "
                "is no mean, no min, no max anywhere in this 'price "
                "summary', and 'top' is the most FREQUENTLY LISTED price "
                "string, not the highest price."
            ),
            "mechanism": (
                "pandas chooses what describe() reports from the column's "
                "type. A column of strings gets frequency statistics; only "
                "a numeric column gets averages and ranges. Nothing errors "
                "-- the type decides silently, which is why the output "
                "looks like a finished summary."
            ),
            "consequence": (
                "Anyone quoting a 'top' or 'typical' price from this block "
                "is reading string bookkeeping, not market figures. Every "
                "downstream number that should have come from this summary "
                "-- a budget, a comparison, a listing strategy -- has no "
                "numeric basis at all."
            ),
            "caveats": [],
        },
    }
