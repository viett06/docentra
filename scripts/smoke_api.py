"""Exercise the local synthetic MVP through HTTP, MinIO and the real OCR worker."""

import argparse
import ipaddress
import json
import ssl
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.demo.fixtures import values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--employee-code", default="SYN-EMP-002")
    parser.add_argument("--ca-file", type=Path, help="Local demo CA for HTTPS on a private Wi-Fi IPv4 address")
    parser.add_argument(
        "--verify", action="store_true", help="Verify only synthetic fields that exactly match renderer ground truth"
    )
    args = parser.parse_args()
    target = urlparse(args.url)
    local = target.hostname in {"127.0.0.1", "localhost"}
    try:
        address = ipaddress.IPv4Address(target.hostname or "")
        private = any(address in ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
    except ipaddress.AddressValueError:
        private = False
    if not (local or private and target.scheme == "https" and args.ca_file) or not args.employee_code.startswith(
        "SYN-EMP-"
    ):
        parser.error("Use localhost, or private Wi-Fi HTTPS with --ca-file, and a SYN employee")
    if (
        target.scheme not in {"http", "https"}
        or target.username
        or target.password
        or target.query
        or target.fragment
        or target.path not in {"", "/"}
    ):
        parser.error("Use an HTTP(S) origin without credentials, path, query or fragment")
    settings = get_settings()
    if not settings.DEMO_MODE:
        parser.error("DEMO_MODE must be enabled")
    context = ssl.create_default_context(cafile=str(args.ca_file)) if args.ca_file else True
    with httpx.Client(
        base_url=args.url,
        timeout=30,
        verify=context,
        trust_env=False,
        headers={"Origin": f"{target.scheme}://{target.netloc}"},
    ) as client:

        def request(method, path, **kwargs):
            response = client.request(method, "/api/v1" + path, **kwargs)
            response.raise_for_status()
            return response

        auth = request(
            "POST", "/auth/login", json={"email": "reviewer@docentra.local", "password": settings.DEMO_PASSWORD}
        ).json()
        client.headers["X-CSRF-Token"] = auth["csrf_token"]
        employee = next(
            row for row in request("GET", "/employees").json() if row["employee_code"] == args.employee_code
        )
        capture = request(
            "POST", "/scan-sessions", json={"employee_id": employee["id"], "client_session_id": str(uuid4())}
        ).json()
        receipts, groups = [], []
        kinds = ["employment_contract", "degree", "practice_certificate", "unknown"]
        for code in kinds:
            page_ids = []
            count = 2 if code == "employment_contract" else 1
            for page in range(1, count + 1):
                image = request("GET", f"/demo/samples/{employee['id']}/{code}/{page}?page_count={count}").content
                receipt = request(
                    "POST",
                    f"/scan-sessions/{capture['id']}/pages",
                    data={"client_page_id": str(uuid4()), "page_order": str(len(receipts) + 1)},
                    files={"file": ("synthetic.png", image, "image/png")},
                ).json()
                receipts.append(receipt)
                page_ids.append(receipt["id"])
            title = {
                "employment_contract": "Hợp đồng lao động (mẫu)",
                "degree": "Bằng cấp (mẫu)",
                "practice_certificate": "Chứng chỉ hành nghề (mẫu)",
                "unknown": "Giấy tờ chờ phân loại (mẫu)",
            }[code]
            groups.append({"title": title, "page_ids": page_ids})
        request(
            "POST",
            f"/scan-sessions/{capture['id']}/finalize",
            json={"version": capture["version"], "pages": [{"id": p["id"], "sha256": p["sha256"]} for p in receipts]},
        )
        request(
            "POST", f"/scan-sessions/{capture['id']}/process", json={"idempotency_key": str(uuid4()), "groups": groups}
        )
        deadline = time.monotonic() + 180
        while True:
            current = request("GET", "/scan-sessions/" + capture["id"]).json()
            if current["job"]["status"] == "SUCCEEDED":
                break
            if current["job"]["status"] == "FAILED" or time.monotonic() > deadline:
                raise RuntimeError("Worker did not complete the smoke job")
            time.sleep(1)
        outcomes = []
        for document_id in current["document_ids"]:
            doc = request("GET", "/documents/" + document_id).json()
            assert request("GET", "/pages/" + doc["pages"][0]["id"] + "/image").content
            correct = False
            if doc["type_code"] != "unknown":
                expected = values(doc["type_code"], int(args.employee_code.rsplit("-", 1)[1]))
                correct = {f["field_name"]: f["value"] for f in doc["fields"]} == expected
                if args.verify and correct and doc["identity_match"] is True:
                    saved = request(
                        "PATCH",
                        "/documents/" + document_id,
                        json={
                            "version": doc["version"],
                            "title": doc["title"],
                            "type_code": doc["type_code"],
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
                        },
                    ).json()
                    doc = request(
                        "POST",
                        "/documents/" + document_id + "/verify",
                        json={"version": saved["version"], "identity_confirmed": True},
                    ).json()
            outcomes.append(
                {
                    "id": doc["id"],
                    "type": doc["type_code"],
                    "fields_match_synthetic_truth": correct,
                    "status": doc["review_status"],
                    "pages": len(doc["pages"]),
                }
            )
        assert {d["type"] for d in outcomes} == set(kinds)
        print(
            json.dumps(
                {"session_id": capture["id"], "real_ocr": True, "synthetic_only": True, "documents": outcomes},
                ensure_ascii=False,
                indent=2,
            )
        )
        request("POST", "/auth/logout")


if __name__ == "__main__":
    main()
