from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, func
from app.db.base import Base


class GraduationEvent(Base):
    __tablename__ = 'graduation_events'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    discord_id = Column(String(32), nullable=True, index=True)
    source_id = Column(Text, unique=True, nullable=False)  # idempotency key = course graduation_events.id
    badge_slug = Column(String(64), default='hyper-graduate')
    tokens_awarded = Column(Integer, default=500)
    portfolio_url = Column(Text, nullable=True)
    discord_role_assigned = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
