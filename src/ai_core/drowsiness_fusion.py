"""
============================================
🔗 Drowsiness Sensor Fusion
Combine eyes, mouth, head signals into a single score
============================================
"""
import time
from collections import deque
from typing import Deque, Tuple, Optional

from src.ai_core.perclos_detector import PERCLOSDetector, EyeState
from src.ai_core.smile_detector import SmileDetector
from src.ai_core.head_pose import HeadPoseEstimator


class NoddingDetector:
    """Simple nod (gật đầu) detector based on pitch minima patterns."""
    def __init__(self, min_nod_depth: float = 6.0, window_seconds: float = 2.0, cooldown: float = 1.0):
        self.history: Deque[Tuple[float, float]] = deque()
        self.window_seconds = window_seconds
        self.min_nod_depth = min_nod_depth
        self.last_nod_time = 0.0
        self.cooldown = cooldown

    def update(self, pitch: float, timestamp: Optional[float] = None) -> bool:
        if timestamp is None:
            timestamp = time.time()
        self.history.append((timestamp, pitch))
        # purge old
        cutoff = timestamp - self.window_seconds
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

        # cooldown
        if timestamp - self.last_nod_time < self.cooldown:
            return False

        # need at least 3 samples
        if len(self.history) < 3:
            return False

        # find local minimum (most negative pitch) in window
        min_t, min_pitch = min(self.history, key=lambda x: x[1])
        # ensure there is a recovery (pitch before and after min are higher by threshold)
        before = [p for t, p in self.history if t < min_t]
        after = [p for t, p in self.history if t > min_t]
        if not before or not after:
            return False

        if (max(before) - min_pitch) >= self.min_nod_depth and (max(after) - min_pitch) >= self.min_nod_depth:
            # detected nod
            self.last_nod_time = timestamp
            self.history.clear()
            return True

        return False


class HeadPoseTracker:
    """
    Theo dõi tư thế đầu với Độ trễ (Time Delay) và Vùng an toàn (Safe Zones).
    
    Logic:
    - Vùng an toàn (Safe Zone): Yaw trong khoảng -20 đến +20 độ -> An toàn (nhìn gương/thẳng).
    - Cảnh báo (Distracted): Yaw < -20 hoặc > 20 (hoặc Pitch < -20).
    - Độ trễ (Time Delay): Chỉ báo động nếu trạng thái Distracted kéo dài quá 'distraction_threshold' giây.
    """
    def __init__(self, safe_yaw_limit: float = 15.0, distraction_threshold: float = 2.0):
        self.safe_yaw_limit = safe_yaw_limit
        self.distraction_threshold = distraction_threshold # 2.0s delay
        
        self.distraction_start_time: Optional[float] = None
        self.is_distracted = False
        
    def update(self, pitch: float, yaw: float, timestamp: float) -> Tuple[bool, float]:
        """
        Cập nhật trạng thái đầu.
        Returns:
            (is_distracted_confirmed, duration)
            - is_distracted_confirmed: True nếu đã vượt quá thời gian cho phép.
            - duration: Thời gian đã quay đi (giây).
        """
        # 1. Kiểm tra xem có đang ở tư thế "Xấu" không?
        # Pitch < -20: Gật đầu/Cúi đầu (đã xử lý bởi NodDetector, nhưng cứ check thêm)
        # Yaw > 20 hoặc < -20: Quay trái/phải quá nhiều
        is_bad_pose = (abs(yaw) > self.safe_yaw_limit) or (pitch < -25.0)
        
        if is_bad_pose:
            if self.distraction_start_time is None:
                self.distraction_start_time = timestamp
            
            duration = timestamp - self.distraction_start_time
            
            # Chỉ Confirm là distracted nếu vượt quá threshold (2s)
            if duration > self.distraction_threshold:
                self.is_distracted = True
                return True, duration
            else:
                return False, duration
        else:
            # Tư thế an toàn -> Reset
            self.distraction_start_time = None
            self.is_distracted = False
            return False, 0.0


class DrowsinessFusion:
    """Implements the multimodal drowsiness scoring described by user.

    Score updates per frame:
      - eye closed: +1
      - yawn: +3
      - nod: +2
      - distraction (head): +2 (NEW)
      - normal: -1 (decay, floor 0)

    Also supports sunglasses detection (reduces eye weight) and returns actions.
    """

    def __init__(self,
                 decay_per_frame: int = 1,
                 yawn_weight: int = 3,
                 nod_weight: int = 2,
                 head_weight: int = 2, # [NEW] Trọng số cho distraction
                 eye_weight: int = 1,
                 sunglasses_window: float = 10.0,
                 sunglasses_zero_frac: float = 0.95):
        self.score = 0
        self.decay = decay_per_frame
        self.yawn_weight = yawn_weight
        self.nod_weight = nod_weight
        self.head_weight = head_weight
        self.eye_weight = eye_weight

        # Detectors
        self.nod_detector = NoddingDetector()
        self.head_tracker = HeadPoseTracker(safe_yaw_limit=20.0, distraction_threshold=2.0)

        # For sunglasses detection: store recent ear samples
        self.ear_history = deque()
        self.sunglasses_window = sunglasses_window
        self.sunglasses_zero_frac = sunglasses_zero_frac
        self.last_update = time.time()

    def _purge_ear(self, now: float):
        cutoff = now - self.sunglasses_window
        while self.ear_history and self.ear_history[0][0] < cutoff:
            self.ear_history.popleft()

    def update(self, ear: float, mar: float, is_yawning: bool, pitch: float, 
               timestamp: Optional[float] = None, is_smiling: bool = False,
               yaw: float = 0.0, ear_threshold: float = 0.22) -> dict: # [NEW] Added yaw and ear_threshold param
        
        now = timestamp or time.time()
        self.last_update = now

        # track ears
        self.ear_history.append((now, ear))
        self._purge_ear(now)

        # detect sunglasses: many zero / invalid ears in window
        zeros = sum(1 for t, e in self.ear_history if e <= 0.001)
        sunglasses = (len(self.ear_history) > 0) and (zeros / len(self.ear_history) >= self.sunglasses_zero_frac)

        # nod detection
        nod_detected = self.nod_detector.update(pitch, now)
        
        # [NEW] Head Distraction Detection with Delay
        is_distracted, distraction_duration = self.head_tracker.update(pitch, yaw, now)

        # Apply weights, but reduce eye contribution if sunglasses detected or smiling
        eye_contrib = 0
        if ear <= 0.0:
            # treat as eye closed
            eye_contrib = self.eye_weight
        else:
            # if ear below threshold consider partial closure
            # [IMPROVED] Dùng adaptive threshold từ bên ngoài truyền vào
            if ear < ear_threshold:
                eye_contrib = self.eye_weight

        if sunglasses:
            eye_contrib = 0  # ignore eye
            
        # [NEW] Nếu đang cười -> Bỏ qua mắt (vì mắt híp lại)
        if is_smiling:
            eye_contrib = 0
            
        # Update score
        if eye_contrib > 0:
            self.score += eye_contrib
        if is_yawning:
            self.score += self.yawn_weight
        if nod_detected:
            self.score += self.nod_weight
            
        # [NEW] Cộng điểm nếu bị phân tâm quá lâu
        if is_distracted:
            # Cộng điểm mỗi frame khi đang distracted
            self.score += self.head_weight

        # If everything normal, decay
        # Nếu đang cười thì cũng tính là "normal" để giảm score nhanh
        is_normal = (eye_contrib == 0 and not is_yawning and not nod_detected and not is_distracted)
        
        if is_normal or is_smiling:
            decay = self.decay * 3 if is_smiling else self.decay # Cười giúp tỉnh táo -> giảm nhanh hơn
            self.score = max(0, self.score - decay)

        # Clamp
        if self.score < 0: self.score = 0

        # Determine alert action
        action = None
        if self.score > 30:
            action = 'alarm'
        elif self.score > 15:
            action = 'beep'

        return {
            'score': int(self.score),
            'sunglasses': sunglasses,
            'nod': nod_detected,
            'distracted': is_distracted,       # [NEW]
            'distraction_duration': distraction_duration, # [NEW]
            'action': action
        }


# Singleton
fusion = DrowsinessFusion()

def get_fusion() -> DrowsinessFusion:
    return fusion

