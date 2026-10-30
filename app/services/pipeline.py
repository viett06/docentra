"""Self-hosted OCR and an inspectable rule baseline, without benchmark answers."""

import csv
import re
import subprocess
import tempfile
import unicodedata
from io import BytesIO, StringIO
from pathlib import Path

from PIL import Image, ImageStat

from app.core.config import get_settings

LABELS = {
    "employment_contract": {
        "contract_number": ["so hop dong", "contract number"],
        "contract_type": ["loai hop dong", "contract type"],
        "signed_date": ["ngay ky", "signed date"],
        "effective_date": ["ngay hieu luc", "effective date"],
    },
    "degree": {
        "degree_name": ["ten bang", "degree name"],
        "major": ["chuyen nganh", "major"],
        "issuer": ["co so cap", "issuer"],
        "issue_date": ["ngay cap", "issue date"],
    },
    "practice_certificate": {
        "certificate_number": ["so chung chi", "certificate number"],
        "certificate_type": ["loai chung chi", "certificate type"],
        "issue_date": ["ngay cap", "issue date"],
        "issuer": ["co quan cap", "issuer"],
    },
}


def normalize(value):
    return "".join(
        c for c in unicodedata.normalize("NFD", value.lower().replace("đ", "d")) if not unicodedata.combining(c)
    )


def classify(text):
    clean = normalize(text)
    for code, labels in [
        ("practice_certificate", ["chung chi hanh nghe", "practice certificate"]),
        ("employment_contract", ["hop dong lao dong", "employment contract"]),
        ("degree", ["bang tot nghiep", "bang cap", "degree certificate"]),
    ]:
        if any(label in clean for label in labels):
            return code
    return "unknown"


def extract(type_code, pages):
    results = []
    for field, labels in LABELS.get(type_code, {}).items():
        value, source, confidence = None, None, None
        for page in pages:
            for line in page["lines"]:
                text = line["text"].strip()
                clean = normalize(text)
                for label in labels:
                    if re.match(r"^" + re.escape(label) + r"\s*[:：]", clean):
                        candidate = re.split(r"[:：]", text, maxsplit=1)[1].strip()
                        if candidate:
                            value, source, confidence = candidate[:500], page["page_id"], line["confidence"]
                        break
                if value:
                    break
            if value:
                break
        # Date normalization is deterministic; invalid dates remain visible for HR correction.
        if value and (field.endswith("date")):
            matched = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value)
            if matched:
                year, month, day = matched.groups()
                value = f"{year}-{int(month):02d}-{int(day):02d}"
            else:
                matched = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", value)
                if matched:
                    day, month, year = matched.groups()
                    value = f"{year}-{int(month):02d}-{int(day):02d}"
        results.append(
            {
                "field_name": field,
                "value": value,
                "source_page_id": source,
                "confidence": confidence,
                "value_state": "PRESENT" if value else "NOT_FOUND",
            }
        )
    return results


def identity_check(text, employee_code):
    found = {f"SYN-EMP-{number}" for number in re.findall(r"\bSYN[\s-]*EMP[\s-]*(\d{3})\b", text, re.I)}
    if not found:
        return None, "OCR chưa đọc được mã nhân viên; HR cần đối chiếu trực tiếp bản scan."
    if found != {employee_code}:
        return False, "Mã nhân viên trên tài liệu không khớp hồ sơ đã chọn."
    return True, "Mã nhân viên đọc được khớp hồ sơ; HR vẫn phải xác nhận đúng chủ thể."


def ocr_image(data: bytes):
    with Image.open(BytesIO(data)) as original:
        image = original.convert("RGB")
        image.thumbnail((2500, 3500))
        clean = Image.new("RGB", image.size, "white")
        clean.paste(image)
    buffer = BytesIO()
    clean.save(buffer, "PNG")
    flags = ["LOW_CONTRAST"] if ImageStat.Stat(clean.convert("L")).stddev[0] < 20 else []
    with tempfile.TemporaryDirectory(prefix="docentra-ocr-") as directory:
        image_path = Path(directory) / "page.png"
        image_path.write_bytes(buffer.getvalue())
        result = subprocess.run(
            ["tesseract", str(image_path), "stdout", "-l", get_settings().OCR_LANGUAGES, "--psm", "6", "tsv"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    grouped = {}
    for row in csv.DictReader(StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if not word or row.get("level") != "5":
            continue
        key = (row["block_num"], row["par_num"], row["line_num"])
        grouped.setdefault(key, []).append(row)
    lines = []
    for words in grouped.values():
        confidence = sum(max(0, float(w["conf"])) for w in words) / (100 * len(words))
        lines.append({"text": " ".join(w["text"] for w in words), "confidence": round(confidence, 4)})
    if not lines:
        flags.append("NO_TEXT")
    return {
        "text": "\n".join(line["text"] for line in lines),
        "lines": lines,
        "derived": buffer.getvalue(),
        "quality_flags": flags,
    }
