from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.connection import Base
from src.database.db_connection import get_db, execute_query
from src.utils.logger import logger

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
    Helper class to bridge the gap between UI and Database (Safe Access).
    """
    @staticmethod
    def get_user_settings(user_id: int) -> dict:
        """
        Get user settings as a dictionary.
        Returns None if user or settings not found.
        Offline Safe.
        """
        # [OFFLINE-FIRST] Proactive Check
        if user_id < 0 or get_db().is_offline:
            # Return default/cached settings for Guest/Offline
            # logger.info(f"[OFFLINE][SETTINGS] Returning default settings for user {user_id}")
            from config import config
            return {
                'ear_threshold': config.EAR_THRESHOLD,
                'mar_threshold': config.MAR_THRESHOLD,
                'head_threshold': config.HEAD_PITCH_THRESHOLD,
                'alert_volume': config.ALERT_VOLUME,
                'sensitivity': "MEDIUM", # Default
                'enable_sound': True,
                'sunglasses_mode': False
            }

        try:
            query = "SELECT * FROM user_settings WHERE user_id = %s"
            rows = execute_query(query, (user_id,), fetch=True)
            
            if rows and len(rows) > 0:
                settings = rows[0]
                return {
                    'ear_threshold': float(settings.get('ear_threshold', 0.25)),
                    'mar_threshold': float(settings.get('mar_threshold', 0.5)),
                    'head_threshold': float(settings.get('head_threshold', -20.0)),
                    'alert_volume': float(settings.get('alert_volume', 1.0)),
                    'sensitivity': settings.get('sensitivity_level', 'MEDIUM'),
                    'enable_sound': bool(settings.get('enable_sound', True)),
                    'sunglasses_mode': bool(settings.get('sunglasses_mode', False))
                }
            return None
        except Exception as e:
            logger.error(f"❌ Error getting settings for user {user_id}: {e}")
            return None

    @staticmethod
    def update_settings(user_id: int, updates: dict) -> bool:
        """
        Update specific settings for a user using UPSERT (INSERT ON DUPLICATE KEY UPDATE).
        Ensures data is always written to Cloud.
        Safe for Offline/Guest.
        """
        # [OFFLINE GUARD]
        if user_id < 0 or get_db().is_offline:
            logger.info(f"⚠️ [OFFLINE][SETTINGS] Skip cloud update for user {user_id}. Using local config.")
            return True

        try:
            from config import config
            from datetime import datetime
            
            # 1. Prepare Values
            ear_val = float(updates.get('ear_threshold', config.EAR_THRESHOLD))
            mar_val = float(updates.get('mar_threshold', config.MAR_THRESHOLD))
            head_val = float(updates.get('head_threshold', config.HEAD_PITCH_THRESHOLD))
            vol_val = float(updates.get('alert_volume', config.ALERT_VOLUME))
            sens_val = updates.get('sensitivity', "MEDIUM") 
            
            sound_val = 1 if updates.get('enable_sound', True) else 0
            vib_val = 1 if updates.get('enable_vibration', True) else 0 
            sun_val = 1 if updates.get('sunglasses_mode', False) else 0
            
            # [TIMEZONE FIX] Use Local Time from Python instead of Server UTC
            now_local = datetime.now()
            
            # 2. Execute UPSERT
            # Replace NOW() with %s to use local time
            query = """
                INSERT INTO user_settings 
                (user_id, ear_threshold, mar_threshold, head_threshold, 
                 alert_volume, sensitivity_level, enable_sound, enable_vibration, sunglasses_mode, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    ear_threshold = VALUES(ear_threshold),
                    mar_threshold = VALUES(mar_threshold),
                    head_threshold = VALUES(head_threshold),
                    alert_volume = VALUES(alert_volume),
                    sensitivity_level = VALUES(sensitivity_level),
                    enable_sound = VALUES(enable_sound),
                    enable_vibration = VALUES(enable_vibration),
                    sunglasses_mode = VALUES(sunglasses_mode),
                    updated_at = %s
            """
            
            params = (user_id, ear_val, mar_val, head_val, vol_val, sens_val, sound_val, vib_val, sun_val, now_local, now_local)
            
            get_db().execute_query(query, params)
            logger.info(f"✅ Updated settings for User {user_id} (UPSERT)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating settings: {e}")
            return False

# Singleton instance to mimic the old import 'user_model.user_model'
user_model = UserRepository()
