from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.config import get_database_url

engine = create_engine(get_database_url(), pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    with SessionLocal() as session:
        yield session
