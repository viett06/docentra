"""Durable PostgreSQL queue. Duplicate wakeups are harmless; leases fence old workers."""

import argparse
import hashlib
import logging
import time
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.model import (
    Document,
    DocumentField,
    DocumentPage,
    DocumentType,
    Employee,
    FieldPrediction,
    PageOcrResult,
    ProcessingJob,
    ReviewAction,
    ScanPage,
    ScanSession,
)
from app.services import pipeline, storage
from app.services.security import utcnow

logger = logging.getLogger("docentra.worker")


def reap():
    with SessionLocal() as db:
        rows = db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "RUNNING", ProcessingJob.lease_expires_at < utcnow())
            .with_for_update(skip_locked=True)
        ).all()
        for job in rows:
            job.lease_token, job.lease_expires_at = None, None
            if job.attempt_count >= job.max_attempts:
                job.status, job.finished_at, job.error_code = "FAILED", utcnow(), "LEASE_EXPIRED"
                db.get(ScanSession, job.session_id).status = "FAILED"
            else:
                job.status, job.available_at = "QUEUED", utcnow()
        db.commit()


def claim():
    with SessionLocal() as db:
        job = db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.status == "QUEUED", ProcessingJob.available_at <= utcnow())
            .order_by(ProcessingJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        job.status, job.lease_token = "RUNNING", uuid4()
        job.lease_expires_at = utcnow() + timedelta(seconds=get_settings().WORKER_LEASE_SECONDS)
        job.attempt_count += 1
        job.started_at = job.started_at or utcnow()
        db.commit()
        return job.id, job.lease_token


def heartbeat(job_id, token):
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id, with_for_update=True)
        if job.status != "RUNNING" or job.lease_token != token or job.lease_expires_at <= utcnow():
            raise RuntimeError("LEASE_LOST")
        job.lease_expires_at = utcnow() + timedelta(seconds=get_settings().WORKER_LEASE_SECONDS)
        db.commit()


def run_job(job_id, token):
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        manifest, session_id = job.input_manifest, job.session_id
        capture = db.get(ScanSession, session_id)
        employee_code = db.get(Employee, capture.employee_id).employee_code
        inputs = {
            str(p.id): (p.original_storage_key, p.sha256)
            for p in db.scalars(select(ScanPage).where(ScanPage.session_id == session_id))
        }
    outputs = {}
    for page_id, checksum in manifest["pages"].items():
        heartbeat(job_id, token)
        key, recorded = inputs[page_id]
        data = storage.read_object(key)
        if recorded != checksum or hashlib.sha256(data).hexdigest() != checksum:
            raise RuntimeError("IMAGE_INTEGRITY")
        output = pipeline.ocr_image(data)
        output["page_id"] = page_id
        output["derived_key"] = f"derived/{job_id}/{page_id}.png"
        storage.put_object(output["derived_key"], output.pop("derived"), "image/png")
        outputs[page_id] = output
    summaries = {}
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id, with_for_update=True)
        if job.status != "RUNNING" or job.lease_token != token or job.lease_expires_at <= utcnow():
            raise RuntimeError("LEASE_LOST")
        capture = db.get(ScanSession, session_id, with_for_update=True)
        if capture.version != manifest["session_version"] or capture.status != "PROCESSING":
            raise RuntimeError("STALE_MANIFEST")
        for page_id, output in outputs.items():
            db.add(
                PageOcrResult(
                    job_id=job.id,
                    scan_page_id=UUID(page_id),
                    session_id=session_id,
                    engine_version="tesseract-5-vie-eng",
                    text_content=output["text"],
                    blocks=output["lines"],
                    processed_storage_key=output["derived_key"],
                    quality_flags=output["quality_flags"],
                )
            )
        for group in manifest["groups"]:
            document = db.get(Document, UUID(group["document_id"]), with_for_update=True)
            if document.review_status != "DRAFT":
                raise RuntimeError("DOCUMENT_CHANGED")
            actual_pages = [
                str(p)
                for p in db.scalars(
                    select(DocumentPage.scan_page_id)
                    .where(DocumentPage.document_id == document.id)
                    .order_by(DocumentPage.page_order)
                )
            ]
            if actual_pages != group["page_ids"]:
                raise RuntimeError("STALE_GROUPING")
            selected = [outputs[p] for p in group["page_ids"]]
            text = "\n".join(o["text"] for o in selected)
            type_code = pipeline.classify(text)
            identity_match, identity_note = pipeline.identity_check(text, employee_code)
            predictions = pipeline.extract(type_code, selected)
            for field in predictions:
                prediction = FieldPrediction(
                    id=uuid4(),
                    document_id=document.id,
                    session_id=session_id,
                    job_id=job.id,
                    field_name=field["field_name"],
                    predicted_value=field["value"],
                    value_state=field["value_state"],
                    confidence=field["confidence"],
                    source_page_id=UUID(field["source_page_id"]) if field["source_page_id"] else None,
                )
                db.add(prediction)
                db.flush()
                db.add(
                    DocumentField(
                        document_id=document.id,
                        field_name=prediction.field_name,
                        prediction_id=prediction.id,
                        value=prediction.predicted_value,
                        value_state=prediction.value_state,
                        source_page_id=prediction.source_page_id,
                    )
                )
            document.type_code, document.latest_job_id, document.review_status = type_code, job.id, "NEEDS_REVIEW"
            if not document.title:
                document.title = db.get(DocumentType, type_code).name
            document.version += 1
            db.add(
                ReviewAction(
                    document_id=document.id,
                    actor_id=job.requested_by,
                    document_version=document.version,
                    action="ACCEPT_PROCESSING",
                    changes={"job_id": str(job.id), "type_code": type_code},
                )
            )
            summaries[str(document.id)] = {
                "predicted_type": type_code,
                "identity_match": identity_match,
                "identity_note": identity_note,
            }
        job.result_summary = {"documents": summaries, "page_count": len(outputs)}
        job.status, job.finished_at = "SUCCEEDED", utcnow()
        job.lease_token, job.lease_expires_at = None, None
        capture.status = "NEEDS_REVIEW"
        db.commit()


def fail_job(job_id, token, code):
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id, with_for_update=True)
        if job.status != "RUNNING" or job.lease_token != token:
            return
        job.error_code, job.lease_token, job.lease_expires_at = code, None, None
        if job.attempt_count >= job.max_attempts:
            job.status, job.finished_at = "FAILED", utcnow()
            db.get(ScanSession, job.session_id).status = "FAILED"
        else:
            job.status, job.available_at = "QUEUED", utcnow() + timedelta(seconds=2**job.attempt_count)
        db.commit()


def tick():
    reap()
    claimed = claim()
    if not claimed:
        return False
    job_id, token = claimed
    try:
        run_job(job_id, token)
        logger.info("job_succeeded job_id=%s", job_id)
    except Exception as error:
        # OCR output, image data and SQL parameter values must not enter worker logs.
        code = str(error) if isinstance(error, RuntimeError) and str(error).isupper() else type(error).__name__.upper()
        logger.warning("job_failed job_id=%s error_code=%s", job_id, code)
        fail_job(job_id, token, code[:100])
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    while True:
        try:
            worked = tick()
        except Exception as error:
            logger.warning("queue_unavailable error_code=%s", type(error).__name__)
            worked = False
        if args.once:
            return
        if not worked:
            time.sleep(1)


if __name__ == "__main__":
    main()
