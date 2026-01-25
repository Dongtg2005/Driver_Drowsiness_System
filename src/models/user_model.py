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

# --- Repository Helper for Compatibility with Controllers ---
class UserRepository:
    """
    Helper class to bridge the gap between SQLAlchemy ORM and legacy controller calls.
    Provides a simplified API for controllers to get/set user settings.
    """
    @staticmethod
    def get_user_settings(user_id: int) -> dict:
        """
        Get user settings as a dictionary.
        Returns None if user or settings not found.
        """
        from src.database.connection import SessionLocal
        from src.models.user_settings_model import UserSettings
        from config import config
        
        db = SessionLocal()
        try:
            # Join not strictly needed if we just want settings by user_id
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                return {
                    'ear_threshold': settings.ear_threshold,
                    'mar_threshold': settings.mar_threshold,
                    'head_threshold': settings.head_threshold,
                    'alert_volume': settings.alert_volume,
                    'sensitivity': settings.sensitivity_level,
                    'enable_sound': settings.enable_sound,
                    'sunglasses_mode': settings.sunglasses_mode
                }
            return None
        except Exception as e:
            print(f"❌ Error getting settings for user {user_id}: {e}")
            return None
        finally:
            db.close()

    @staticmethod
    def update_settings(user_id: int, updates: dict) -> bool:
        """
        Update specific settings for a user.
        updates: dict of keys to update (e.g. {'ear_threshold': 0.22})
        """
        from src.database.connection import SessionLocal
        from src.models.user_settings_model import UserSettings
        
        db = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            
            if not settings:
                # If settings don't exist, create default
                settings = UserSettings(user_id=user_id)
                db.add(settings)
            
            # Apply updates
            if 'ear_threshold' in updates:
                settings.ear_threshold = float(updates['ear_threshold'])
            if 'mar_threshold' in updates:
                settings.mar_threshold = float(updates['mar_threshold'])
            if 'head_threshold' in updates:
                settings.head_threshold = float(updates['head_threshold'])
            if 'alert_volume' in updates:
                settings.alert_volume = float(updates['alert_volume'])
            if 'enable_sound' in updates:
                settings.enable_sound = bool(updates['enable_sound'])
            if 'sunglasses_mode' in updates:
                settings.sunglasses_mode = bool(updates['sunglasses_mode'])
                
            db.commit()
            print(f"✅ Updated settings for User {user_id}: {updates}")
            return True
        except Exception as e:
            print(f"❌ Error updating settings: {e}")
            db.rollback()
            return False
        finally:
            db.close()

# Singleton instance to mimic the old import 'user_model.user_model'
user_model = UserRepository()
