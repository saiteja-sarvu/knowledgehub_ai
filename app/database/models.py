from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database.db import Base
from datetime import datetime


class User(Base):
    __tablename__ = "kai_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    password = Column(String(255))
    role = Column(String(20), default="user")


class Document(Base):
    __tablename__ = "kai_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    filename = Column(String(255))
    original_filename = Column(String(255))
    file_type = Column(String(50))
    file_size = Column(Integer)
    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class ChatHistory(Base):
    __tablename__ = "kai_chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )