import argparse
import csv
import json
import math
from collections import defaultdict
from statistics import median

parser = argparse.ArgumentParser()
parser.add_argument("input")
args = parser.parse_args()
pairs = defaultdict(dict)
with open(args.input, newline="") as stream:
    for row in csv.DictReader(stream):
        workflow = row["workflow"].upper()
        if workflow not in {"A", "B"}:
            parser.error("workflow must be A or B")
        key = (row["participant"], row["pair_id"])
        if workflow in pairs[key]:
            parser.error("Duplicate workflow in one participant/pair")
        for name in ("capture_active_s", "review_active_s", "organize_active_s", "retrieve_active_s"):
            try:
                if not math.isfinite(float(row[name])) or float(row[name]) < 0:
                    raise ValueError
            except (ValueError, KeyError):
                parser.error(f"Missing or invalid {name}")
        pairs[key][workflow] = row
results = []
for key, workflows in pairs.items():
    if set(workflows) != {"A", "B"}:
        parser.error("Every pair must have A and B; do not omit unsuccessful trials")
    a, b = workflows["A"], workflows["B"]

    def active(row, capture):
        keys = ["review_active_s", "organize_active_s", "retrieve_active_s"]
        if capture:
            keys.append("capture_active_s")
        return sum(float(row[key]) for key in keys)

    if active(a, True) <= 0 or active(a, False) <= 0:
        parser.error("Baseline active times must be greater than zero")
    results.append(
        {
            "participant": key[0],
            "pair_id": key[1],
            "active_saving": 1 - active(b, True) / active(a, True),
            "post_scan_saving": 1 - active(b, False) / active(a, False),
            "completed_a": a["completed"],
            "completed_b": b["completed"],
        }
    )
if not results:
    parser.error("No completed pairs; no HR result can be inferred")
print(
    json.dumps(
        {
            "pairs": len(results),
            "median_active_saving": median(r["active_saving"] for r in results),
            "median_post_scan_saving": median(r["post_scan_saving"] for r in results),
            "trials": results,
        },
        ensure_ascii=False,
        indent=2,
    )
)
