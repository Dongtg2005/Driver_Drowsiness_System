"""
============================================
🕶️ Sunglasses Detector Module
Driver Drowsiness Detection System
============================================
Phát hiện kính râm dựa trên phân tích độ tương phản vùng mắt
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from collections import deque


class SunglassesDetector:
    """
    Phát hiện kính râm bằng cách phân tích độ tương phản (variance) của vùng mắt.
    
    Logic:
    - Kính râm làm giảm độ tương phản trong vùng mắt
    - Variance thấp = ít chi tiết = có thể đeo kính râm
    - Sử dụng smoothing để tránh false positives
    """
    
    def __init__(self,
                 variance_threshold: float = 15.0,  # [TUNED] Giảm từ 50 xuống 15 để tránh false positive trong phòng tối
                 history_size: int = 30,
                 confidence_threshold: float = 0.80): # [TUNED] Tăng độ tin cậy lên 80%
        """
        Args:
            variance_threshold: Ngưỡng variance - variance thấp hơn = có kính râm
            history_size: Số frames lưu trữ để smoothing
            confidence_threshold: Tỷ lệ frames cần detect để xác nhận kính râm
        """
        self.variance_threshold = variance_threshold
        self.history_size = history_size
        self.confidence_threshold = confidence_threshold
        
        # History của detection results (True/False)
        self.detection_history = deque(maxlen=history_size)
        self.variance_history = deque(maxlen=history_size)
        
    def _calculate_eye_variance(self, 
                                frame: np.ndarray, 
                                eye_landmarks: list) -> Optional[float]:
        """
        Tính variance (độ phân tán) của pixel values trong vùng mắt.
        
        Args:
            frame: Frame ảnh (BGR)
            eye_landmarks: List of (x, y) tuples - landmarks của mắt
            
        Returns:
            Variance value hoặc None nếu không tính được
        """
        if not eye_landmarks or len(eye_landmarks) < 4:
            return None
        
        try:
            # Lấy bounding box của vùng mắt với padding
            points = np.array(eye_landmarks, dtype=np.int32)
            x_min, y_min = np.min(points, axis=0)
            x_max, y_max = np.max(points, axis=0)
            
            # Add padding (20%)
            h, w = frame.shape[:2]
            padding_x = int((x_max - x_min) * 0.2)
            padding_y = int((y_max - y_min) * 0.2)
            
            x_min = max(0, x_min - padding_x)
            y_min = max(0, y_min - padding_y)
            x_max = min(w, x_max + padding_x)
            y_max = min(h, y_max + padding_y)
            
            # Crop vùng mắt
            eye_roi = frame[y_min:y_max, x_min:x_max]
            
            if eye_roi.size == 0:
                return None
            
            # Convert sang grayscale
            gray_roi = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2GRAY)
            
            # Tính variance (np.var)
            # Variance cao = nhiều chi tiết (mắt bình thường)
            # Variance thấp = ít chi tiết (kính râm che)
            variance = float(np.var(gray_roi))
            
            return variance
            
        except Exception as e:
            print(f"[Sunglasses] Error calculating variance: {e}")
            return None
    
    def detect(self, 
               frame: np.ndarray,
               left_eye_landmarks: list,
               right_eye_landmarks: list) -> Tuple[bool, dict]:
        """
        Phát hiện kính râm dựa trên variance của cả 2 mắt.
        
        Args:
            frame: Frame ảnh (BGR)
            left_eye_landmarks: Landmarks của mắt trái
            right_eye_landmarks: Landmarks của mắt phải
            
        Returns:
            (is_wearing_sunglasses, debug_info)
        """
        # Tính variance cho cả 2 mắt
        left_variance = self._calculate_eye_variance(frame, left_eye_landmarks)
        right_variance = self._calculate_eye_variance(frame, right_eye_landmarks)
        
        debug_info = {
            'left_variance': left_variance,
            'right_variance': right_variance,
            'threshold': self.variance_threshold,
            'confidence': 0.0
        }
        
        # Nếu không tính được variance
        if left_variance is None or right_variance is None:
            return False, debug_info
        
        # Lấy variance trung bình của 2 mắt
        avg_variance = (left_variance + right_variance) / 2.0
        self.variance_history.append(avg_variance)
        
        # Detect: variance thấp = có kính râm
        is_low_variance = avg_variance < self.variance_threshold
        self.detection_history.append(is_low_variance)
        
        # Hysteresis Logic
        # Bật cần ngưỡng cao (0.8), Tắt cần ngưỡng thấp (< 0.6) để tránh flicker
        if len(self.detection_history) >= 15:
            detection_ratio = sum(self.detection_history) / len(self.detection_history)
            
            # Logic Hysteresis
            if not getattr(self, 'current_state', False):
                # Đang TẮT -> Muốn BẬT phải >= 0.8
                if detection_ratio >= 0.80:
                    self.current_state = True
            else:
                # Đang BẬT -> Muốn TẮT phải < 0.6
                if detection_ratio < 0.60:
                    self.current_state = False
            
            debug_info['confidence'] = detection_ratio
            debug_info['avg_variance'] = avg_variance
            debug_info['is_wearing'] = self.current_state
            
            return self.current_state, debug_info
        
        # Chưa đủ frames -> Giữ nguyên trạng thái cũ (mặc định False)
        return getattr(self, 'current_state', False), debug_info
    
    def reset(self):
        """Reset detector state"""
        self.detection_history.clear()
        self.variance_history.clear()
    
    def get_stats(self) -> dict:
        """Lấy thống kê cho debugging"""
        if not self.variance_history:
            return {}
        
        return {
            'avg_variance': np.mean(self.variance_history),
            'min_variance': np.min(self.variance_history),
            'max_variance': np.max(self.variance_history),
            'detection_rate': sum(self.detection_history) / len(self.detection_history) if self.detection_history else 0
        }
