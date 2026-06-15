import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    host_user_id: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16), default="multi")
    status: Mapped[str] = mapped_column(String(16), default="active")
    phase: Mapped[str] = mapped_column(String(16), default="lobby")
    categories: Mapped[list] = mapped_column(JSONB, default=list)
    current_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "questions.id", ondelete="SET NULL", use_alter=True
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(64))
    login: Mapped[str] = mapped_column(String(64))
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    author_login: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    text: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(16), default="user")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    fire_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    shown_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "user_id", name="uq_question_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "user_id", name="uq_vote_question_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(64))
    choice: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
