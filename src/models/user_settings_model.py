from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.connection import Base

class UserSettings(Base):
    """
    SQLAlchemy model for the 'user_settings' table.
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Detection thresholds
    ear_threshold = Column(Float, default=0.25)
    mar_threshold = Column(Float, default=0.70)
    head_threshold = Column(Float, default=25.0)

    # System settings
    alert_volume = Column(Float, default=0.8)
    sensitivity_level = Column(String(10), default='MEDIUM') # LOW, MEDIUM, HIGH
    enable_sound = Column(Boolean, default=True)
    enable_vibration = Column(Boolean, default=True)
    sunglasses_mode = Column(Boolean, default=False)  # Chế độ kính râm thủ công

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # --- Relationship ---
    # This creates a "one-to-one" relationship.
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"
