"""
============================================
⚙️ Settings Controller
Driver Drowsiness Detection System
Handle user settings and configuration
============================================
"""

from typing import Optional, Dict, Tuple
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from src.models.user_model import user_model
from src.utils.logger import logger
from src.utils.constants import SensitivityLevel


class SettingsController:
    """
    Controller for managing user settings.
    Handles threshold adjustments, audio settings, and preferences.
    """
    
    def __init__(self):
        """Initialize settings controller"""
        self._user_id: Optional[int] = None
        self._settings: Dict = {}
        
        # Default settings
        self._defaults = {
            'ear_threshold': config.EAR_THRESHOLD,
            'mar_threshold': config.MAR_THRESHOLD,
            'head_threshold': config.HEAD_PITCH_THRESHOLD,
            'alert_volume': config.ALERT_VOLUME,
            'sensitivity_level': SensitivityLevel.MEDIUM.value,
            'enable_sound': True,
            'enable_vibration': True
        }
    
    def set_user(self, user_id: int) -> None:
        """
        Set current user and load their settings.
        
        Args:
            user_id: User ID
        """
        self._user_id = user_id
        self.load_settings()
    
    def load_settings(self) -> Dict:
        """
        Load settings from database.
        
        Returns:
            Settings dictionary
        """
        if not self._user_id:
            self._settings = self._defaults.copy()
            return self._settings
        
        db_settings = user_model.get_user_settings(self._user_id)
        
        if db_settings:
            self._settings = db_settings
        else:
            self._settings = self._defaults.copy()
        
        return self._settings
    
    def get_settings(self) -> Dict:
        """
        Get current settings.
        
        Returns:
            Settings dictionary
        """
        if not self._settings:
            self.load_settings()
        return self._settings
    
    def get_setting(self, key: str, default=None):
        """
        Get a specific setting value.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value
        """
        return self._settings.get(key, default or self._defaults.get(key))
    
    def update_settings(self, **kwargs) -> Tuple[bool, str]:
        """
        Update multiple settings.
        
        Args:
            **kwargs: Settings to update
            
        Returns:
            Tuple of (success, message)
        """
        if not self._user_id:
            return False, "Chưa đăng nhập!"
        
        # Validate settings
        validation_result = self._validate_settings(kwargs)
        if not validation_result[0]:
            return validation_result
        
        # Update in database
        success = user_model.update_user_settings(self._user_id, **kwargs)
        
        if success:
            # Update local cache
            self._settings.update(kwargs)
            logger.info(f"Settings updated for user {self._user_id}: {kwargs}")
            return True, "Cập nhật cài đặt thành công!"
        
        return False, "Cập nhật thất bại!"
    
    def _validate_settings(self, settings: Dict) -> Tuple[bool, str]:
        """
        Validate settings values.
        
        Args:
            settings: Settings to validate
            
        Returns:
            Tuple of (valid, message)
        """
        # Validate EAR threshold
        if 'ear_threshold' in settings:
            ear = settings['ear_threshold']
            if not (0.15 <= ear <= 0.40):
                return False, "Ngưỡng EAR phải trong khoảng 0.15 - 0.40!"
        
        # Validate MAR threshold
        if 'mar_threshold' in settings:
            mar = settings['mar_threshold']
            if not (0.50 <= mar <= 1.00):
                return False, "Ngưỡng MAR phải trong khoảng 0.50 - 1.00!"
        
        # Validate head threshold
        if 'head_threshold' in settings:
            head = settings['head_threshold']
            if not (15.0 <= head <= 60.0):
                return False, "Ngưỡng góc đầu phải trong khoảng 15 - 60 độ!"
        
        # Validate volume
        if 'alert_volume' in settings:
            volume = settings['alert_volume']
            if not (0.0 <= volume <= 1.0):
                return False, "Âm lượng phải trong khoảng 0.0 - 1.0!"
        
        # Validate sensitivity level
        if 'sensitivity_level' in settings:
            level = settings['sensitivity_level']
            valid_levels = [s.value for s in SensitivityLevel]
            if level not in valid_levels:
                return False, f"Mức độ nhạy không hợp lệ! Phải là: {valid_levels}"
        
        return True, ""
    
    def set_ear_threshold(self, value: float) -> Tuple[bool, str]:
        """
        Set EAR threshold.
        
        Args:
            value: New threshold value
            
        Returns:
            Tuple of (success, message)
        """
        return self.update_settings(ear_threshold=value)
    
    def set_mar_threshold(self, value: float) -> Tuple[bool, str]:
        """
        Set MAR threshold.
        
        Args:
            value: New threshold value
            
        Returns:
            Tuple of (success, message)
        """
        return self.update_settings(mar_threshold=value)
    
    def set_head_threshold(self, value: float) -> Tuple[bool, str]:
        """
        Set head pose threshold.
        
        Args:
            value: New threshold value
            
        Returns:
            Tuple of (success, message)
        """
        return self.update_settings(head_threshold=value)
    
    def set_alert_volume(self, value: float) -> Tuple[bool, str]:
        """
        Set alert volume.
        
        Args:
            value: Volume level (0.0 - 1.0)
            
        Returns:
            Tuple of (success, message)
        """
        from src.utils.audio_manager import audio_manager
        
        result = self.update_settings(alert_volume=value)
        if result[0]:
            audio_manager.set_volume(value)
        
        return result
    
    def set_sensitivity_level(self, level: str) -> Tuple[bool, str]:
        """
        Set sensitivity level (preset thresholds).
        
        Args:
            level: 'LOW', 'MEDIUM', or 'HIGH'
            
        Returns:
            Tuple of (success, message)
        """
        # Define presets
        presets = {
            'LOW': {
                'ear_threshold': 0.22,
                'mar_threshold': 0.80,
                'head_threshold': 35.0
            },
            'MEDIUM': {
                'ear_threshold': 0.25,
                'mar_threshold': 0.70,
                'head_threshold': 30.0
            },
            'HIGH': {
                'ear_threshold': 0.28,
                'mar_threshold': 0.60,
                'head_threshold': 25.0
            }
        }
        
        if level not in presets:
            return False, f"Mức độ nhạy không hợp lệ! Phải là: {list(presets.keys())}"
        
        preset = presets[level]
        preset['sensitivity_level'] = level
        
        return self.update_settings(**preset)
    
    def toggle_sound(self, enabled: bool) -> Tuple[bool, str]:
        """
        Enable/disable sound alerts.
        
        Args:
            enabled: Whether sound is enabled
            
        Returns:
            Tuple of (success, message)
        """
        from src.utils.audio_manager import audio_manager
        
        result = self.update_settings(enable_sound=enabled)
        if result[0]:
            if enabled:
                audio_manager.enable()
            else:
                audio_manager.disable()
        
        return result
    
    def reset_to_defaults(self) -> Tuple[bool, str]:
        """
        Reset all settings to defaults.
        
        Returns:
            Tuple of (success, message)
        """
        return self.update_settings(**self._defaults)
    
    def get_threshold_ranges(self) -> Dict:
        """
        Get valid ranges for all thresholds.
        
        Returns:
            Dictionary with min/max values for each threshold
        """
        return {
            'ear_threshold': {'min': 0.15, 'max': 0.40, 'step': 0.01, 'default': 0.25},
            'mar_threshold': {'min': 0.50, 'max': 1.00, 'step': 0.05, 'default': 0.70},
            'head_threshold': {'min': 15.0, 'max': 60.0, 'step': 5.0, 'default': 30.0},
            'alert_volume': {'min': 0.0, 'max': 1.0, 'step': 0.1, 'default': 0.8}
        }
    
    def export_settings(self) -> Dict:
        """
        Export current settings.
        
        Returns:
            Settings dictionary
        """
        return self._settings.copy()
    
    def import_settings(self, settings: Dict) -> Tuple[bool, str]:
        """
        Import settings.
        
        Args:
            settings: Settings to import
            
        Returns:
            Tuple of (success, message)
        """
        # Validate all settings
        validation = self._validate_settings(settings)
        if not validation[0]:
            return validation
        
        return self.update_settings(**settings)


# Create singleton instance
settings_controller = SettingsController()


def get_settings_controller() -> SettingsController:
    """Get settings controller instance"""
    return settings_controller


if __name__ == "__main__":
    print("Settings Controller Test")
    
    controller = SettingsController()
    
    # Test threshold ranges
    ranges = controller.get_threshold_ranges()
    print(f"Threshold ranges: {ranges}")
    
    # Test default settings
    defaults = controller.get_settings()
    print(f"Default settings: {defaults}")
