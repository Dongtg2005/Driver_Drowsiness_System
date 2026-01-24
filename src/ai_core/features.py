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
from src.ai_core.perclos_detector import get_perclos_detector
from src.ai_core.smile_detector import get_smile_detector
from src.utils.logger import logger


class FeatureExtractor:
    """
    Trích xuất đặc trưng khuôn mặt (EAR, MAR) cho hệ thống phát hiện buồn ngủ.
    
    Phiên bản nâng cao:
    - MAR sử dụng 3 đường dọc để tăng độ chính xác
    - Hỗ trợ PERCLOS Detection
    - Tích hợp Smile Detection để tránh false positive
    """
    
    def __init__(self, smoothing_window: int = 5):
        """
        Khởi tạo bộ trích xuất đặc trưng.
        
        Args:
            smoothing_window: Kích thước cửa sổ làm mượt dữ liệu (Moving Average).
                            Giá trị lớn hơn = dữ liệu mượt hơn nhưng độ trễ cao hơn.
        
        Raises:
            ValueError: Nếu smoothing_window <= 0
        """
        if smoothing_window <= 0:
            raise ValueError("smoothing_window phải lớn hơn 0")
        
        self.smoothing_window = smoothing_window
        
        # Lịch sử dữ liệu (dùng cho smoothing)
        self._ear_history: List[float] = []
        self._mar_history: List[float] = []
        
        # Giá trị hiện tại (smoothed)
        self._current_ear: float = 0.0
        self._current_mar: float = 0.0
        self._left_ear: float = 0.0
        self._right_ear: float = 0.0
        
        # Detectors
        self.perclos_detector = get_perclos_detector()
        self.smile_detector = get_smile_detector()
    
    def calculate_ear(self, eye_points: List[Tuple[int, int]]) -> float:
        """
        Tính tỷ lệ mắt (Eye Aspect Ratio - EAR).
        
        Công thức: EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Trong đó:
        - p1, p4: các điểm mép mắt trái-phải
        - p2, p6; p3, p5: các điểm mép mắt trên-dưới
        
        Args:
            eye_points: Danh sách 6 điểm của mắt [p1, p2, p3, p4, p5, p6]
        
        Returns:
            EAR value (float). Về 0 khi mắt đóng, ~0.4 khi mắt mở.
            Trả về 0.0 nếu input không hợp lệ.
        
        Raises:
            ValueError: Nếu số điểm không đúng hoặc có NaN
        """
        if len(eye_points) != 6:
            return 0.0
        
        # Kiểm tra điểm hợp lệ
        if any(point is None or len(point) != 2 for point in eye_points):
            return 0.0
        
        p1, p2, p3, p4, p5, p6 = eye_points
        
        # Khoảng cách dọc
        vertical_1 = euclidean_distance(p2, p6)
        vertical_2 = euclidean_distance(p3, p5)
        
        # Khoảng cách ngang
        horizontal = euclidean_distance(p1, p4)
        
        # Tránh chia cho 0
        if horizontal == 0:
            return 0.0
        
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        
        # Kiểm tra giá trị hợp lệ (EAR thường 0.0 - 1.0)
        if np.isnan(ear) or np.isinf(ear):
            return 0.0
        
        return ear
    
    def calculate_both_ears(self, face: FaceLandmarks) -> Tuple[float, float, float]:
        """
        Tính EAR cho cả 2 mắt (trái, phải) và lấy trung bình smoothed.
        
        Args:
            face: Đối tượng FaceLandmarks chứa thông tin khuôn mặt
        
        Returns:
            Tuple[left_ear, right_ear, avg_ear_smoothed]:
            - left_ear: EAR của mắt trái (raw)
            - right_ear: EAR của mắt phải (raw)
            - avg_ear_smoothed: Giá trị trung bình smoothed của 2 mắt
        
        Raises:
            AttributeError: Nếu face không có pixel_landmarks
        """
        try:
            # Lấy tọa độ pixel của mắt
            left_points = [face.pixel_landmarks[i] for i in mp_config.LEFT_EYE]
            right_points = [face.pixel_landmarks[i] for i in mp_config.RIGHT_EYE]
        except (IndexError, KeyError, TypeError) as e:
            # Trả về giá trị mặc định nếu không lấy được landmarks
            return 0.0, 0.0, self._current_ear
        
        # Tính toán EAR
        self._left_ear = self.calculate_ear(left_points)
        self._right_ear = self.calculate_ear(right_points)
        
        # Trung bình của 2 mắt
        avg_ear = (self._left_ear + self._right_ear) / 2.0
        
        # Thêm vào lịch sử để làm mượt
        self._ear_history.append(avg_ear)
        if len(self._ear_history) > self.smoothing_window:
            self._ear_history.pop(0)
        
        # Tính giá trị mượt (Simple Moving Average)
        self._current_ear = (
            sum(self._ear_history) / len(self._ear_history) 
            if self._ear_history else avg_ear
        )
        
        return self._left_ear, self._right_ear, self._current_ear
    
    def calculate_mar(self, face: FaceLandmarks) -> float:
        """
        Tính tỷ lệ miệng (Mouth Aspect Ratio - MAR) - Phiên bản Nâng cao.
        
        Sử dụng 3 đường dọc và 1 đường ngang để tăng độ chính xác,
        tránh sai sót khi người lái cười hoặc nói chuyện.
        
        Công thức: MAR = (V_left + V_center + V_right) / (2 * Horizontal)
        
        Trong đó:
        - V_left, V_center, V_right: 3 đường dọc của miệng
        - Horizontal: độ rộng miệng
        
        Args:
            face: Đối tượng FaceLandmarks chứa thông tin khuôn mặt
        
        Returns:
            MAR value smoothed (float). Giá trị nhỏ khi miệng đóng, lớn khi mở.
            Trả về 0.0 nếu không tính được.
        """
        try:
            # 1. Tính độ rộng miệng (ngang)
            left_point = face.pixel_landmarks[mp_config.MOUTH_LEFT]
            right_point = face.pixel_landmarks[mp_config.MOUTH_RIGHT]
            horizontal = euclidean_distance(left_point, right_point)
        except (IndexError, KeyError, TypeError):
            return self._current_mar
        
        if horizontal == 0:
            return self._current_mar

        # 2. Tính tổng 3 đường dọc (verticals)
        vertical_sum = 0.0
        num_verticals = 0
        
        try:
            for top_idx, bot_idx in mp_config.MOUTH_VERTICAL_POINTS:
                top_p = face.pixel_landmarks[top_idx]
                bot_p = face.pixel_landmarks[bot_idx]
                dist = euclidean_distance(top_p, bot_p)
                
                # Chỉ cộng giá trị hợp lệ
                if not np.isnan(dist) and not np.isinf(dist) and dist >= 0:
                    vertical_sum += dist
                    num_verticals += 1
        except (IndexError, KeyError, TypeError):
            return self._current_mar
        
        if num_verticals == 0:
            return self._current_mar
        
        # 3. Tính MAR
        # Công thức: (V1 + V2 + V3) / (2 * H)
        # Chia cho 2 để chuẩn hóa với EAR (dễ so sánh ngưỡng)
        mar = vertical_sum / (2.0 * horizontal)
        
        # Kiểm tra giá trị hợp lệ
        if np.isnan(mar) or np.isinf(mar):
            return self._current_mar
        
        # 4. Thêm vào lịch sử để làm mượt
        self._mar_history.append(mar)
        if len(self._mar_history) > self.smoothing_window:
            self._mar_history.pop(0)
        
        # Tính giá trị mượt
        self._current_mar = (
            sum(self._mar_history) / len(self._mar_history) 
            if self._mar_history else mar
        )
        
        return self._current_mar
    
    def extract_all_features(self, face: FaceLandmarks) -> Dict:
        """
        Trích xuất tất cả đặc trưng khuôn mặt cho phát hiện buồn ngủ.
        
        Bao gồm:
        - EAR (Eye Aspect Ratio) - thông số chính phát hiện buồn ngủ
        - MAR (Mouth Aspect Ratio) - hỗ trợ giảm false positive
        - PERCLOS - phân biệt chớp mắt vs ngủ gục
        - Smile Detection - tránh nhầm lẫn khi cười
        
        Args:
            face: Đối tượng FaceLandmarks với đầy đủ thông tin khuôn mặt
        
        Returns:
            Dict chứa các thông số:
            - 'ear': EAR smoothed
            - 'mar': MAR smoothed
            - 'left_ear', 'right_ear': EAR từng mắt
            - 'ear_raw', 'mar_raw': Giá trị chưa làm mượt
            - 'eye_state': Trạng thái mắt hiện tại
            - 'perclos': Giá trị PERCLOS (%)
            - 'is_drowsy': True nếu phát hiện buồn ngủ
            - 'is_just_blinking': True nếu đang chớp mắt
            - 'is_smiling': True nếu đang cười
            - 'smile_confidence': Độ tự tin (0.0 - 1.0)
        """
        if not face or not hasattr(face, 'pixel_landmarks'):
            return self._get_default_features()
        
        try:
            # 1. Tính EAR và MAR
            self.calculate_both_ears(face)
            self.calculate_mar(face)
            
            # 2. Lấy eye landmarks cho sunglasses detection
            left_eye_landmarks = [face.pixel_landmarks[i] for i in mp_config.LEFT_EYE]
            right_eye_landmarks = [face.pixel_landmarks[i] for i in mp_config.RIGHT_EYE]
            
            # 3. PERCLOS Detection (phân biệt chớp mắt vs buồn ngủ)
            eye_state, perclos_value = self.perclos_detector.update(self._current_ear)
            
            # 4. Smile Detection (tránh false positive)
            is_smiling, smile_confidence = self.smile_detector.is_smiling(
                face,
                self._left_ear,
                self._right_ear,
                self._current_mar
            )
            
            # 5. Trả về đầy đủ thông tin
            return {
                # Raw values
                'ear': self._current_ear,
                'mar': self._current_mar,
                'left_ear': self._left_ear,
                'right_ear': self._right_ear,
                'ear_raw': self._ear_history[-1] if self._ear_history else 0,
                'mar_raw': self._mar_history[-1] if self._mar_history else 0,
                
                # Eye landmarks for sunglasses detection
                'left_eye_landmarks': left_eye_landmarks,
                'right_eye_landmarks': right_eye_landmarks,
                
                # PERCLOS Analysis
                'eye_state': eye_state,
                'perclos': perclos_value,
                'perclos_stats': self.perclos_detector.get_statistics(),
                'is_drowsy': self.perclos_detector.is_drowsy(),
                'is_just_blinking': self.perclos_detector.is_just_blinking(),
                
                # Smile Detection
                'is_smiling': is_smiling,
                'smile_confidence': smile_confidence
            }
        
        except Exception as e:
            import traceback
            logger.exception("Exception in extract_all_features:\n" + traceback.format_exc())
            return self._get_default_features()
    
    def _get_default_features(self) -> Dict:
        """Trả về Dict đặc trưng với giá trị mặc định (khi lỗi)."""
        return {
            'ear': 0.0,
            'mar': 0.0,
            'left_ear': 0.0,
            'right_ear': 0.0,
            'ear_raw': 0.0,
            'mar_raw': 0.0,
            'eye_state': 'unknown',
            'perclos': 0.0,
            'perclos_stats': {},
            'is_drowsy': False,
            'is_just_blinking': False,
            'is_smiling': False,
            'smile_confidence': 0.0
        }
    
    def reset(self) -> None:
        """
        Xóa sạch trạng thái cũ của feature extractor.
        
        ⚠️ QUAN TRỌNG: Gọi hàm này khi mất khuôn mặt (Face Lost)
        để tránh dữ liệu stale từ người lái trước đó.
        """
        self._ear_history.clear()
        self._mar_history.clear()
        self._current_ear = 0.0
        self._current_mar = 0.0
        self._left_ear = 0.0
        self._right_ear = 0.0
        
        # Reset các detector
        if self.perclos_detector:
            self.perclos_detector.reset()
        if self.smile_detector:
            self.smile_detector.reset()
    
    def get_current_state(self) -> Dict[str, float]:
        """
        Lấy trạng thái hiện tại của detectors (mà không tính toán lại).
        
        Hữu ích để debug hoặc theo dõi.
        
        Returns:
            Dict chứa: ear, mar, left_ear, right_ear
        """
        return {
            'ear': self._current_ear,
            'mar': self._current_mar,
            'left_ear': self._left_ear,
            'right_ear': self._right_ear
        }


# Singleton instance - Sử dụng global instance để tái sử dụng
feature_extractor = FeatureExtractor()