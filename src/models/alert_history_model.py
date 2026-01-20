from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.connection import Base

class AlertHistory(Base):
    """
    SQLAlchemy model for the 'alert_history' table.
    This version correctly defines the composite index.
    """
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    alert_type = Column(String(50), nullable=False, index=True) # This single index is correct
    alert_level = Column(Integer, nullable=False, default=1)

    # Technical parameters
    ear_value = Column(Float, default=0)
    mar_value = Column(Float, default=0)
    head_pitch = Column(Float, default=0)
    head_yaw = Column(Float, default=0)

    duration_seconds = Column(Float, default=0)
    screenshot_path = Column(String(255), default=None)
    timestamp = Column(DateTime, default=func.now())

    # --- Relationship ---
    user = relationship("User", back_populates="alerts")

    # --- Table Arguments ---
    # Define composite indexes and other table-level settings here.
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, user_id={self.user_id}, type='{self.alert_type}')>"
