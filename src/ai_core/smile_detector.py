"""
============================================
😊 Smile & Speech Detector (Production)
Driver Drowsiness Detection System
- Phân biệt: Cười / Nói / Ngáp / Bình thường
- Lọc false positive khi mắt híp
- Statistics đầy đủ
============================================
"""

import numpy as np
from typing import Tuple, Deque, Optional
from collections import deque
from dataclasses import dataclass
from enum import Enum
import time

from src.ai_core.face_mesh import FaceLandmarks
from config import mp_config


class MouthState(Enum):
    """Trạng thái miệng"""
    NEUTRAL = "NEUTRAL"      # Bình thường
    SMILING = "SMILING"      # Cười
    SPEAKING = "SPEAKING"    # Nói
    YAWNING = "YAWNING"      # Ngáp
    UNKNOWN = "UNKNOWN"


@dataclass
class SmileEvent:
    """Sự kiện cười"""
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    avg_confidence: float = 0.0


class SmileDetector:
    """
    Smile & Speech Detector
    
    Features:
    - Phân biệt cười/nói/ngáp
    - Lọc false positive
    - Event tracking
    """
    
    def __init__(self,
                 smile_mar_min: float = 0.10,       # Giảm min để bắt cười mỉm, cười ngậm miệng (MAR thấp)
                 smile_mar_max: float = 0.60,       # Giảm max (MAR cao quá là nói/ngáp)
                 smile_width_ratio: float = 2.2,    # Tăng ratio (Miệng phải bè ngang rõ rệt)
                 speaking_mar_min: float = 0.30,
                 speaking_mar_max: float = 0.55,
                 yawn_mar_min: float = 0.65,
                 ear_difference_max: float = 0.15,  # Tăng độ chênh lệch cho phép
                 confidence_threshold: float = 0.45, # Giảm confidence threshold
                 smile_window: int = 10):
        """
        Args:
            smile_mar_min: MAR tối thiểu khi cười
            smile_mar_max: MAR tối đa khi cười
            smile_width_ratio: Width/Height ratio khi cười
            speaking_mar_min: MAR tối thiểu khi nói
            speaking_mar_max: MAR tối đa khi nói
            yawn_mar_min: MAR tối thiểu khi ngáp
            ear_difference_max: Diff tối đa giữa 2 mắt
            confidence_threshold: Ngưỡng confidence
            smile_window: Window size cho smoothing
        """
        # Thresholds
        self.smile_mar_min = smile_mar_min
        self.smile_mar_max = smile_mar_max
        self.smile_width_ratio = smile_width_ratio
        self.speaking_mar_min = speaking_mar_min
        self.speaking_mar_max = speaking_mar_max
        self.yawn_mar_min = yawn_mar_min
        self.ear_difference_max = ear_difference_max
        self.confidence_threshold = confidence_threshold
        
        # History
        self._smile_confidence_history: Deque[float] = deque(maxlen=smile_window)
        self._mouth_state_history: Deque[MouthState] = deque(maxlen=smile_window)
        
        # State
        self._current_state = MouthState.NEUTRAL
        self._smile_active = False
        self._current_smile: Optional[SmileEvent] = None
        
        # Statistics
        self._smile_events: Deque[SmileEvent] = deque(maxlen=100)
        self._total_smiles = 0
        self._last_smile_time = 0.0
    
    def detect_mouth_state(self, face: FaceLandmarks, ear_left: float, 
                          ear_right: float, mar: float) -> Tuple[MouthState, float]:
        """
        Phát hiện trạng thái miệng
        
        Returns:
            (mouth_state, confidence)
        """
        # Validate landmarks exist
        try:
            mouth_ratio = self._calculate_mouth_ratio(face)
        except (KeyError, IndexError, AttributeError) as e:
            # Landmarks không hợp lệ
            return MouthState.UNKNOWN, 0.0
        
        # Calculate features
        ear_avg = (ear_left + ear_right) / 2
        ear_diff = abs(ear_left - ear_right)
        
        # === CLASSIFY MOUTH STATE ===
        
        # 1. Ngáp: MAR cao + mouth mở dọc
        if mar > self.yawn_mar_min and mouth_ratio < 1.5:
            state = MouthState.YAWNING
            confidence = min(1.0, (mar - self.yawn_mar_min) / 0.3)
        
        # 2. Cười: MAR vừa + mouth kéo ngang + mắt híp đều
        elif (self.smile_mar_min < mar < self.smile_mar_max and
              mouth_ratio > self.smile_width_ratio and
              0.05 < ear_avg < 0.30 and
              ear_diff < self.ear_difference_max):
            state = MouthState.SMILING
            # Tính confidence
            mar_score = 1.0 if self.smile_mar_min < mar < self.smile_mar_max else 0.5
            ratio_score = min(1.0, (mouth_ratio - self.smile_width_ratio) / 1.0)
            ear_score = 1.0 if 0.20 < ear_avg < 0.28 else 0.7
            sym_score = 1.0 if ear_diff < self.ear_difference_max else 0.5
            confidence = (mar_score + ratio_score + ear_score + sym_score) / 4.0
        
        # 3. Nói: MAR trung bình + mouth ratio trung bình
        elif (self.speaking_mar_min < mar < self.speaking_mar_max and
              1.5 < mouth_ratio < 2.5):
            state = MouthState.SPEAKING
            confidence = 0.6  # Moderate confidence
        
        # 4. Bình thường
        else:
            state = MouthState.NEUTRAL
            confidence = 1.0 - max(0, (mar - 0.20) / 0.5)  # Càng nhỏ càng neutral
        
        # === SMOOTHING ===
        self._smile_confidence_history.append(confidence)
        self._mouth_state_history.append(state)
        
        # Vote-based smoothing cho state
        if len(self._mouth_state_history) >= 5:
            state_counts = {}
            for s in self._mouth_state_history:
                state_counts[s] = state_counts.get(s, 0) + 1
            # Lấy state xuất hiện nhiều nhất
            smoothed_state = max(state_counts, key=state_counts.get)
        else:
            smoothed_state = state
        
        # Average confidence
        smoothed_confidence = np.mean(self._smile_confidence_history)
        
        # === UPDATE STATE ===
        self._update_state(smoothed_state, smoothed_confidence)
        
        return smoothed_state, smoothed_confidence
    
    def _update_state(self, state: MouthState, confidence: float):
        """Cập nhật state và ghi event"""
        now = time.time()
        prev_state = self._current_state
        self._current_state = state
        
        # === SMILE EVENT TRACKING ===
        if state == MouthState.SMILING and confidence > self.confidence_threshold:
            if not self._smile_active:
                # Bắt đầu cười → Tạo event mới
                self._smile_active = True
                self._current_smile = SmileEvent(start_time=now)
                self._last_smile_time = now
        else:
            if self._smile_active:
                # Kết thúc cười → Đóng event
                if self._current_smile:
                    self._current_smile.end_time = now
                    self._current_smile.duration = now - self._current_smile.start_time
                    self._current_smile.avg_confidence = confidence
                    
                    # Chỉ lưu nếu cười đủ lâu (> 0.3s)
                    if self._current_smile.duration > 0.3:
                        self._smile_events.append(self._current_smile)
                        self._total_smiles += 1
                    
                    self._current_smile = None
                
                self._smile_active = False
    
    def _calculate_mouth_ratio(self, face: FaceLandmarks) -> float:
        """
        Tính width/height ratio của miệng
        """
        # Get points (with error handling)
        try:
            left_pt = face.pixel_landmarks[mp_config.MOUTH_LEFT]
            right_pt = face.pixel_landmarks[mp_config.MOUTH_RIGHT]
            top_pt = face.pixel_landmarks[mp_config.MOUTH_TOP]
            bottom_pt = face.pixel_landmarks[mp_config.MOUTH_BOTTOM]
        except (KeyError, IndexError, AttributeError):
            # Fallback: Use hardcoded indices if mp_config missing
            left_pt = face.pixel_landmarks[61]
            right_pt = face.pixel_landmarks[291]
            top_pt = face.pixel_landmarks[0]
            bottom_pt = face.pixel_landmarks[17]
        
        # Calculate
        width = np.linalg.norm(np.array(left_pt) - np.array(right_pt))
        height = np.linalg.norm(np.array(top_pt) - np.array(bottom_pt))
        
        if height < 1e-6:  # Tránh chia 0
            return 0.0
        
        return width / height
    
    def is_smiling(self, face: FaceLandmarks, ear_left: float, 
                   ear_right: float, mar: float) -> Tuple[bool, float]:
        """
        Wrapper function tương thích với API cũ
        
        Returns:
            (is_smiling, confidence)
        """
        state, confidence = self.detect_mouth_state(face, ear_left, ear_right, mar)
        return (state == MouthState.SMILING, confidence)
    
    def is_speaking(self) -> bool:
        """Kiểm tra có đang nói không"""
        return self._current_state == MouthState.SPEAKING
    
    def is_yawning(self) -> bool:
        """Kiểm tra có đang ngáp không"""
        return self._current_state == MouthState.YAWNING
    
    def should_ignore_ear_drop(self, ear_avg: float) -> bool:
        """
        Kiểm tra có nên bỏ qua EAR giảm không (do cười)
        
        Returns:
            True nếu đang cười và EAR giảm là do cười
        """
        return (self._current_state == MouthState.SMILING and 
                0.05 < ear_avg < 0.30)
    
    def get_statistics(self) -> dict:
        """Lấy thống kê"""
        now = time.time()
        
        # Events trong 60s gần nhất
        recent_smiles = [e for e in self._smile_events if e.start_time >= now - 60]
        
        # Tính total smile duration
        total_duration = sum(e.duration for e in recent_smiles)
        
        return {
            'current_state': self._current_state.value,
            'is_smiling': self._smile_active,
            'total_smiles': self._total_smiles,
            'smiles_last_60s': len(recent_smiles),
            'smile_duration_last_60s': round(total_duration, 2),
            'last_smile_time': self._last_smile_time,
            'time_since_last_smile': round(now - self._last_smile_time, 1) if self._last_smile_time > 0 else None
        }
    
    def reset(self):
        """Reset detector"""
        self._smile_confidence_history.clear()
        self._mouth_state_history.clear()
        self._current_state = MouthState.NEUTRAL
        self._smile_active = False
        self._current_smile = None
        self._last_smile_time = 0.0


# Singleton
smile_detector = SmileDetector()


def get_smile_detector() -> SmileDetector:
    """Get singleton instance"""
    return smile_detector


if __name__ == "__main__":
    print("✅ Smile Detector (Production Version) - Ready")
    print("\nFeatures:")
    print("  - Phân biệt: Cười / Nói / Ngáp / Bình thường")
    print("  - Lọc false positive từ EAR drop")
    print("  - Event tracking với duration")
    print("  - Vote-based smoothing")