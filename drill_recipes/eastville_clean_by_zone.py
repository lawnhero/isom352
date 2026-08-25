"""Eastville clean control (session 4 tier): the full chain, done right.

The counterpart to the session-4 dirty drills: price converted before
computing, rows checked against distinct house ids and deduplicated with
the check PRINTED, and per-zone averages shown next to their group sizes.
Certifying this is a win; refusing to sign it is the false alarm the
calibration ledger records.
"""

DISEASE = "dz-duplicate-rows"
DISEASE_LABEL = "Cleaning/manipulation — Duplicate rows (clean control)"
DEBUT_SESSION = 4
SPINE = "eastville"
DISPLAY_FILENAME = "eastville_teaching.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("eastville_teaching.csv")
homes["price"] = pd.to_numeric(
    homes["price"].str.replace("$", "", regex=False).str.replace(",", "", regex=False)
)

print("Rows in the file:", len(homes))
print("Distinct homes:", homes["house"].nunique())

# Keep one listing per home before counting or averaging
homes = homes.drop_duplicates(subset="house")

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
        "status": "clean",
        "code": _CODE,
        "answer_key": {
            "verdict": "sign",
            "flaw": "",
            "mechanism": (
                "Every trap this file carries is handled in the open: price "
                "is converted to numbers before any arithmetic, the "
                "row-versus-distinct-homes check is printed so the reader "
                "sees the relisted homes exist, duplicates are removed by "
                "house id before counting, and each zone average sits next "
                "to the group size it rests on."
            ),
            "consequence": "",
            "caveats": [
                "An average per zone still hides the spread within a zone; "
                "two zones with similar means can hold very different "
                "markets.",
                "The age column has missing values, so any follow-up that "
                "uses age must handle them deliberately rather than with a "
                "blanket dropna().",
            ],
        },
    }
