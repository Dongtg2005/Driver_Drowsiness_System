"""
Views package initialization
"""

from .components import (
    Colors,
    StyledButton,
    StyledEntry,
    StyledLabel,
    StyledFrame,
    StyledSlider,
    StyledSwitch,
    StyledOptionMenu,
    MessageBox,
    LoadingSpinner,
    StatusBar
)

from .login_view import LoginView
from .register_view import RegisterView
from .camera_view import CameraView
from .dashboard_view import DashboardView
from .settings_view import SettingsView

__all__ = [
    # Components
    'Colors',
    'StyledButton',
    'StyledEntry',
    'StyledLabel',
    'StyledFrame',
    'StyledSlider',
    'StyledSwitch',
    'StyledOptionMenu',
    'MessageBox',
    'LoadingSpinner',
    'StatusBar',
    
    # Views
    'LoginView',
    'RegisterView',
    'CameraView',
    'DashboardView',
    'SettingsView'
]
