"""Demo recipe: "typical" price reported as a mean under visible skew.

The trap: the word "typical" over a mean, with the outliers sitting in
plain sight -- the printed max is several times the reported average.
Findable from the output alone: max vs 'typical' vs min.

DEMO SPINE ONLY -- see demo_silent_row_loss.py.
"""

DISEASE = "describe-one-mean-under-skew"
DISEASE_LABEL = "1-variable description — Mean under skew"
DEBUT_SESSION = 4
SPINE = "demo"
DISPLAY_FILENAME = "demo_homes.csv"

_CODE = '''
import pandas as pd

homes = pd.read_csv("demo_homes.csv")
oldtown = homes[homes["neighborhood"] == "Oldtown"]

print("Oldtown homes:", len(oldtown))
print("Typical Oldtown price:", round(oldtown["price"].mean()))
print("Highest:", oldtown["price"].max(), "  Lowest:", oldtown["price"].min())
'''


def variants():
    yield {
        "id_suffix": "01",
        "status": "dirty",
        "code": _CODE,
        "answer_key": {
            "verdict": "dont_sign",
            "flaw": (
                "'Typical' is claimed from .mean() while the output itself "
                "shows a highest price several times the reported figure. A "
                "few luxury sales pull the mean well above what a typical "
                "Oldtown home costs; the median is the honest 'typical' "
                "here."
            ),
            "mechanism": (
                "The mean weights every dollar equally, so a handful of "
                "extreme values drag it toward them. Under skew, mean and "
                "median separate, and the printed max/min is the tell: when "
                "the top value dwarfs the 'typical' value, the mean is "
                "being pulled."
            ),
            "consequence": (
                "A buyer or lender using this number expects to pay more "
                "than most Oldtown homes actually sell for -- budgets, "
                "offers, and comparisons anchored on it are all inflated."
            ),
            "caveats": [],
        },
    }
