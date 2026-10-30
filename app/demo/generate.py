"""Generate a reproducible synthetic benchmark, without writing any operational records."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter

from app.demo.fixtures import KINDS, render, values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".data/benchmark-v1"))
    parser.add_argument("--employees", type=int, default=30)
    args = parser.parse_args()
    if not 3 <= args.employees <= 30:
        parser.error("--employees must be between 3 and 30")
    destination = args.output
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "manifest.jsonl").exists():
        parser.error("Manifest already exists; choose a new version directory")
    manifest = []
    for number in range(1, args.employees + 1):
        split = "dev" if number <= args.employees * 0.6 else "validation" if number <= args.employees * 0.8 else "test"
        family = {"dev": 0, "validation": 1, "test": 2}[split]
        employee_code = f"SYN-EMP-{number:03d}"
        selected = list(KINDS) if number % 3 == 0 else [code for code in KINDS if code != "unknown"]
        for code in selected:
            doc_id = f"{employee_code}-{code}"
            count = {"employment_contract": 3, "degree": 2, "practice_certificate": 2, "unknown": 1}[code]
            folder = destination / "documents" / doc_id
            folder.mkdir(parents=True, exist_ok=True)
            pages = []
            for page in range(1, count + 1):
                data = render(
                    code, employee_code, f"Nhân viên giả lập {number:03d}", page, count, family, spread_fields=True
                )
                variant = "clean"
                if number % 4 == 0:
                    image = Image.open(BytesIO(data)).filter(ImageFilter.GaussianBlur(0.6))
                    image = image.rotate(1 if page % 2 else -1, fillcolor="white")
                    buffer = BytesIO()
                    image.save(buffer, "PNG")
                    data, variant = buffer.getvalue(), "blur_and_rotation"
                path = folder / f"{page:03d}.png"
                path.write_bytes(data)
                pages.append(
                    {
                        "path": str(path.relative_to(destination)),
                        "page_order": page,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "variant": variant,
                    }
                )
            manifest.append(
                {
                    "id": doc_id,
                    "employee_code": employee_code,
                    "split": split,
                    "layout_family": family,
                    "type_code": code,
                    "pages": pages,
                    "fields": {
                        key: {"value": value, "source_page_order": index % count + 1}
                        for index, (key, value) in enumerate(values(code, number).items())
                    },
                }
            )
    (destination / "manifest.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in manifest) + "\n"
    )
    summary = {
        "version": "synthetic-v1",
        "employees": args.employees,
        "documents": len(manifest),
        "pages": sum(len(row["pages"]) for row in manifest),
        "splits": {split: sum(row["split"] == split for row in manifest) for split in ["dev", "validation", "test"]},
        "limitations": "Generated layouts and typography; not representative of real hospital forms or phone captures.",
    }
    (destination / "dataset.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
