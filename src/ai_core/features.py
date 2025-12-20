"""
============================================
📐 Feature Extraction Module (Advanced)
Driver Drowsiness Detection System
EAR, MAR (Multi-point) calculations
============================================
"""

import numpy as np
from typing import Tuple, List, Optional, Dict
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config, mp_config
from src.utils.math_helpers import euclidean_distance, moving_average
from src.ai_core.face_mesh import FaceLandmarks


class FeatureExtractor:
    """
    Trích xuất đặc trưng khuôn mặt (EAR, MAR).
    Phiên bản nâng cao: MAR dùng 3 đường dọc.
    """
    
    def __init__(self, smoothing_window: int = 5):
        """
        Khởi tạo bộ trích xuất.
        :param smoothing_window: Kích thước cửa sổ làm mượt dữ liệu (Moving Average)
        """
        self.smoothing_window = smoothing_window
        
        # Lịch sử dữ liệu (Dùng cho smoothing)
        self._ear_history: List[float] = []
        self._mar_history: List[float] = []
        
        # Giá trị hiện tại (Smoothed)
        self._current_ear: float = 0.0
        self._current_mar: float = 0.0
        self._left_ear: float = 0.0
        self._right_ear: float = 0.0
    
    def calculate_ear(self, eye_points: List[Tuple[int, int]]) -> float:
        """
        Tính tỷ lệ mắt (EAR).
        Công thức: EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        if len(eye_points) != 6:
            return 0.0
        
        p1, p2, p3, p4, p5, p6 = eye_points
        
        # Khoảng cách dọc
        vertical_1 = euclidean_distance(p2, p6)
        vertical_2 = euclidean_distance(p3, p5)
        
        # Khoảng cách ngang
        horizontal = euclidean_distance(p1, p4)
        
        if horizontal == 0:
            return 0.0
        
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear
    
    def calculate_both_ears(self, face: FaceLandmarks) -> Tuple[float, float, float]:
        """Tính EAR cho cả 2 mắt và lấy trung bình"""
        # Lấy tọa độ
        left_points = [face.pixel_landmarks[i] for i in mp_config.LEFT_EYE]
        right_points = [face.pixel_landmarks[i] for i in mp_config.RIGHT_EYE]
        
        # Tính toán
        self._left_ear = self.calculate_ear(left_points)
        self._right_ear = self.calculate_ear(right_points)
        
        # Trung bình
        avg_ear = (self._left_ear + self._right_ear) / 2.0
        
        # Thêm vào lịch sử để làm mượt
        self._ear_history.append(avg_ear)
        if len(self._ear_history) > self.smoothing_window:
            self._ear_history.pop(0)
        
        # Tính giá trị mượt (Simple Average of history)
        self._current_ear = sum(self._ear_history) / len(self._ear_history) if self._ear_history else avg_ear
        
        return self._left_ear, self._right_ear, self._current_ear
    
    def calculate_mar(self, face: FaceLandmarks) -> float:
        """
        Tính tỷ lệ miệng (MAR) - Phiên bản Nâng cao (Robust).
        Sử dụng 3 đường dọc và 1 đường ngang để tránh sai sót khi cười/nói.
        
        Công thức cải tiến: 
        MAR = (Vertical_Left + Vertical_Center + Vertical_Right) / (2 * Horizontal)
        """
        # 1. Tính độ rộng miệng (Ngang)
        left_point = face.pixel_landmarks[mp_config.MOUTH_LEFT]
        right_point = face.pixel_landmarks[mp_config.MOUTH_RIGHT]
        horizontal = euclidean_distance(left_point, right_point)
        
        if horizontal == 0:
            return 0.0

        # 2. Tính 3 đường dọc (Verticals)
        vertical_sum = 0.0
        for top_idx, bot_idx in mp_config.MOUTH_VERTICAL_POINTS:
            top_p = face.pixel_landmarks[top_idx]
            bot_p = face.pixel_landmarks[bot_idx]
            vertical_sum += euclidean_distance(top_p, bot_p)
        
        # 3. Tính MAR trung bình
        # Tại sao chia cho (2 * horizontal)? 
        # Để chuẩn hóa giá trị MAR về khoảng tương đương với EAR (dễ so sánh ngưỡng).
        # Nếu dùng 3 đường, ta có thể chia cho 3 để lấy trung bình dọc, sau đó chia cho horizontal.
        # Công thức đề xuất: (Sum_Verticals / 3) / Horizontal * factor
        # Nhưng để khớp với yêu cầu của bạn: (V1 + V2 + V3) / (2 * H)
        mar = vertical_sum / (2.0 * horizontal)
        
        # Thêm vào lịch sử để làm mượt
        self._mar_history.append(mar)
        if len(self._mar_history) > self.smoothing_window:
            self._mar_history.pop(0)
        
        self._current_mar = sum(self._mar_history) / len(self._mar_history) if self._mar_history else mar
        
        return self._current_mar
    
    def extract_all_features(self, face: FaceLandmarks) -> Dict:
        """Trích xuất tất cả đặc trưng cùng lúc"""
        self.calculate_both_ears(face)
        self.calculate_mar(face)
        
        return {
            'ear': self._current_ear,         # Đã làm mượt
            'mar': self._current_mar,         # Đã làm mượt
            'left_ear': self._left_ear,
            'right_ear': self._right_ear,
            'ear_raw': self._ear_history[-1] if self._ear_history else 0, # Giá trị thô
            'mar_raw': self._mar_history[-1] if self._mar_history else 0
        }
    
    def reset(self) -> None:
        """
        QUAN TRỌNG: Xóa sạch trạng thái cũ.
        Hàm này cần được gọi khi mất khuôn mặt (Face Lost).
        """
        self._ear_history.clear()
        self._mar_history.clear()
        
        # Reset về 0 hoặc giá trị an toàn mặc định
        self._current_ear = 0.0
        self._current_mar = 0.0
        self._left_ear = 0.0
        self._right_ear = 0.0


# Singleton instance
feature_extractor = FeatureExtractor()