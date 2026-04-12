from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    discord_id: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.DEVELOPER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    projects: Mapped[list[Project]] = relationship(back_populates="owner")
    tasks: Mapped[list[Task]] = relationship(back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="projects")
    tasks: Mapped[list[Task]] = relationship(back_populates="project")

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority: Mapped[str] = mapped_column(String, default="medium")
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"))
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="tasks")
    assignee: Mapped[Optional[User]] = relationship(back_populates="tasks")


class AccessProvision(Base):
    """Phase 3: Agent Access + Shop Bridge.

    One row per provisioned sandbox. source_id ties back to the
    Course shop_purchases row — same UNIQUE guard as Phase 2.
    api_key is the credential sent to the student via Discord DM.
    """
    __tablename__ = "access_provisions"
    __table_args__ = (
        UniqueConstraint("api_key",   name="uq_access_provisions_api_key"),
        UniqueConstraint("source_id", name="uq_access_provisions_source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    discord_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    provision_type: Mapped[str] = mapped_column(String(64), default="agent_sandbox", nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission_control_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[Optional[User]] = relationship("User", foreign_keys=[user_id])
