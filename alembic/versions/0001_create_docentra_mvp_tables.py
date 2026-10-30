"""create_docentra_mvp_tables

Revision ID: 0001
Revises: None
Create Date: 2026-10-29 23:25:27.049122

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "document_types",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "field_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("jsonb_typeof(field_schema) = 'object'", name="ck_document_types_field_schema"),
        sa.CheckConstraint("schema_version > 0", name="ck_document_types_schema_version"),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_code", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("btrim(employee_code) <> ''", name="ck_employees_code_not_blank"),
        sa.CheckConstraint("btrim(full_name) <> ''", name="ck_employees_name_not_blank"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), server_default=sa.text("'CAPTURE'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("role IN ('CAPTURE', 'REVIEWER', 'VIEWER', 'ADMIN')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_audit_logs_metadata"),
        sa.CheckConstraint("outcome IN ('ALLOWED', 'DENIED', 'FAILED')", name="ck_audit_logs_outcome"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_logs_actor_created_at", "audit_logs", ["actor_id", "created_at"], unique=False)
    op.create_index("idx_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index(
        "idx_audit_logs_resource_created_at", "audit_logs", ["resource_type", "resource_id", "created_at"], unique=False
    )
    op.create_table(
        "employee_access",
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("can_capture", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("can_review", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("can_view", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("granted_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("can_capture OR can_review OR can_view", name="ck_employee_access_has_permission"),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("employee_id", "user_id"),
    )
    op.create_index("idx_employee_access_user_id", "employee_access", ["user_id"], unique=False)
    op.create_table(
        "scan_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("client_session_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'UPLOADING'"), nullable=False),
        sa.Column("expected_page_count", sa.Integer(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADING', 'CANCELLED') OR (finalized_at IS NOT NULL AND expected_page_count IS NOT NULL)",
            name="ck_scan_sessions_finalized",
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADING', 'UPLOADED', 'PROCESSING', 'NEEDS_REVIEW', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_scan_sessions_status",
        ),
        sa.CheckConstraint(
            "expected_page_count IS NULL OR expected_page_count > 0", name="ck_scan_sessions_page_count"
        ),
        sa.CheckConstraint("version > 0", name="ck_scan_sessions_version"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by", "client_session_id", name="uq_scan_sessions_creator_client"),
    )
    op.create_index("idx_scan_sessions_created_by_status", "scan_sessions", ["created_by", "status"], unique=False)
    op.create_index(
        "idx_scan_sessions_employee_created_at", "scan_sessions", ["employee_id", "created_at"], unique=False
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.UUID(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=100), nullable=False),
        sa.Column("input_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'QUEUED'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column("lease_token", sa.UUID(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status <> 'RUNNING' AND lease_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_processing_jobs_lease",
        ),
        sa.CheckConstraint(
            "(status IN ('SUCCEEDED', 'FAILED', 'CANCELLED')) = (finished_at IS NOT NULL)",
            name="ck_processing_jobs_finished_at",
        ),
        sa.CheckConstraint("jsonb_typeof(input_manifest) = 'object'", name="ck_processing_jobs_manifest"),
        sa.CheckConstraint(
            "result_summary IS NULL OR jsonb_typeof(result_summary) = 'object'", name="ck_processing_jobs_summary"
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')", name="ck_processing_jobs_status"
        ),
        sa.CheckConstraint("attempt_count BETWEEN 0 AND max_attempts", name="ck_processing_jobs_attempt_count"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 5", name="ck_processing_jobs_max_attempts"),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["scan_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_processing_jobs_id_session"),
        sa.UniqueConstraint("session_id", "idempotency_key", name="uq_processing_jobs_session_key"),
    )
    op.create_index(
        "idx_processing_jobs_dispatch",
        "processing_jobs",
        ["available_at", "created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'QUEUED'"),
    )
    op.create_index(
        "uq_processing_jobs_active_session",
        "processing_jobs",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.create_table(
        "scan_pages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("client_page_id", sa.UUID(), nullable=False),
        sa.Column("page_order", sa.Integer(), nullable=True),
        sa.Column("original_storage_key", sa.String(length=1000), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("mime_type IN ('image/jpeg', 'image/png', 'image/webp')", name="ck_scan_pages_mime_type"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_scan_pages_sha256"),
        sa.CheckConstraint(
            "(discarded_at IS NULL AND page_order IS NOT NULL) OR (discarded_at IS NOT NULL AND page_order IS NULL)",
            name="ck_scan_pages_discarded_order",
        ),
        sa.CheckConstraint("byte_size > 0 AND width > 0 AND height > 0", name="ck_scan_pages_dimensions"),
        sa.CheckConstraint("page_order IS NULL OR page_order > 0", name="ck_scan_pages_order"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["scan_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_scan_pages_id_session"),
        sa.UniqueConstraint("original_storage_key"),
        sa.UniqueConstraint("session_id", "client_page_id", name="uq_scan_pages_session_client"),
        sa.UniqueConstraint(
            "session_id", "page_order", deferrable=True, initially="IMMEDIATE", name="uq_scan_pages_session_order"
        ),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("type_code", sa.String(length=50), server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("latest_job_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), server_default=sa.text("''"), nullable=False),
        sa.Column("review_status", sa.String(length=50), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("identity_confirmed_by", sa.UUID(), nullable=True),
        sa.Column("identity_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.UUID(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "(review_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL) OR (review_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_documents_verification_metadata",
        ),
        sa.CheckConstraint(
            "review_status <> 'VERIFIED' OR (type_code <> 'unknown' AND identity_confirmed_by IS NOT NULL)",
            name="ck_documents_verified_identity",
        ),
        sa.CheckConstraint(
            "review_status IN ('DRAFT', 'NEEDS_REVIEW', 'VERIFIED', 'REJECTED')", name="ck_documents_review_status"
        ),
        sa.CheckConstraint(
            "(identity_confirmed_by IS NULL) = (identity_confirmed_at IS NULL)",
            name="ck_documents_identity_confirmation",
        ),
        sa.CheckConstraint("version > 0", name="ck_documents_version"),
        sa.ForeignKeyConstraint(
            ["identity_confirmed_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_documents_latest_job_session",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["scan_sessions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["type_code"],
            ["document_types.code"],
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "session_id", name="uq_documents_id_session"),
    )
    op.create_index(
        "idx_documents_review_status_created_at", "documents", ["review_status", "created_at"], unique=False
    )
    op.create_index("idx_documents_session_id", "documents", ["session_id"], unique=False)
    op.create_index(
        "idx_documents_verified_type",
        "documents",
        ["type_code", "verified_at"],
        unique=False,
        postgresql_where=sa.text("review_status = 'VERIFIED'"),
    )
    op.create_table(
        "page_ocr_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("scan_page_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column(
            "blocks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("processed_storage_key", sa.String(length=1000), nullable=True),
        sa.Column(
            "quality_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple'::regconfig, text_content)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint("jsonb_typeof(blocks) = 'array'", name="ck_page_ocr_results_blocks"),
        sa.CheckConstraint("jsonb_typeof(quality_flags) = 'array'", name="ck_page_ocr_results_quality_flags"),
        sa.ForeignKeyConstraint(
            ["job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_page_ocr_results_job_session",
        ),
        sa.ForeignKeyConstraint(
            ["scan_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_page_ocr_results_scan_page_session",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "scan_page_id", name="uq_page_ocr_results_job_page"),
        sa.UniqueConstraint("processed_storage_key"),
    )
    op.create_index("idx_page_ocr_results_scan_page_id", "page_ocr_results", ["scan_page_id"], unique=False)
    op.create_index(
        "idx_page_ocr_results_search_vector",
        "page_ocr_results",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "document_pages",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("scan_page_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("page_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("page_order > 0", name="ck_document_pages_order"),
        sa.ForeignKeyConstraint(
            ["document_id", "session_id"],
            ["documents.id", "documents.session_id"],
            name="fk_document_pages_document_session",
        ),
        sa.ForeignKeyConstraint(
            ["scan_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_document_pages_scan_page_session",
        ),
        sa.PrimaryKeyConstraint("document_id", "scan_page_id"),
        sa.UniqueConstraint(
            "document_id", "page_order", deferrable=True, initially="IMMEDIATE", name="uq_document_pages_document_order"
        ),
        sa.UniqueConstraint("scan_page_id", name="uq_document_pages_scan_page"),
    )
    op.create_table(
        "field_predictions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("predicted_value", sa.Text(), nullable=True),
        sa.Column("value_state", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("source_page_id", sa.UUID(), nullable=True),
        sa.Column("source_bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "(value_state = 'PRESENT' AND predicted_value IS NOT NULL AND btrim(predicted_value) <> '') OR (value_state <> 'PRESENT' AND predicted_value IS NULL)",
            name="ck_field_predictions_value",
        ),
        sa.CheckConstraint("btrim(field_name) <> ''", name="ck_field_predictions_field_name"),
        sa.CheckConstraint(
            "source_bbox IS NULL OR (jsonb_typeof(source_bbox) = 'array' AND jsonb_array_length(source_bbox) = 4)",
            name="ck_field_predictions_bbox",
        ),
        sa.CheckConstraint(
            "value_state IN ('PRESENT', 'NOT_FOUND', 'UNREADABLE')", name="ck_field_predictions_value_state"
        ),
        sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_field_predictions_confidence"),
        sa.CheckConstraint(
            "source_bbox IS NULL OR source_page_id IS NOT NULL", name="ck_field_predictions_bbox_source"
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "session_id"],
            ["documents.id", "documents.session_id"],
            name="fk_field_predictions_document_session",
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "session_id"],
            ["processing_jobs.id", "processing_jobs.session_id"],
            name="fk_field_predictions_job_session",
        ),
        sa.ForeignKeyConstraint(
            ["source_page_id", "session_id"],
            ["scan_pages.id", "scan_pages.session_id"],
            name="fk_field_predictions_source_session",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "document_id", "field_name", name="uq_field_predictions_id_document_field"),
        sa.UniqueConstraint("job_id", "document_id", "field_name", name="uq_field_predictions_job_document_field"),
    )
    op.create_index("idx_field_predictions_document_job", "field_predictions", ["document_id", "job_id"], unique=False)
    op.create_table(
        "review_actions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column(
            "changes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "action IN ('EDIT_FIELDS', 'CHANGE_TYPE', 'REGROUP_PAGES', 'CONFIRM_IDENTITY', 'VERIFY', 'REOPEN', 'REJECT', 'ACCEPT_PROCESSING')",
            name="ck_review_actions_action",
        ),
        sa.CheckConstraint("jsonb_typeof(changes) = 'object'", name="ck_review_actions_changes"),
        sa.CheckConstraint("document_version > 0", name="ck_review_actions_document_version"),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "document_version", name="uq_review_actions_document_version"),
    )
    op.create_index("idx_review_actions_actor_id", "review_actions", ["actor_id"], unique=False)
    op.create_table(
        "document_fields",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=True),
        sa.Column("value", sa.String(length=500), nullable=True),
        sa.Column("value_state", sa.String(length=50), nullable=False),
        sa.Column("source_page_id", sa.UUID(), nullable=True),
        sa.Column("source_bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("review_status", sa.String(length=50), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.CheckConstraint(
            "(review_status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (review_status <> 'PENDING' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_document_fields_review_metadata",
        ),
        sa.CheckConstraint(
            "(value_state = 'PRESENT' AND value IS NOT NULL AND btrim(value) <> '') OR (value_state <> 'PRESENT' AND value IS NULL)",
            name="ck_document_fields_value",
        ),
        sa.CheckConstraint("btrim(field_name) <> ''", name="ck_document_fields_field_name"),
        sa.CheckConstraint(
            "review_status IN ('PENDING', 'CONFIRMED', 'CORRECTED')", name="ck_document_fields_review_status"
        ),
        sa.CheckConstraint(
            "source_bbox IS NULL OR (jsonb_typeof(source_bbox) = 'array' AND jsonb_array_length(source_bbox) = 4)",
            name="ck_document_fields_bbox",
        ),
        sa.CheckConstraint(
            "value_state IN ('PRESENT', 'NOT_FOUND', 'UNREADABLE', 'NOT_APPLICABLE')",
            name="ck_document_fields_value_state",
        ),
        sa.CheckConstraint("source_bbox IS NULL OR source_page_id IS NOT NULL", name="ck_document_fields_bbox_source"),
        sa.ForeignKeyConstraint(
            ["document_id", "source_page_id"],
            ["document_pages.document_id", "document_pages.scan_page_id"],
            name="fk_document_fields_source_document",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id", "document_id", "field_name"],
            ["field_predictions.id", "field_predictions.document_id", "field_predictions.field_name"],
            name="fk_document_fields_prediction_field",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("document_id", "field_name"),
    )
    op.create_index(
        "idx_document_fields_lookup",
        "document_fields",
        ["field_name", "value"],
        unique=False,
        postgresql_where=sa.text("value IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "idx_document_fields_lookup", table_name="document_fields", postgresql_where=sa.text("value IS NOT NULL")
    )
    op.drop_table("document_fields")
    op.drop_index("idx_review_actions_actor_id", table_name="review_actions")
    op.drop_table("review_actions")
    op.drop_index("idx_field_predictions_document_job", table_name="field_predictions")
    op.drop_table("field_predictions")
    op.drop_table("document_pages")
    op.drop_index("idx_page_ocr_results_search_vector", table_name="page_ocr_results", postgresql_using="gin")
    op.drop_index("idx_page_ocr_results_scan_page_id", table_name="page_ocr_results")
    op.drop_table("page_ocr_results")
    op.drop_index(
        "idx_documents_verified_type", table_name="documents", postgresql_where=sa.text("review_status = 'VERIFIED'")
    )
    op.drop_index("idx_documents_session_id", table_name="documents")
    op.drop_index("idx_documents_review_status_created_at", table_name="documents")
    op.drop_table("documents")
    op.drop_table("scan_pages")
    op.drop_index(
        "uq_processing_jobs_active_session",
        table_name="processing_jobs",
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.drop_index(
        "idx_processing_jobs_dispatch", table_name="processing_jobs", postgresql_where=sa.text("status = 'QUEUED'")
    )
    op.drop_table("processing_jobs")
    op.drop_index("idx_scan_sessions_employee_created_at", table_name="scan_sessions")
    op.drop_index("idx_scan_sessions_created_by_status", table_name="scan_sessions")
    op.drop_table("scan_sessions")
    op.drop_index("idx_employee_access_user_id", table_name="employee_access")
    op.drop_table("employee_access")
    op.drop_index("idx_audit_logs_resource_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_actor_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("employees")
    op.drop_table("document_types")
