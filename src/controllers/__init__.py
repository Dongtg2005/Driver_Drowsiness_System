"""
Controllers package initialization
"""

from .auth_controller import auth_controller
from .monitor_controller import MonitorController
from .settings_controller import settings_controller

__all__ = [
    'auth_controller',
    'MonitorController',
    'settings_controller'
]

def __init__(self, user_id: int = None):
        # ... (các biến cũ giữ nguyên)
        self._drowsy_frames = 0
        
        # [MỚI] Thêm biến này để đếm thời gian tỉnh táo
        self._eyes_open_frames = 0