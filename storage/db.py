import os
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "./output/governance_data.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChecklistItem(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="anonymous", index=True)
    query = Column(Text, nullable=True)
    domain = Column(String, index=True)
    requirement = Column(Text, nullable=True)
    source_section = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized via SQLAlchemy at {DB_PATH}")

def save_checklist(query: str, checklist_items: list, user_id: str = "anonymous"):
    if not checklist_items:
        return
    try:
        with SessionLocal() as session:
            records = []
            for it in checklist_items:
                record = ChecklistItem(
                    user_id=user_id,
                    query=query,
                    domain=it.get("domain", "general"),
                    requirement=it.get("item", ""),
                    source_section=str(it.get("source_section", "")),
                    raw_json=json.dumps(it, ensure_ascii=False)
                )
                records.append(record)

            session.add_all(records)
            session.commit()
            logger.info(f"Saved {len(records)} checklist items to DB using SQLAlchemy.")
    except Exception as e:
        logger.error(f"Failed to save checklist to DB: {e}")
