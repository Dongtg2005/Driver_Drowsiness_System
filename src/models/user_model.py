from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.connection import Base

class User(Base):
    """
    SQLAlchemy model for the 'users' table.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False, comment='Hash password')
    full_name = Column(String(100), default=None)
    email = Column(String(100), default=None)
    phone = Column(String(20), default=None)
    avatar = Column(String(255), default=None)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, default=None)

    # --- Relationships ---
    # This creates a "one-to-many" relationship. One User can have many Alerts.
    # The `back_populates` argument specifies that the `Alert` model will have a `user` attribute
    # that links back to this user. `cascade="all, delete-orphan"` means that if a user is deleted,
    # all of their associated alerts will also be deleted.
    alerts = relationship("AlertHistory", back_populates="user", cascade="all, delete-orphan")

    # One User has one Settings profile
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # One User can have many Driving Sessions
    sessions = relationship("DrivingSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
