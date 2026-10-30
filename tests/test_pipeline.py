from io import BytesIO

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.errors import AppError
from app.schema.capture import FinalizeRequest
from app.schema.documents import FieldUpdate
from app.services.pipeline import classify, extract, identity_check
from app.services.storage import validate_image


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("HỢP ĐỒNG LAO ĐỘNG", "employment_contract"),
        ("BẰNG TỐT NGHIỆP", "degree"),
        ("CHỨNG CHỈ HÀNH NGHỀ", "practice_certificate"),
        ("PHIẾU GHI CHÚ", "unknown"),
    ],
)
def test_classification_rejects_unknown(text, expected):
    assert classify(text) == expected


def test_extraction_retains_page_evidence_and_missing_values():
    result = extract(
        "employment_contract",
        [
            {"page_id": "page-1", "lines": [{"text": "Số hợp đồng: SYN-001", "confidence": 0.91}]},
            {"page_id": "page-2", "lines": [{"text": "Ngày ký: 01/10/2026", "confidence": 0.87}]},
        ],
    )
    rows = {r["field_name"]: r for r in result}
    assert rows["signed_date"]["value"] == "2026-10-01"
    assert rows["signed_date"]["source_page_id"] == "page-2"
    assert rows["effective_date"]["value"] is None
    assert rows["effective_date"]["value_state"] == "NOT_FOUND"


def test_identity_mismatch_is_not_hidden_by_a_matching_page():
    assert identity_check("SYN-EMP-001 and SYN-EMP-002", "SYN-EMP-001")[0] is False
    assert identity_check("No readable code", "SYN-EMP-001")[0] is None
    assert identity_check("Mã: SYN-EMP-001", "SYN-EMP-001")[0] is True


def test_validate_actual_image_bytes_not_filename():
    with pytest.raises(AppError):
        validate_image(b"This is not an image.png")
    output = BytesIO()
    Image.new("RGB", (200, 300), "white").save(output, "PNG")
    assert validate_image(output.getvalue()) == ("image/png", 200, 300)


def test_schema_rejects_hidden_fields_and_inconsistent_null_values():
    with pytest.raises(ValidationError):
        FieldUpdate(field_name="issuer", value="value", value_state="NOT_FOUND")
    with pytest.raises(ValidationError):
        FieldUpdate(field_name="issuer", value="value", value_state="PRESENT", verified_by="arbitrary-user")


def test_manifest_cannot_contain_the_same_page_twice():
    page = {"id": "00000000-0000-0000-0000-000000000001", "sha256": "a" * 64}
    with pytest.raises(ValidationError):
        FinalizeRequest(version=1, pages=[page, page])
