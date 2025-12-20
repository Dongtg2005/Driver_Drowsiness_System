"""
============================================
📋 Constants & Enums (Final Synced)
Driver Drowsiness Detection System
============================================
"""

from enum import Enum, IntEnum
from typing import Dict, Tuple


class AlertType(Enum):
    """Types of drowsiness alerts"""
    NONE = "NONE"
    DROWSY = "DROWSY"           # Nhắm mắt
    YAWN = "YAWN"               # Ngáp
    HEAD_DOWN = "HEAD_DOWN"     # Cúi đầu
    DISTRACTED = "DISTRACTED"   # Mất tập trung


class AlertLevel(IntEnum):
    """Alert severity levels"""
    NONE = 0
    WARNING = 1      # Cảnh báo nhẹ (Beep)
    ALARM = 2       # Nguy hiểm (Alarm)
    CRITICAL = 3     # Khẩn cấp (Siren)


class DetectionState(Enum):
    """Current detection state"""
    NORMAL = "NORMAL"
    EYES_CLOSED = "EYES_CLOSED"
    YAWNING = "YAWNING"
    HEAD_DOWN = "HEAD_DOWN"
    NO_FACE = "NO_FACE"
    WAITING = "WAITING"   # Thêm trạng thái chờ


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ONLINE = 1           # Thêm cho tương thích logic cũ
    OFFLINE = 0
    DRIVING = 2


class SessionStatus(Enum):
    """Driving session status"""
    STARTED = "STARTED"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"


class SensitivityLevel(Enum):
    """Detection sensitivity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ============================================
# 🎨 COLOR CONSTANTS (BGR for OpenCV)
# ============================================
class Colors:
    """Color constants in BGR format for OpenCV"""
    
    # Status colors
    GREEN = (0, 255, 0)         # Bình thường
    YELLOW = (0, 255, 255)      # Cảnh báo
    ORANGE = (0, 165, 255)      # Nguy hiểm
    RED = (0, 0, 255)           # Khẩn cấp
    BLUE = (255, 0, 0)          # Thêm màu xanh dương
    
    # UI colors (Hex for CustomTkinter)
    BG_DARK = "#1a1a1a"
    BG_CARD = "#2b2b2b"
    BG_INPUT = "#333333"
    PRIMARY = "#3B8ED0"
    SUCCESS = "#2CC985"
    DANGER = "#E53935"
    WARNING = "#E9B604"
    WARNING_HEX = "#E9B604"
    INFO = "#0DCAF0"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_MUTED = "#666666"
    
    # OpenCV Colors (Tuple)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (128, 128, 128)
    
    @staticmethod
    def get_status_color(level: AlertLevel) -> Tuple[int, int, int]:
        """Get color based on alert level"""
        color_map = {
            AlertLevel.NONE: Colors.GREEN,
            AlertLevel.WARNING: Colors.YELLOW,
            AlertLevel.ALARM: Colors.ORANGE, # Sửa DANGER thành ALARM cho khớp Enum
            AlertLevel.CRITICAL: Colors.RED
        }
        return color_map.get(level, Colors.GREEN)


# ============================================
# 📐 THRESHOLD CONSTANTS
# ============================================


class Thresholds:
    """Detection threshold constants"""
    
    # EAR (Eye Aspect Ratio)
    EAR_OPEN = 0.30              # Mắt mở bình thường
    EAR_DROWSY = 0.25           # Ngưỡng nhắm mắt (Default)
    EAR_CONSEC_FRAMES = 20      # Số frame liên tiếp
    
    # MAR (Mouth Aspect Ratio)
    MAR_YAWN = 0.70             # Ngưỡng ngáp
    MAR_NORMAL = 0.50
    
    # Head Pose
    HEAD_PITCH = 20.0           # Góc cúi đầu (Default)
    HEAD_YAW = 30.0             # Góc quay đầu (Default)


# ============================================
# 📝 MESSAGE CONSTANTS
# ============================================
class Messages:
    """UI message constants"""
    
    # Status messages
    STATUS_NORMAL = "Trạng thái: Bình thường ✓"
    STATUS_WARNING = "⚠️ CẢNH BÁO: Có dấu hiệu buồn ngủ!"
    STATUS_DANGER = "🚨 NGUY HIỂM: Đang ngủ gật!"
    STATUS_CRITICAL = "🔴 KHẨN CẤP: Dừng xe ngay!"
    
    # Alert messages
    ALERT_EYES_CLOSED = "Mắt nhắm quá lâu!"
    ALERT_YAWNING = "Bạn đang ngáp - Nghỉ ngơi nếu mệt!"
    ALERT_HEAD_DOWN = "Đầu cúi xuống - Tập trung lái xe!"
    
    # Login/Register
    LOGIN_SUCCESS = "Đăng nhập thành công!"
    LOGIN_FAILED = "Sai tên đăng nhập hoặc mật khẩu!"
    REGISTER_SUCCESS = "Đăng ký thành công! Vui lòng đăng nhập."
    REGISTER_FAILED = "Đăng ký thất bại."
    
    # Errors
    DB_CONNECTION_ERROR = "Lỗi kết nối cơ sở dữ liệu!"
    CAMERA_NOT_FOUND = "Không tìm thấy Camera!"


# ============================================
# 🔧 UI CONSTANTS
# ============================================
class UIConstants:
    """UI dimension and styling constants"""
    WINDOW_TITLE = "Driver Drowsiness Detection System"
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    SIDEBAR_WIDTH = 250
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480


# ============================================
# 🎵 SOUND CONSTANTS
# ============================================
class SoundFiles:
    """Sound file names mapping"""
    LEVEL_1 = "level1_warning.wav"
    LEVEL_2 = "level2_alarm.wav"
    LEVEL_3 = "level3_siren.wav"