"""Eastville clean control (session 3 tier): a sound typical-price read.

Rule D3: wherever students hunt flaws, clean-with-caveats material exists
too. This artifact does the session-3 job correctly: converts price to
numbers before computing, claims "typical" from the median (robust to the
market's expensive tail), and shows the range beside it.

The one honest caveat is the file's own: rows are listings, and the
relisting issue does not debut until session 4 -- so it lives in the
caveats, where the debrief can credit a student who spots it early without
the drill being scored dirty.
"""

DISEASE = "dz-type-confusion"
DISEASE_LABEL = "Loading files — Type confusion (clean control)"
DEBUT_SESSION = 3
SPINE = "eastville"
DISPLAY_FILENAME = "eastville_teaching.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("eastville_teaching.csv")
prices = pd.to_numeric(
    homes["price"].str.replace("$", "", regex=False).str.replace(",", "", regex=False)
)

print("Rows in the file:", len(homes))
print("Typical Eastville price (median):", round(prices.median()))
print("Range:", round(prices.min()), "to", round(prices.max()))
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
                "The price text is converted to numbers before any "
                "statistic is computed -- both the dollar sign and the "
                "comma are removed, so to_numeric parses every value. "
                "'Typical' is claimed from the median, which a handful of "
                "expensive homes cannot drag, and the range is printed "
                "beside it so the reader can see the spread the median "
                "summarizes."
            ),
            "consequence": "",
            "caveats": [
                "The count is rows in the file, and a row is a listing -- "
                "if any home was relisted it is counted twice. The median "
                "barely moves for a few repeats, but the row count should "
                "not be quoted as a count of homes.",
                "A single market-wide figure hides the gap between school "
                "zones; a by-zone read would tell a buyer more.",
            ],
        },
    }
