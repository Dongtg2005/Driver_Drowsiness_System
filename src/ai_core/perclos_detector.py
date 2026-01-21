"""
============================================
👁️ PERCLOS Detector (Fixed & Production-Ready)
Driver Drowsiness Detection System
- Adaptive EAR threshold (với validation)
- Real-time PERCLOS (chuẩn IEEE)
- Robust noise filtering
- Smile detection integration ready
============================================
"""

import time
import numpy as np
from typing import List, Tuple, Optional, Deque
from collections import deque
from dataclasses import dataclass
from enum import Enum

from src.utils.constants import AlertLevel


class EyeState(Enum):
    """Trạng thái mắt"""
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    BLINK = "BLINK"
    MICROSLEEP = "MICROSLEEP"
    DROWSY = "DROWSY"


@dataclass
class BlinkEvent:
    """Sự kiện chớp mắt"""
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    min_ear: float = 0.0
    is_drowsy: bool = False
    
    def close(self, end_time: float):
        """Đóng event"""
        self.end_time = end_time
        self.duration = end_time - self.start_time
    
    @property
    def is_complete(self) -> bool:
        return self.end_time is not None


class PERCLOSDetector:
    """
    PERCLOS-based Drowsiness Detector (Production Version)
    
    Improvements:
    - Robust noise filtering (median-based)
    - Safe adaptive threshold (với validation)
    - Accurate PERCLOS (frame-based, chuẩn IEEE)
    - Better statistics
    """
    
    def __init__(self,
                 blink_max_duration: float = 0.4,
                 microsleep_duration: float = 0.8,
                 drowsy_duration: float = 2.0,
                 perclos_window: float = 60.0,
                 perclos_threshold: float = 0.20):
        """
        Args:
            blink_max_duration: Thời gian tối đa của chớp mắt (400ms)
            microsleep_duration: Thời gian microsleep (800ms)
            drowsy_duration: Thời gian buồn ngủ (2s)
            perclos_window: Cửa sổ PERCLOS (60s)
            perclos_threshold: Ngưỡng PERCLOS (20%)
        """
        # Adaptive threshold
        self._adaptive_phase = True
        self._open_ear_samples: List[float] = []
        self._adaptive_time = 15.0  # 15 giây calibration
        self._adaptive_start = time.time()
        self.ear_threshold = 0.19  # Default, sẽ update sau calibration
        
        # Detection parameters
        self.blink_max_duration = blink_max_duration
        self.microsleep_duration = microsleep_duration
        self.drowsy_duration = drowsy_duration
        self.perclos_window = perclos_window
        self.perclos_threshold = perclos_threshold
        
        # History
        self._ear_history: Deque[Tuple[float, float]] = deque(maxlen=1800)  # 60s @ 30fps
        
        # State
        self._current_state = EyeState.OPEN
        self._previous_state = EyeState.OPEN
        self._current_blink: Optional[BlinkEvent] = None
        
        # Statistics
        self._blink_events: Deque[BlinkEvent] = deque(maxlen=100)
        self._total_blinks = 0
        self._total_microsleeps = 0
        self._total_drowsy_events = 0
        
        # PERCLOS
        self._perclos_value = 0.0
        self._last_perclos_update = time.time()
    
    def update(self, ear: float, timestamp: Optional[float] = None) -> Tuple[EyeState, float]:
        """
        Cập nhật detector với EAR mới
        
        Returns:
            (eye_state, perclos_value)
        """
        if timestamp is None:
            timestamp = time.time()
        
        # === PHASE 1: ADAPTIVE CALIBRATION ===
        if self._adaptive_phase:
            self._update_adaptive_threshold(ear)
        
        # === PHASE 2: NOISE FILTERING ===
        ear = self._filter_noise(ear)
        
        # === PHASE 3: SAVE HISTORY ===
        self._ear_history.append((timestamp, ear))
        
        # === PHASE 4: UPDATE STATE MACHINE ===
        self._update_state_machine(ear, timestamp)
        
        # === PHASE 5: UPDATE PERCLOS ===
        self._update_perclos(timestamp)
        
        return self._current_state, self._perclos_value
    
    def _update_adaptive_threshold(self, ear: float):
        """
        Adaptive threshold với validation
        """
        # Chỉ collect khi mắt mở rõ ràng
        if ear > 0.20:  # Threshold thấp hơn để tránh collect khi đang buồn ngủ
            self._open_ear_samples.append(ear)
        
        # Check nếu đủ thời gian
        elapsed = time.time() - self._adaptive_start
        if elapsed > self._adaptive_time:
            if len(self._open_ear_samples) >= 30:  # Cần ít nhất 30 samples
                # Lọc outliers: Lấy top 75% (bỏ 25% thấp nhất)
                sorted_samples = sorted(self._open_ear_samples)
                top_75_index = len(sorted_samples) // 4
                top_samples = sorted_samples[top_75_index:]
                
                mean_ear = np.mean(top_samples)
                std_ear = np.std(top_samples)
                
                # Validation: Mean phải hợp lý
                if 0.15 < mean_ear < 0.40 and std_ear < 0.08:  # Std không quá cao
                    # Tính threshold = 80% của mean
                    # [FIXED] Hạ thấp min clamp xuống 0.15 để hỗ trợ mắt nhỏ
                    self.ear_threshold = max(0.15, min(0.30, mean_ear * 0.80))
                    print(f"✅ Adaptive EAR threshold: {self.ear_threshold:.3f} (from {len(top_samples)} samples, mean={mean_ear:.3f})")
                else:
                    # Data không hợp lý → Dùng default an toàn
                    self.ear_threshold = 0.22 # Giảm default xuống chút
                    print(f"⚠️  Adaptive calibration failed (mean={mean_ear:.3f}, std={std_ear:.3f}). Using default: 0.22")
            else:
                # Không đủ data
                self.ear_threshold = 0.22
                print(f"⚠️  Not enough calibration data ({len(self._open_ear_samples)} samples). Using default: 0.22")
            
            self._adaptive_phase = False
    
    def _filter_noise(self, ear: float) -> float:
        """
        Lọc nhiễu bằng median filter
        """
        if len(self._ear_history) < 3:
            return ear
        
        # Lấy 3 giá trị gần nhất
        recent_ears = [e[1] for e in list(self._ear_history)[-3:]]
        median_ear = np.median(recent_ears)
        
        # Nếu khác biệt quá lớn với median (> 35% của median)
        threshold_diff = max(0.05, median_ear * 0.35)  # Ít nhất 0.05
        if abs(ear - median_ear) > threshold_diff:
            # Có thể là noise → Smooth về median
            return median_ear
        
        return ear
    
    def _update_state_machine(self, ear: float, timestamp: float):
        """State machine logic"""
        self._previous_state = self._current_state
        
        if ear < self.ear_threshold:
            # Mắt đóng
            if self._current_state == EyeState.OPEN:
                # Bắt đầu event mới
                self._current_state = EyeState.CLOSING
                self._current_blink = BlinkEvent(start_time=timestamp, min_ear=ear)
            else:
                # Tiếp tục đóng
                if self._current_blink:
                    self._current_blink.min_ear = min(self._current_blink.min_ear, ear)
                    duration = timestamp - self._current_blink.start_time
                    
                    # Phân loại theo duration
                    if duration < self.blink_max_duration:
                        self._current_state = EyeState.BLINK
                    elif duration < self.drowsy_duration:
                        self._current_state = EyeState.MICROSLEEP
                    else:
                        self._current_state = EyeState.DROWSY
        else:
            # Mắt mở
            if self._current_state != EyeState.OPEN:
                # Kết thúc event
                if self._current_blink and not self._current_blink.is_complete:
                    self._current_blink.close(timestamp)
                    self._classify_and_store_event(self._current_blink)
                    self._current_blink = None
                
                self._current_state = EyeState.OPEN
    
    def _classify_and_store_event(self, event: BlinkEvent):
        """Phân loại event"""
        duration = event.duration
        
        if duration < self.blink_max_duration:
            # Chớp mắt bình thường
            self._total_blinks += 1
            event.is_drowsy = False
        elif duration < self.drowsy_duration:
            # Microsleep
            self._total_microsleeps += 1
            event.is_drowsy = True
        else:
            # Drowsy
            self._total_drowsy_events += 1
            event.is_drowsy = True
        
        self._blink_events.append(event)
    
    def _update_perclos(self, current_time: float):
        """
        Tính PERCLOS theo chuẩn IEEE (frame-based)
        """
        if len(self._ear_history) < 30:  # Cần ít nhất 1s
            self._perclos_value = 0.0
            return
        
        # Lấy data trong window
        cutoff_time = current_time - self.perclos_window
        window_data = [(t, ear) for t, ear in self._ear_history if t >= cutoff_time]
        
        if not window_data:
            self._perclos_value = 0.0
            return
        
        # Đếm frame nhắm mắt
        closed_frames = sum(1 for _, ear in window_data if ear < self.ear_threshold)
        total_frames = len(window_data)
        
        # PERCLOS = % frames nhắm
        self._perclos_value = (closed_frames / total_frames) if total_frames > 0 else 0.0
        self._last_perclos_update = current_time
    
    def get_alert_level(self) -> AlertLevel:
        """Xác định mức cảnh báo"""
        # Priority 1: Drowsy state
        if self._current_state == EyeState.DROWSY:
            return AlertLevel.CRITICAL
        # Priority 2: Microsleep
        if self._current_state == EyeState.MICROSLEEP:
            return AlertLevel.ALARM

        # Priority 3: PERCLOS
        if self._perclos_value > self.perclos_threshold:
            if self._perclos_value > 0.35:
                return AlertLevel.CRITICAL
            elif self._perclos_value > 0.25:
                return AlertLevel.ALARM
            else:
                return AlertLevel.WARNING

        return AlertLevel.NONE
    
    def is_drowsy(self) -> bool:
        """Kiểm tra có buồn ngủ không"""
        return (self._current_state in [EyeState.MICROSLEEP, EyeState.DROWSY] or
                self._perclos_value > self.perclos_threshold)
    
    def is_just_blinking(self) -> bool:
        """Kiểm tra có phải chỉ chớp mắt bình thường"""
        return (self._current_state == EyeState.BLINK and 
                self._perclos_value < self.perclos_threshold)
    
    def get_statistics(self) -> dict:
        """Lấy thống kê chi tiết"""
        now = time.time()
        
        # Events trong 60s gần nhất
        recent_blinks = [e for e in self._blink_events 
                        if e.start_time >= now - 60 and not e.is_drowsy]
        recent_microsleeps = [e for e in self._blink_events 
                             if e.start_time >= now - 60 and e.is_drowsy 
                             and e.duration < self.drowsy_duration]
        recent_drowsy = [e for e in self._blink_events 
                        if e.start_time >= now - 60 
                        and e.duration >= self.drowsy_duration]
        
        return {
            'current_state': self._current_state.value,
            'perclos': round(self._perclos_value * 100, 2),  # %
            'ear_threshold': round(self.ear_threshold, 3),
            'is_calibrated': not self._adaptive_phase,
            
            # Total counts
            'total_blinks': self._total_blinks,
            'total_microsleeps': self._total_microsleeps,
            'total_drowsy': self._total_drowsy_events,
            
            # Recent (60s) counts
            'blinks_last_60s': len(recent_blinks),
            'microsleeps_last_60s': len(recent_microsleeps),
            'drowsy_last_60s': len(recent_drowsy),
            
            'alert_level': self.get_alert_level().value
        }
    
    def reset(self):
        """Reset detector"""
        self._ear_history.clear()
        self._current_state = EyeState.OPEN
        self._previous_state = EyeState.OPEN
        self._current_blink = None
        self._perclos_value = 0.0
        
        # Reset adaptive (giữ lại threshold đã học)
        # self._open_ear_samples.clear()
        # self._adaptive_phase = True
        # self._adaptive_start = time.time()


# Singleton instance
perclos_detector = PERCLOSDetector()


def get_perclos_detector() -> PERCLOSDetector:
    """Get singleton instance"""
    return perclos_detector


class PerclosDetector:
    """Compatibility wrapper for older tests/code expecting a simpler API.

    - Simulates frame timestamps using provided `fps` so tests can call `update()` in a tight loop.
    - Exposes `update(ear_value)` and `get_perclos_level()` and a `threshold` attribute.
    """
    def __init__(self, history_seconds: float = 60.0, fps: int = 30, threshold: float = 0.25):
        # Create underlying detector with reasonable defaults, then override ear threshold
        self._impl = PERCLOSDetector(perclos_window=history_seconds)
        # Treat provided `threshold` parameter as the user's configured EAR threshold target
        # but apply a safe scaling so small-eyed users are not falsely detected.
        self._user_threshold = float(threshold)
        # Set internal ear threshold to a fraction (80%) of configured threshold to allow
        # tolerance for small eyes. Clamp to a reasonable minimum.
        self._impl.ear_threshold = max(0.15, self._user_threshold * 0.80)
        # Disable adaptive calibration in the compatibility wrapper to keep deterministic tests
        self._impl._adaptive_phase = False

        self._fps = max(1, int(fps))
        self._frame_dt = 1.0 / float(self._fps)
        # start synthetic time slightly in the past to allow history build-up
        self._current_time = time.time() - history_seconds

    @property
    def threshold(self) -> float:
        return float(self._user_threshold)

    def update(self, ear_value: float):
        """Update with a single frame's EAR value. Returns the current perclos value."""
        state, perclos = self._impl.update(ear_value, timestamp=self._current_time)
        # advance synthetic time by one frame
        self._current_time += self._frame_dt
        return perclos

    def get_perclos_level(self) -> float:
        return float(self._impl._perclos_value)

    def reset(self):
        self._impl.reset()


if __name__ == "__main__":
    print("✅ PERCLOS Detector (Fixed Version) - Ready to use")