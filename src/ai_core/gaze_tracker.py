"""
============================================
👁️ Gaze Tracking Module
Driver Drowsiness Detection System
Iris Tracking & Gaze Direction Detection using MediaPipe
============================================
"""

import numpy as np
from typing import Tuple, Optional, List, Dict
import time
from collections import deque
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import mp_config
from src.ai_core.face_mesh import FaceLandmarks
from src.utils.math_helpers import euclidean_distance
from src.utils.logger import logger


class GazeDirection:
    """Enum-like class for gaze directions"""
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    OFF_ROAD = "off_road"  # Looking away from road


class GazeTracker:
    """
    Theo dõi hướng nhìn của mắt sử dụng Iris Tracking.
    
    MediaPipe Face Mesh cung cấp 478 landmarks, trong đó:
    - Left Iris: indices 468, 469, 470, 471, 472
    - Right Iris: indices 473, 474, 475, 476, 477
    
    Chúng ta sẽ tính toán vị trí tương đối của iris trong mắt để xác định hướng nhìn.
    """
    
    # MediaPipe Iris Landmarks (added in newer versions)
    LEFT_IRIS = [468, 469, 470, 471, 472]    # Left iris center and boundaries
    RIGHT_IRIS = [473, 474, 475, 476, 477]   # Right iris center and boundaries
    
    # Eye corner landmarks for reference
    LEFT_EYE_INNER = 133
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263
    
    def __init__(self, 
                 distraction_threshold: float = 2.0,
                 gaze_threshold_horizontal: float = 0.25,
                 gaze_threshold_vertical: float = 0.30):
        """
        Khởi tạo Gaze Tracker.
        
        Args:
            distraction_threshold: Thời gian (giây) mắt nhìn xa khỏi đường mới cảnh báo
            gaze_threshold_horizontal: Ngưỡng tỷ lệ ngang (0.25 = 25% độ lệch)
            gaze_threshold_vertical: Ngưỡng tỷ lệ dọc (0.30 = 30% độ lệch)
        """
        self.distraction_threshold = distraction_threshold
        self.gaze_threshold_h = gaze_threshold_horizontal
        self.gaze_threshold_v = gaze_threshold_vertical
        
        # Tracking state
        self._off_road_start_time: Optional[float] = None
        self._is_distracted = False
        self._current_gaze_direction = GazeDirection.CENTER
        
        # History for smoothing
        self._gaze_ratio_history_x: deque = deque(maxlen=5)
        self._gaze_ratio_history_y: deque = deque(maxlen=5)
        
        # Statistics
        self._left_gaze_ratio = (0.0, 0.0)   # (x, y) ratio for left eye
        self._right_gaze_ratio = (0.0, 0.0)  # (x, y) ratio for right eye
        self._avg_gaze_ratio = (0.0, 0.0)    # averaged
        
        logger.info(f"GazeTracker initialized: distraction_threshold={distraction_threshold}s, "
                   f"h_threshold={gaze_threshold_horizontal}, v_threshold={gaze_threshold_vertical}")
    
    def _calculate_iris_position_ratio(self, 
                                       face: FaceLandmarks,
                                       iris_indices: List[int],
                                       eye_inner_idx: int,
                                       eye_outer_idx: int) -> Tuple[float, float]:
        """
        Tính tỷ lệ vị trí iris trong mắt.
        
        Returns:
            (ratio_x, ratio_y):
            - ratio_x: -1.0 (nhìn trái) đến +1.0 (nhìn phải), 0.0 là giữa
            - ratio_y: -1.0 (nhìn trên) đến +1.0 (nhìn dưới), 0.0 là giữa
        """
        try:
            # Lấy tọa độ iris center (index 0 of iris list is center)
            if len(iris_indices) > 0 and iris_indices[0] < len(face.pixel_landmarks):
                iris_center = face.pixel_landmarks[iris_indices[0]]
            else:
                return (0.0, 0.0)
            
            # Lấy góc trong và góc ngoài của mắt
            eye_inner = face.pixel_landmarks[eye_inner_idx]
            eye_outer = face.pixel_landmarks[eye_outer_idx]
            
            # Lấy 6 điểm của mắt để tính bbox
            eye_indices = mp_config.LEFT_EYE if eye_inner_idx == self.LEFT_EYE_INNER else mp_config.RIGHT_EYE
            eye_points = [face.pixel_landmarks[i] for i in eye_indices]
            
            # Tính bounding box của mắt
            xs = [p[0] for p in eye_points]
            ys = [p[1] for p in eye_points]
            eye_left = min(xs)
            eye_right = max(xs)
            eye_top = min(ys)
            eye_bottom = max(ys)
            
            eye_width = eye_right - eye_left
            eye_height = eye_bottom - eye_top
            
            if eye_width == 0 or eye_height == 0:
                return (0.0, 0.0)
            
            # Tính tỷ lệ vị trí của iris
            # X: 0.0 = giữa, -1.0 = trái cực, +1.0 = phải cực
            eye_center_x = (eye_left + eye_right) / 2.0
            iris_offset_x = iris_center[0] - eye_center_x
            ratio_x = (iris_offset_x / (eye_width / 2.0))
            
            # Y: 0.0 = giữa, -1.0 = trên cực, +1.0 = dưới cực
            eye_center_y = (eye_top + eye_bottom) / 2.0
            iris_offset_y = iris_center[1] - eye_center_y
            ratio_y = (iris_offset_y / (eye_height / 2.0))
            
            # Clamp values
            ratio_x = np.clip(ratio_x, -1.0, 1.0)
            ratio_y = np.clip(ratio_y, -1.0, 1.0)
            
            return (ratio_x, ratio_y)
            
        except (IndexError, KeyError, TypeError, ZeroDivisionError) as e:
            logger.debug(f"Error calculating iris ratio: {e}")
            return (0.0, 0.0)
    
    def calculate_gaze_ratios(self, face: FaceLandmarks) -> Tuple[float, float]:
        """
        Tính toán tỷ lệ hướng nhìn từ cả 2 mắt.
        
        Returns:
            (avg_ratio_x, avg_ratio_y): Giá trị trung bình smoothed của 2 mắt
        """
        # Check if we have iris landmarks (468-477)
        if len(face.pixel_landmarks) < 478:
            logger.debug("Iris landmarks not available (need 478 landmarks)")
            return (0.0, 0.0)
        
        # Calculate for both eyes
        self._left_gaze_ratio = self._calculate_iris_position_ratio(
            face, 
            self.LEFT_IRIS,
            self.LEFT_EYE_INNER,
            self.LEFT_EYE_OUTER
        )
        
        self._right_gaze_ratio = self._calculate_iris_position_ratio(
            face,
            self.RIGHT_IRIS,
            self.RIGHT_EYE_INNER,
            self.RIGHT_EYE_OUTER
        )
        
        # Average both eyes
        avg_x = (self._left_gaze_ratio[0] + self._right_gaze_ratio[0]) / 2.0
        avg_y = (self._left_gaze_ratio[1] + self._right_gaze_ratio[1]) / 2.0
        
        # Add to history for smoothing
        self._gaze_ratio_history_x.append(avg_x)
        self._gaze_ratio_history_y.append(avg_y)
        
        # Calculate smoothed average
        smooth_x = sum(self._gaze_ratio_history_x) / len(self._gaze_ratio_history_x)
        smooth_y = sum(self._gaze_ratio_history_y) / len(self._gaze_ratio_history_y)
        
        self._avg_gaze_ratio = (smooth_x, smooth_y)
        
        return self._avg_gaze_ratio
    
    def detect_gaze_direction(self, gaze_ratio: Tuple[float, float]) -> str:
        """
        Xác định hướng nhìn dựa trên gaze ratio.
        
        Args:
            gaze_ratio: (ratio_x, ratio_y) từ calculate_gaze_ratios()
        
        Returns:
            Gaze direction string (center, left, right, up, down, off_road)
        """
        ratio_x, ratio_y = gaze_ratio
        
        # Check vertical first (looking down is critical - phone usage)
        if ratio_y > self.gaze_threshold_v:
            self._current_gaze_direction = GazeDirection.DOWN
            return GazeDirection.DOWN
        elif ratio_y < -self.gaze_threshold_v:
            self._current_gaze_direction = GazeDirection.UP
            return GazeDirection.UP
        
        # Check horizontal
        if ratio_x < -self.gaze_threshold_h:
            self._current_gaze_direction = GazeDirection.LEFT
            return GazeDirection.LEFT
        elif ratio_x > self.gaze_threshold_h:
            self._current_gaze_direction = GazeDirection.RIGHT
            return GazeDirection.RIGHT
        
        # Center (looking at road)
        self._current_gaze_direction = GazeDirection.CENTER
        return GazeDirection.CENTER
    
    def is_looking_at_road(self, gaze_direction: str) -> bool:
        """
        Kiểm tra xem tài xế có đang nhìn đường không.
        
        Vùng an toàn (Road region): CENTER, hoặc LEFT/RIGHT nhẹ (để nhìn gương)
        Vùng nguy hiểm: DOWN (nhìn điện thoại), UP (nhìn trần xe), hoặc quá lệch
        """
        return gaze_direction in [GazeDirection.CENTER]
    
    def update_distraction_state(self, 
                                 gaze_ratio: Tuple[float, float],
                                 timestamp: Optional[float] = None) -> Tuple[bool, float, str]:
        """
        Cập nhật trạng thái mất tập trung dựa trên hướng nhìn.
        
        Args:
            gaze_ratio: (ratio_x, ratio_y) từ calculate_gaze_ratios()
            timestamp: Thời gian hiện tại (giây), mặc định là time.time()
        
        Returns:
            (is_distracted_confirmed, duration, gaze_direction):
            - is_distracted_confirmed: True nếu đã mất tập trung quá lâu
            - duration: Thời gian đã mất tập trung (giây)
            - gaze_direction: Hướng nhìn hiện tại
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Detect current gaze direction
        gaze_direction = self.detect_gaze_direction(gaze_ratio)
        
        # Check if looking at road
        is_looking_road = self.is_looking_at_road(gaze_direction)
        
        if not is_looking_road:
            # Start tracking distraction time
            if self._off_road_start_time is None:
                self._off_road_start_time = timestamp
            
            duration = timestamp - self._off_road_start_time
            
            # Confirm distraction if exceeded threshold
            if duration > self.distraction_threshold:
                self._is_distracted = True
                return True, duration, gaze_direction
            else:
                return False, duration, gaze_direction
        else:
            # Reset distraction tracking
            self._off_road_start_time = None
            self._is_distracted = False
            return False, 0.0, gaze_direction
    
    def get_gaze_info(self) -> Dict:
        """
        Lấy thông tin chi tiết về gaze tracking.
        
        Returns:
            Dict chứa các thông tin về gaze state
        """
        return {
            'left_gaze_ratio': self._left_gaze_ratio,
            'right_gaze_ratio': self._right_gaze_ratio,
            'avg_gaze_ratio': self._avg_gaze_ratio,
            'gaze_direction': self._current_gaze_direction,
            'is_distracted': self._is_distracted,
            'off_road_duration': (
                time.time() - self._off_road_start_time 
                if self._off_road_start_time is not None 
                else 0.0
            )
        }
    
    def reset(self):
        """Reset all tracking state"""
        self._off_road_start_time = None
        self._is_distracted = False
        self._current_gaze_direction = GazeDirection.CENTER
        self._gaze_ratio_history_x.clear()
        self._gaze_ratio_history_y.clear()
        self._left_gaze_ratio = (0.0, 0.0)
        self._right_gaze_ratio = (0.0, 0.0)
        self._avg_gaze_ratio = (0.0, 0.0)


# Singleton instance
_gaze_tracker_instance: Optional[GazeTracker] = None

def get_gaze_tracker() -> GazeTracker:
    """
    Lấy singleton instance của GazeTracker.
    
    Returns:
        GazeTracker instance
    """
    global _gaze_tracker_instance
    if _gaze_tracker_instance is None:
        _gaze_tracker_instance = GazeTracker()
    return _gaze_tracker_instance


def reset_gaze_tracker():
    """Reset gaze tracker instance"""
    global _gaze_tracker_instance
    if _gaze_tracker_instance is not None:
        _gaze_tracker_instance.reset()
