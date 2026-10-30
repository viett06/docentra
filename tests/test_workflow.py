from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app import worker
from app.model import FieldPrediction, ProcessingJob
from app.services.security import utcnow

pytestmark = pytest.mark.integration


def login(system, role="reviewer"):
    client = system["client"]
    response = client.post("/api/v1/auth/login", json={"email": role + "@test.local", "password": "TestDocentra!2026"})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


def upload(system, image_bytes):
    client = system["client"]
    response = client.post(
        "/api/v1/scan-sessions", json={"employee_id": str(system["employee"].id), "client_session_id": str(uuid4())}
    )
    assert response.status_code == 200, response.text
    capture = response.json()
    response = client.post(
        f"/api/v1/scan-sessions/{capture['id']}/pages",
        data={"client_page_id": str(uuid4()), "page_order": 1},
        files={"file": ("page.png", image_bytes, "image/png")},
    )
    assert response.status_code == 200, response.text
    return capture, response.json()


def enqueue(system, image_bytes):
    client = system["client"]
    capture, page = upload(system, image_bytes)
    path = f"/api/v1/scan-sessions/{capture['id']}"
    response = client.post(
        path + "/finalize",
        json={"version": capture["version"], "pages": [{"id": page["id"], "sha256": page["sha256"]}]},
    )
    assert response.status_code == 200, response.text
    body = {"idempotency_key": str(uuid4()), "groups": [{"title": "Synthetic document", "page_ids": [page["id"]]}]}
    response = client.post(path + "/process", json=body)
    assert response.status_code == 200, response.text
    return capture, page, response.json(), body


def process(system, image_bytes, monkeypatch, code="SYN-EMP-001", unknown=False):
    capture, page, job, body = enqueue(system, image_bytes)
    lines = (
        ["PHIẾU GHI CHÚ"]
        if unknown
        else [
            "HỢP ĐỒNG LAO ĐỘNG",
            f"Mã nhân viên: {code}",
            "Số hợp đồng: SYN-HD-001",
            "Loại hợp đồng: Có thời hạn",
            "Ngày ký: 2026-10-01",
            "Ngày hiệu lực: 2026-11-01",
        ]
    )
    monkeypatch.setattr(
        worker.pipeline,
        "ocr_image",
        lambda data: {
            "text": "\n".join(lines),
            "lines": [{"text": line, "confidence": 0.95} for line in lines],
            "derived": b"derived-test-data",
            "quality_flags": [],
        },
    )
    assert worker.tick()
    current = system["client"].get("/api/v1/scan-sessions/" + capture["id"]).json()
    assert current["job"]["status"] == "SUCCEEDED", current
    document = system["client"].get("/api/v1/documents/" + current["document_ids"][0])
    assert document.status_code == 200, document.text
    return document.json(), page, job


def checked_body(doc):
    return {
        "version": doc["version"],
        "type_code": doc["type_code"],
        "title": doc["title"],
        "fields": [
            {
                "field_name": f["field_name"],
                "value": f["value"],
                "value_state": f["value_state"],
                "source_page_id": f["source_page_id"],
                "reviewed": True,
            }
            for f in doc["fields"]
        ],
    }


def save_checked(system, doc):
    response = system["client"].patch("/api/v1/documents/" + doc["id"], json=checked_body(doc))
    assert response.status_code == 200, response.text
    return response.json()


def test_auth_csrf_logout_and_origin(system):
    client = system["client"]
    assert client.get("/api/v1/employees").status_code == 401
    login(system)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "invalid"}).status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"Origin": "https://untrusted.invalid"}).status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/employees").status_code == 401


def test_upload_retry_does_not_create_duplicate_or_overwrite(system, image_bytes):
    client = login(system)
    capture, page = upload(system, image_bytes)
    path = f"/api/v1/scan-sessions/{capture['id']}/pages"
    args = {"client_page_id": page["client_page_id"], "page_order": 1}
    repeated = client.post(path, data=args, files={"file": ("other-name.jpg", image_bytes, "image/jpeg")})
    assert repeated.status_code == 200
    assert repeated.json()["id"] == page["id"]
    assert len(system["writes"]) == 1
    different = client.post(path, data=args, files={"file": ("page.png", image_bytes + b"extra", "image/png")})
    assert different.status_code == 409
    bad = client.post(
        path,
        data={"client_page_id": str(uuid4()), "page_order": 2},
        files={"file": ("fake.png", b"fake data", "image/png")},
    )
    assert bad.status_code == 422


def test_manifest_and_processing_retry_are_explicit(system, image_bytes):
    client = login(system)
    capture, page = upload(system, image_bytes)
    path = "/api/v1/scan-sessions/" + capture["id"]
    bad = client.post(
        path + "/finalize", json={"version": capture["version"], "pages": [{"id": page["id"], "sha256": "b" * 64}]}
    )
    assert bad.status_code == 409
    good = client.post(
        path + "/finalize",
        json={"version": capture["version"], "pages": [{"id": page["id"], "sha256": page["sha256"]}]},
    )
    assert good.status_code == 200
    body = {"idempotency_key": str(uuid4()), "groups": [{"title": "First", "page_ids": [page["id"]]}]}
    first = client.post(path + "/process", json=body)
    assert first.status_code == 200
    assert client.post(path + "/process", json=body).json()["id"] == first.json()["id"]
    body["groups"][0]["title"] = "Changed"
    assert client.post(path + "/process", json=body).status_code == 409


def test_review_verify_search_source_export_and_reopen(system, image_bytes, monkeypatch):
    client = login(system)
    doc, page, _ = process(system, image_bytes, monkeypatch)
    assert client.get("/api/v1/search").json()["total"] == 0
    assert (
        client.post(
            f"/api/v1/documents/{doc['id']}/verify", json={"version": doc["version"], "identity_confirmed": True}
        ).status_code
        == 422
    )
    body = checked_body(doc)
    next(field for field in body["fields"] if field["field_name"] == "contract_number")["value"] = "SYN-HR-CORRECTED"
    result = client.patch("/api/v1/documents/" + doc["id"], json=body)
    assert result.status_code == 200, result.text
    saved = result.json()
    verified = client.post(
        f"/api/v1/documents/{doc['id']}/verify", json={"version": saved["version"], "identity_confirmed": True}
    )
    assert verified.status_code == 200, verified.text
    assert client.get("/api/v1/search?q=CORRECTED").json()["total"] == 1
    assert client.get("/api/v1/search?q=hợp").json()["total"] == 1
    assert client.get(f"/api/v1/pages/{page['id']}/image").content == image_bytes
    exported = client.get(f"/api/v1/documents/{doc['id']}/export")
    assert exported.status_code == 200 and "SYN-HR-CORRECTED" in exported.text
    with system["factory"]() as db:
        prediction = db.scalar(select(FieldPrediction).where(FieldPrediction.field_name == "contract_number"))
        assert prediction.predicted_value == "SYN-HD-001"
    reopened = client.post(
        f"/api/v1/documents/{doc['id']}/reopen",
        json={"version": verified.json()["version"], "reason": "Check synthetic date"},
    )
    assert reopened.status_code == 200
    assert client.get("/api/v1/search").json()["total"] == 0
    assert len(client.get(f"/api/v1/documents/{doc['id']}/history").json()) >= 4


def test_denies_cross_scope_capture_and_operator_content_access(system, image_bytes, monkeypatch):
    client = login(system)
    doc, page, _ = process(system, image_bytes, monkeypatch)
    for role in ("outsider", "admin", "capture"):
        login(system, role)
        assert client.get("/api/v1/documents/" + doc["id"]).status_code == 404
        assert client.patch("/api/v1/documents/" + doc["id"], json=checked_body(doc)).status_code == 404
        assert client.get("/api/v1/pages/" + page["id"] + "/image").status_code == 404
    login(system, "outsider")
    assert client.get("/api/v1/search").json()["total"] == 0


def test_wrong_employee_blocks_publication(system, image_bytes, monkeypatch):
    client = login(system)
    doc, _, _ = process(system, image_bytes, monkeypatch, code="SYN-EMP-002")
    saved = save_checked(system, doc)
    result = client.post(
        f"/api/v1/documents/{doc['id']}/verify", json={"version": saved["version"], "identity_confirmed": True}
    )
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "IDENTITY_MISMATCH"
    assert client.get("/api/v1/search").json()["total"] == 0


def test_stale_review_and_unknown_documents_are_not_silently_accepted(system, image_bytes, monkeypatch):
    client = login(system)
    doc, _, _ = process(system, image_bytes, monkeypatch)
    save_checked(system, doc)
    assert client.patch("/api/v1/documents/" + doc["id"], json=checked_body(doc)).status_code == 409
    unknown, _, _ = process(system, image_bytes, monkeypatch, unknown=True)
    assert unknown["type_code"] == "unknown" and unknown["fields"] == []
    assert (
        client.post(
            f"/api/v1/documents/{unknown['id']}/verify",
            json={"version": unknown["version"], "identity_confirmed": True},
        ).status_code
        == 409
    )


def test_database_guards_history_and_verified_content(system, image_bytes, monkeypatch):
    client = login(system)
    doc, _, _ = process(system, image_bytes, monkeypatch)
    saved = save_checked(system, doc)
    result = client.post(
        f"/api/v1/documents/{doc['id']}/verify", json={"version": saved["version"], "identity_confirmed": True}
    )
    assert result.status_code == 200, result.text
    for statement in [
        "UPDATE field_predictions SET predicted_value='changed'",
        "DELETE FROM review_actions",
        "UPDATE document_fields SET value='changed'",
    ]:
        with system["factory"]() as db:
            with pytest.raises(DBAPIError):
                db.execute(text(statement))
                db.commit()


def test_expired_worker_lease_fences_previous_worker(system, image_bytes):
    login(system)
    _, _, job, _ = enqueue(system, image_bytes)
    job_id, old_token = worker.claim()
    with system["factory"]() as db:
        row = db.get(ProcessingJob, job_id)
        row.lease_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    worker.reap()
    claimed_id, new_token = worker.claim()
    assert claimed_id == job_id and new_token != old_token
    with pytest.raises(RuntimeError, match="LEASE_LOST"):
        worker.heartbeat(job_id, old_token)
    worker.heartbeat(job_id, new_token)
