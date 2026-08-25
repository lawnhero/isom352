"""Eastville drill: duplicate rows — relisted homes counted twice.

Three houses appear twice in the teaching file (dirt 3 in the course's
dirt_injection.py: relisted homes, rows 108 -> 111; the session 4 trap).
This artifact counts rows and calls them homes. Findable from what session
4 taught: on this file, a row is a LISTING, and the row-vs-distinct-homes
check is the first thing a careful reader runs.
"""

DISEASE = "dz-duplicate-rows"
DISEASE_LABEL = "Cleaning/manipulation — Duplicate rows"
DEBUT_SESSION = 4
SPINE = "eastville"
DISPLAY_FILENAME = "eastville_teaching.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("eastville_teaching.csv")
homes["price"] = pd.to_numeric(
    homes["price"].str.replace("$", "", regex=False).str.replace(",", "", regex=False)
)

print("Homes on the Eastville market:", len(homes))
print()
print("Homes per school zone:")
print(homes.groupby("school")["price"].count())
print()
print("Average price by school zone:")
print(homes.groupby("school")["price"].mean().round(0))
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "dirty",
        "code": _CODE,
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": (
                "len(homes) counts ROWS, and this file's rows are listings: "
                "several homes were relisted and appear twice. The headline "
                "'homes on the market' figure, the per-zone counts, and the "
                "zone averages all weight those relisted homes double. "
                "Nothing in the code checked rows against distinct house "
                "ids before claiming a count of homes."
            ),
            "mechanism": (
                "A row is a record, not necessarily a thing. When the same "
                "house appears under two listings, every count and every "
                "average silently treats it as two houses. The one-line "
                "check -- compare len(homes) with homes['house'].nunique() "
                "-- was never run."
            ),
            "consequence": (
                "The market looks bigger than it is and the double-counted "
                "homes pull the zone averages toward their own prices. "
                "Inventory reports, market-share claims, and zone "
                "comparisons built on these figures are all quietly wrong."
            ),
            "caveats": [],
        },
    }
