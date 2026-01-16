"""
============================================
⚙️ CONFIGURATION FILE
Driver Drowsiness Detection System
============================================
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if exists)
load_dotenv()

class Config:
    # ----------------------------------
    # 1. APPLICATION SETTINGS
    # ----------------------------------
    APP_NAME = "Driver Drowsiness Detection"
    APP_VERSION = "1.0.0"
    DEBUG = True
    
    # Window Settings
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    
    # ----------------------------------
    # 2. PATHS & DIRECTORIES
    # ----------------------------------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
    
    # Tạo thư mục nếu chưa có
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    # ----------------------------------
    # 3. DATABASE CONFIGURATION
    # ----------------------------------
    # Mặc định XAMPP: User='root', Pass='' (Rỗng)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "drowsiness_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "12345") 

    # ----------------------------------
    # 4. AUDIO & ALERTS (Phần bạn đang thiếu)
    # ----------------------------------
    ALERT_VOLUME = 1.0  # Giá trị từ 0.0 đến 1.0
    
    # Đường dẫn file âm thanh
    SOUND_LEVEL_1 = os.path.join(SOUNDS_DIR, "level1_warning.wav") # Cảnh báo nhẹ
    SOUND_LEVEL_2 = os.path.join(SOUNDS_DIR, "level2_alarm.wav")   # Báo động
    SOUND_LEVEL_3 = os.path.join(SOUNDS_DIR, "level3_siren.wav")   # Khẩn cấp

    # ----------------------------------
    # 5. DETECTION THRESHOLDS (Mặc định)
    # ----------------------------------
    # Ngưỡng mắt (EAR): Càng nhỏ càng dễ báo nhắm mắt
    EAR_THRESHOLD = 0.25
    # Số frame liên tiếp mắt nhắm để báo động
    EAR_CONSEC_FRAMES = 20 
    
    # Ngưỡng miệng (MAR): Càng lớn càng dễ báo ngáp
    MAR_THRESHOLD = 0.70
    
    # Góc đầu (Độ) - Tăng ngưỡng để giảm false positive
    HEAD_PITCH_THRESHOLD = 35.0 # Cúi đầu/Ngửa đầu (góc dương = cúi đầu)
    HEAD_YAW_THRESHOLD = 40.0   # Quay trái/phải

# Global Config Instance
config = Config()

# Mediapipe Configuration (Không thay đổi)
class MediaPipeConfig:
    MAX_NUM_FACES = 1
    REFINE_LANDMARKS = True
    MIN_DETECTION_CONFIDENCE = 0.5
    MIN_TRACKING_CONFIDENCE = 0.5
    
    # Landmark indices (MediaPipe 468 points)
    LEFT_EYE = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]
    
    MOUTH_OUTER = [61, 291, 39, 181, 0, 17, 269, 405]
    MOUTH_INNER = [78, 308, 191, 80, 81, 82, 13, 312, 311, 310, 415, 324]
    
    # Key points for drawing
    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 61
    MOUTH_RIGHT = 291
    NOSE_TIP = 1
    
    # Head pose estimation landmarks
    CHIN = 152
    LEFT_EYE_OUTER = 263
    RIGHT_EYE_OUTER = 33
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291
    
    # Mouth vertical point pairs for MAR calculation (top, bottom)
    # Using inner lip landmarks for more accurate yawn detection
    MOUTH_VERTICAL_POINTS = [
        (81, 178),   # Left vertical
        (13, 14),    # Center vertical (top lip to bottom lip)
        (311, 402),  # Right vertical
    ]

mp_config = MediaPipeConfig()