"""
======================================================
⚙️ Settings Controller (Refactored with SQLAlchemy)
Driver Drowsiness Detection System
Handles user settings and configuration using SQLAlchemy ORM.
======================================================
"""

from typing import Optional, Dict, Tuple
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.database.connection import SessionLocal
from src.models.user_model import User
from src.models.user_settings_model import UserSettings
from src.utils.logger import logger
from src.utils.constants import SensitivityLevel
from src.utils.audio_manager import audio_manager # Import here for direct use

class SettingsController:
    """
    Controller for managing user settings using SQLAlchemy.
    """
    
    def __init__(self):
        """Initialize settings controller"""
        self._user_id: Optional[int] = None
        self._current_settings: Optional[UserSettings] = None
        
        # Default settings (used if no DB entry exists, or for reset)
        # These should ideally match the defaults in UserSettings model
        self._defaults = {
            'ear_threshold': 0.25,
            'mar_threshold': 0.70,
            'head_threshold': 30.0,
            'alert_volume': 0.8,
            'sensitivity_level': SensitivityLevel.MEDIUM.value,
            'enable_sound': True,
            'enable_vibration': True, # Not yet implemented in UI/DB, but kept for consistency
            'sunglasses_mode': False  # [NEW] Chế độ kính râm thủ công
        }
    
    def set_user(self, user_id: int) -> None:
        """
        Set current user and load/create their settings.
        
        Args:
            user_id: User ID
        """
        self._user_id = user_id
        self._load_or_create_settings()
    
    def _load_or_create_settings(self) -> None:
        """
        Loads user settings from DB, or creates default settings if none exist.
        """
        if not self._user_id:
            self._current_settings = None
            return

        db: Session = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == self._user_id).first()
            if not settings:
                # Create default settings for the user if they don't exist
                settings = UserSettings(user_id=self._user_id, **self._defaults)
                db.add(settings)
                db.commit()
                db.refresh(settings)
                logger.info(f"Created default settings for user ID: {self._user_id}")
            self._current_settings = settings
        except Exception as e:
            logger.error(f"Error loading/creating settings for user {self._user_id}: {e}")
            db.rollback()
            self._current_settings = None
        finally:
            db.close()
    
    def get_settings(self) -> Dict:
        """
        Get current settings as a dictionary.
        """
        if not self._current_settings:
            self._load_or_create_settings() # Try to load again if not set
            if not self._current_settings:
                return self._defaults.copy() # Fallback to hardcoded defaults

        # Convert UserSettings object to a dictionary
        return {
            'ear_threshold': self._current_settings.ear_threshold,
            'mar_threshold': self._current_settings.mar_threshold,
            'head_threshold': self._current_settings.head_threshold,
            'alert_volume': self._current_settings.alert_volume,
            'sensitivity_level': self._current_settings.sensitivity_level,
            'enable_sound': self._current_settings.enable_sound,
            'enable_vibration': self._current_settings.enable_vibration, # Assuming this exists in DB
            'sunglasses_mode': getattr(self._current_settings, 'sunglasses_mode', False)  # [NEW] Safe get
        }
    
    def get_setting(self, key: str, default=None):
        """
        Get a specific setting value.
        """
        settings_dict = self.get_settings()
        return settings_dict.get(key, default or self._defaults.get(key))
    
    def update_settings(self, **kwargs) -> Tuple[bool, str]:
        """
        Update multiple settings in the database.
        """
        if not self._user_id or not self._current_settings:
            return False, "Chưa đăng nhập hoặc cài đặt chưa được tải!"
        
        validation_result = self._validate_settings(kwargs)
        if not validation_result[0]:
            return validation_result

        db: Session = SessionLocal()
        try:
            # Re-fetch settings within the session to ensure it's attached
            settings_to_update = db.query(UserSettings).filter(UserSettings.user_id == self._user_id).first()
            if not settings_to_update:
                return False, "Không tìm thấy cài đặt người dùng!"

            for key, value in kwargs.items():
                if hasattr(settings_to_update, key):
                    setattr(settings_to_update, key, value)

            db.commit()
            db.refresh(settings_to_update)
            self._current_settings = settings_to_update # Update local cache

            logger.info(f"Settings updated for user {self._user_id}: {kwargs}")

            # Apply audio settings immediately
            if 'alert_volume' in kwargs:
                audio_manager.set_volume(kwargs['alert_volume'])
            if 'enable_sound' in kwargs:
                if kwargs['enable_sound']:
                    audio_manager.enable()
                else:
                    audio_manager.disable()

            return True, "Cập nhật cài đặt thành công!"
        except Exception as e:
            logger.error(f"Error updating settings for user {self._user_id}: {e}")
            db.rollback()
            return False, "Cập nhật thất bại do lỗi hệ thống!"
        finally:
            db.close()
    
    def _validate_settings(self, settings: Dict) -> Tuple[bool, str]:
        """
        Validate settings values.
        """
        if 'ear_threshold' in settings and not (0.15 <= settings['ear_threshold'] <= 0.40):
            return False, "Ngưỡng EAR phải trong khoảng 0.15 - 0.40!"
        if 'mar_threshold' in settings and not (0.50 <= settings['mar_threshold'] <= 1.00):
            return False, "Ngưỡng MAR phải trong khoảng 0.50 - 1.00!"
        if 'head_threshold' in settings and not (15.0 <= settings['head_threshold'] <= 60.0):
            return False, "Ngưỡng góc đầu phải trong khoảng 15 - 60 độ!"
        if 'alert_volume' in settings and not (0.0 <= settings['alert_volume'] <= 1.0):
            return False, "Âm lượng phải trong khoảng 0.0 - 1.0!"
        if 'sensitivity_level' in settings:
            valid_levels = [s.value for s in SensitivityLevel]
            if settings['sensitivity_level'] not in valid_levels:
                return False, f"Mức độ nhạy không hợp lệ! Phải là: {valid_levels}"
        return True, ""

    def set_sensitivity_level(self, level: str) -> Tuple[bool, str]:
        """
        Set sensitivity level (preset thresholds).
        """
        presets = {
            'LOW': {'ear_threshold': 0.22, 'mar_threshold': 0.80, 'head_threshold': 35.0},
            'MEDIUM': {'ear_threshold': 0.25, 'mar_threshold': 0.70, 'head_threshold': 30.0},
            'HIGH': {'ear_threshold': 0.28, 'mar_threshold': 0.60, 'head_threshold': 25.0}
        }
        if level not in presets:
            return False, f"Mức độ nhạy không hợp lệ! Phải là: {list(presets.keys())}"
        
        preset = presets[level]
        preset['sensitivity_level'] = level
        return self.update_settings(**preset)

    def reset_to_defaults(self) -> Tuple[bool, str]:
        """
        Reset all settings to defaults.
        """
        return self.update_settings(**self._defaults)

# Create singleton instance
settings_controller = SettingsController()

def get_settings_controller() -> SettingsController:
    """Get settings controller instance"""
    return settings_controller
