"""Seed the MVP document type catalog.

Revision ID: 0002
Revises: 0001
"""

import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None

DOCUMENT_TYPES = (
    ("unknown", "Chưa xác định", {}),
    (
        "employment_contract",
        "Hợp đồng lao động",
        {
            "contract_number": {"label": "Số hợp đồng", "type": "string", "required": True},
            "contract_type": {"label": "Loại hợp đồng", "type": "string", "required": False},
            "signed_date": {"label": "Ngày ký", "type": "date", "required": True},
            "effective_date": {"label": "Ngày hiệu lực", "type": "date", "required": False},
        },
    ),
    (
        "degree",
        "Bằng cấp",
        {
            "degree_name": {"label": "Tên bằng", "type": "string", "required": True},
            "major": {"label": "Chuyên ngành", "type": "string", "required": False},
            "issuer": {"label": "Cơ sở cấp", "type": "string", "required": True},
            "issue_date": {"label": "Ngày cấp", "type": "date", "required": False},
        },
    ),
    (
        "practice_certificate",
        "Chứng chỉ hành nghề",
        {
            "certificate_number": {"label": "Số chứng chỉ", "type": "string", "required": True},
            "certificate_type": {"label": "Loại chứng chỉ", "type": "string", "required": False},
            "issue_date": {"label": "Ngày cấp", "type": "date", "required": True},
            "issuer": {"label": "Cơ quan cấp", "type": "string", "required": False},
        },
    ),
)


def _catalog_table() -> sa.TableClause:
    return sa.table(
        "document_types",
        sa.column("code", sa.String(50)),
        sa.column("name", sa.String(255)),
        sa.column("field_schema", postgresql.JSONB),
    )


def upgrade() -> None:
    catalog = _catalog_table()
    for code, name, fields in DOCUMENT_TYPES:
        op.execute(
            catalog.insert().values(
                code=op.inline_literal(code),
                name=op.inline_literal(name),
                field_schema=sa.cast(op.inline_literal(json.dumps(fields, ensure_ascii=False)), postgresql.JSONB),
            )
        )


def downgrade() -> None:
    catalog = _catalog_table()
    op.execute(catalog.delete().where(catalog.c.code.in_([code for code, _, _ in DOCUMENT_TYPES])))
