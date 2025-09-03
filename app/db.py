import os
from dotenv import load_dotenv
load_dotenv(override=True)
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Text,
    Date, DateTime, func, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env")

# Engine & session factory
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# ORM base
Base = declarative_base()

# Tables
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    tz = Column(String(64), default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DailyLog(Base):
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    date = Column(Date, server_default=func.current_date())
    text_log = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
