"""Measure raw OCR/rule outputs; no reviewer corrections or operational DB are used."""

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from app.services import pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "validation", "test"], default="dev")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    selected = [row for row in dataset if row["split"] == args.split]
    if args.limit:
        selected = selected[: args.limit]
    if not selected:
        parser.error("No documents in selected split")
    results = []
    for row in selected:
        started = time.perf_counter()
        pages = []
        for page in row["pages"]:
            data = (args.manifest.parent / page["path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != page["sha256"]:
                raise ValueError("Dataset checksum mismatch")
            output = pipeline.ocr_image(data)
            output["page_id"] = str(page["page_order"])
            pages.append(output)
        predicted_type = pipeline.classify("\n".join(p["text"] for p in pages))
        predicted = {f["field_name"]: f for f in pipeline.extract(predicted_type, pages)}
        fields = []
        for name, expected in row["fields"].items():
            actual = predicted.get(name, {})
            correct = actual.get("value") == expected["value"]
            fields.append(
                {
                    "field_name": name,
                    "correct": correct,
                    "source_correct": actual.get("source_page_id") == str(expected["source_page_order"]),
                    "predicted": actual.get("value"),
                    "expected": expected["value"],
                }
            )
        results.append(
            {
                "id": row["id"],
                "expected_type": row["type_code"],
                "predicted_type": predicted_type,
                "seconds": round(time.perf_counter() - started, 3),
                "fields": fields,
            }
        )
    known = [r for r in results if r["expected_type"] != "unknown"]
    unknown = [r for r in results if r["expected_type"] == "unknown"]
    fields = [f for r in known for f in r["fields"]]
    correct_fields = [f for f in fields if f["correct"]]
    latencies = sorted(r["seconds"] for r in results)

    def ratio(n, total):
        return {"correct": n, "total": total, "rate": round(n / total, 4) if total else None}

    per_class = {}
    for code in ["employment_contract", "degree", "practice_certificate"]:
        tp = sum(r["expected_type"] == code and r["predicted_type"] == code for r in results)
        fp = sum(r["expected_type"] != code and r["predicted_type"] == code for r in results)
        fn = sum(r["expected_type"] == code and r["predicted_type"] != code for r in results)
        support = sum(r["expected_type"] == code for r in results)
        per_class[code] = {"support": support, "f1": round(2 * tp / (2 * tp + fp + fn), 4) if support else None}
    report = {
        "dataset": str(args.manifest),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "pipeline_sha256": hashlib.sha256(Path(pipeline.__file__).read_bytes()).hexdigest(),
        "split": args.split,
        "documents": len(results),
        "before_hr_review": True,
        "classification": ratio(sum(r["predicted_type"] == r["expected_type"] for r in known), len(known)),
        "unknown_rejection": ratio(sum(r["predicted_type"] == "unknown" for r in unknown), len(unknown)),
        "extraction_exact_match": ratio(len(correct_fields), len(fields)),
        "source_linking_on_correct_values": ratio(
            sum(f["source_correct"] for f in correct_fields), len(correct_fields)
        ),
        "per_class": per_class,
        "p50_seconds": latencies[math.ceil(len(latencies) * 0.5) - 1],
        "p95_seconds": latencies[math.ceil(len(latencies) * 0.95) - 1],
        "limitations": "Synthetic rendered images, not an HR time study, phone capture test, security certification, or evidence on real employee records.",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
