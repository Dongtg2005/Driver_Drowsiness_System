"""
Utils package initialization
"""

from .math_helpers import (
    euclidean_distance,
    calculate_ear,
    calculate_mar,
    rotation_matrix_to_euler_angles
)

from .constants import (
    AlertType,
    AlertLevel,
    DetectionState,
    Colors,
    Thresholds
)

from .logger import logger as app_logger
from .audio_manager import audio_manager

__all__ = [
    'euclidean_distance',
    'calculate_ear',
    'calculate_mar',
    'rotation_matrix_to_euler_angles',
    'AlertType',
    'AlertLevel',
    'DetectionState',
    'Colors',
    'Thresholds',
    'app_logger',
    'audio_manager'
]
