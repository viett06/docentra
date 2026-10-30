import os
from io import BytesIO
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.db.config import PROJECT_ROOT, get_database_url


@pytest.fixture
def image_bytes():
    output = BytesIO()
    Image.new("RGB", (300, 400), "white").save(output, "PNG")
    return output.getvalue()


@pytest.fixture
def system(monkeypatch):
    if os.getenv("DOCENTRA_RUN_DB_TESTS") != "1":
        pytest.skip("Set DOCENTRA_RUN_DB_TESTS=1 to run isolated PostgreSQL integration tests")
    url = get_database_url()
    assert url.host in {"127.0.0.1", "localhost"}, (
        "Integration tests create temporary databases only on local PostgreSQL"
    )
    name = "docentra_test_" + uuid4().hex[:12]
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    test_url = url.set(database=name)
    test_engine = create_engine(test_url, hide_parameters=True)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)
    try:
        monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
        command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")
        from app import worker
        from app.db import session as db_module
        from app.model import Employee, EmployeeAccess, User
        from app.services import security, storage
        from main import app

        monkeypatch.setattr(db_module, "SessionLocal", factory)
        monkeypatch.setattr(security, "SessionLocal", factory)
        monkeypatch.setattr(worker, "SessionLocal", factory)
        objects = {}
        writes = []

        def put(key, data, mime):
            objects[key] = data
            writes.append(key)

        monkeypatch.setattr(storage, "put_object", put)
        monkeypatch.setattr(storage, "read_object", lambda key: objects[key])
        with factory() as db:
            users = {}
            encoded = security.password_hasher.hash("TestDocentra!2026")
            for role in ("reviewer", "capture", "viewer", "outsider", "admin"):
                row = User(
                    id=uuid4(),
                    email=role + "@test.local",
                    full_name="Synthetic " + role,
                    password_hash=encoded,
                    role="VIEWER" if role == "outsider" else role.upper(),
                )
                db.add(row)
                users[role] = row
            employee = Employee(id=uuid4(), employee_code="SYN-EMP-001", full_name="Synthetic employee")
            db.add(employee)
            db.flush()
            for role in ("reviewer", "capture", "viewer"):
                db.add(
                    EmployeeAccess(
                        employee_id=employee.id,
                        user_id=users[role].id,
                        granted_by=users["admin"].id,
                        can_capture=role in {"capture", "reviewer"},
                        can_review=role == "reviewer",
                        can_view=role in {"reviewer", "viewer"},
                    )
                )
            db.commit()
        with TestClient(app, raise_server_exceptions=False) as client:
            yield {
                "client": client,
                "factory": factory,
                "employee": employee,
                "users": users,
                "objects": objects,
                "writes": writes,
            }
    finally:
        test_engine.dispose()
        with admin.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        admin.dispose()
