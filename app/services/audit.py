from uuid import uuid4

from sqlalchemy.orm import Session

from app.model import AuditLog


def audit(session: Session, actor, action: str, resource_type: str, resource_id=None, outcome="ALLOWED", **metadata):
    session.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            request_id=uuid4(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            audit_metadata=metadata,
        )
    )
