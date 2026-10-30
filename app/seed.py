from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.model import Employee, EmployeeAccess, User
from app.services.security import password_hasher
from app.services.storage import ensure_bucket


def main():
    settings = get_settings()
    if not settings.DEMO_MODE or len(settings.DEMO_PASSWORD) < 12:
        raise RuntimeError("Demo seed requires DEMO_MODE=true and DEMO_PASSWORD of at least 12 characters")
    ensure_bucket()
    people = [
        "Nguyễn An",
        "Trần Bình",
        "Lê Chi",
        "Phạm Dung",
        "Hoàng Giang",
        "Đỗ Hà",
        "Vũ Huy",
        "Bùi Linh",
        "Đinh Mai",
        "Ngô Nam",
    ]
    with SessionLocal() as db:
        accounts = {}
        for name, role in [
            ("capture", "CAPTURE"),
            ("reviewer", "REVIEWER"),
            ("viewer", "VIEWER"),
            ("admin", "ADMIN"),
            ("outsider", "VIEWER"),
        ]:
            email = f"{name}@docentra.local"
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    id=uuid4(),
                    email=email,
                    full_name={
                        "capture": "Lan · Số hóa",
                        "reviewer": "Minh · HR",
                        "viewer": "An · Tra cứu",
                        "admin": "Quản trị vận hành",
                        "outsider": "Tài khoản ngoài phạm vi",
                    }[name],
                    role=role,
                    password_hash=password_hasher.hash(settings.DEMO_PASSWORD),
                )
                db.add(user)
                db.flush()
            accounts[name] = user
        for number in range(1, 31):
            code = f"SYN-EMP-{number:03d}"
            employee = db.scalar(select(Employee).where(Employee.employee_code == code))
            if not employee:
                employee = Employee(
                    id=uuid4(),
                    employee_code=code,
                    full_name=f"{people[(number - 1) % len(people)]} {number:02d} (giả lập)",
                )
                db.add(employee)
                db.flush()
            for name in ["capture", "reviewer", "viewer"]:
                user = accounts[name]
                if not db.get(EmployeeAccess, (employee.id, user.id)):
                    db.add(
                        EmployeeAccess(
                            employee_id=employee.id,
                            user_id=user.id,
                            can_capture=name in {"capture", "reviewer"},
                            can_review=name == "reviewer",
                            can_view=name in {"reviewer", "viewer"},
                            granted_by=accounts["admin"].id,
                        )
                    )
        db.commit()
    print("Synthetic demo accounts and 30 employees are ready; existing passwords/data were preserved.")


if __name__ == "__main__":
    main()
