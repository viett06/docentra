"""Protect original scans, approved content and immutable processing history.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION docentra_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END; $$;
    """)
    for table in ("audit_logs", "review_actions", "field_predictions", "page_ocr_results"):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION docentra_append_only()"
        )
    op.execute("""
        CREATE FUNCTION docentra_guard_content() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target_id uuid; parent_state text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.document_id <> OLD.document_id THEN
                RAISE EXCEPTION 'Document ownership is immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN target_id := OLD.document_id;
            ELSE target_id := NEW.document_id; END IF;
            SELECT review_status INTO parent_state FROM documents WHERE id=target_id FOR UPDATE;
            IF parent_state IN ('VERIFIED','REJECTED') THEN
                RAISE EXCEPTION 'Reopen the document before editing';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$;
    """)
    for table in ("document_fields", "document_pages"):
        op.execute(
            f"CREATE TRIGGER {table}_guard BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION docentra_guard_content()"
        )
    op.execute("""
        CREATE FUNCTION docentra_guard_scan() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target_id uuid; parent_state text;
        BEGIN
            IF TG_OP = 'UPDATE' AND (
                NEW.session_id IS DISTINCT FROM OLD.session_id OR NEW.id IS DISTINCT FROM OLD.id OR
                NEW.original_storage_key IS DISTINCT FROM OLD.original_storage_key OR
                NEW.sha256 IS DISTINCT FROM OLD.sha256 OR NEW.client_page_id IS DISTINCT FROM OLD.client_page_id OR
                NEW.byte_size IS DISTINCT FROM OLD.byte_size OR NEW.mime_type IS DISTINCT FROM OLD.mime_type OR
                NEW.width IS DISTINCT FROM OLD.width OR NEW.height IS DISTINCT FROM OLD.height
            ) THEN RAISE EXCEPTION 'Original scan metadata is immutable'; END IF;
            IF TG_OP = 'DELETE' THEN target_id := OLD.session_id;
            ELSE target_id := NEW.session_id; END IF;
            SELECT status INTO parent_state FROM scan_sessions WHERE id=target_id FOR UPDATE;
            IF parent_state <> 'UPLOADING' THEN RAISE EXCEPTION 'Capture is finalized'; END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER scan_pages_guard BEFORE INSERT OR UPDATE OR DELETE ON scan_pages
            FOR EACH ROW EXECUTE FUNCTION docentra_guard_scan();
    """)
    op.execute("""
        CREATE FUNCTION docentra_guard_session() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.employee_id IS DISTINCT FROM OLD.employee_id OR NEW.created_by IS DISTINCT FROM OLD.created_by OR
                NEW.client_session_id IS DISTINCT FROM OLD.client_session_id THEN
                RAISE EXCEPTION 'Capture ownership is immutable';
            END IF;
            IF OLD.finalized_at IS NOT NULL AND (
                NEW.finalized_at IS DISTINCT FROM OLD.finalized_at OR NEW.status='UPLOADING' OR
                NEW.expected_page_count IS DISTINCT FROM OLD.expected_page_count
            ) THEN RAISE EXCEPTION 'Finalized capture cannot be reopened'; END IF;
            RETURN NEW;
        END; $$;
        CREATE TRIGGER scan_sessions_guard BEFORE UPDATE ON scan_sessions
            FOR EACH ROW EXECUTE FUNCTION docentra_guard_session();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER scan_sessions_guard ON scan_sessions")
    op.execute("DROP FUNCTION docentra_guard_session()")
    op.execute("DROP TRIGGER scan_pages_guard ON scan_pages")
    op.execute("DROP FUNCTION docentra_guard_scan()")
    for table in ("document_fields", "document_pages"):
        op.execute(f"DROP TRIGGER {table}_guard ON {table}")
    op.execute("DROP FUNCTION docentra_guard_content()")
    for table in ("audit_logs", "review_actions", "field_predictions", "page_ocr_results"):
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP FUNCTION docentra_append_only()")
