from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.connection import Base

class DrivingSession(Base):
    """
    SQLAlchemy model for the 'driving_sessions' table.
    """
    __tablename__ = "driving_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, default=None)

    total_alerts = Column(Integer, default=0)
    drowsy_count = Column(Integer, default=0)
    yawn_count = Column(Integer, default=0)

    status = Column(String(20), default='ACTIVE')
    notes = Column(Text, default=None)

    # --- Relationship ---
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<DrivingSession(id={self.id}, user_id={self.user_id}, start='{self.start_time}')>"
