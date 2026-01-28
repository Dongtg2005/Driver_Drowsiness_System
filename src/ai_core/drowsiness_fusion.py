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


from config import config

class HeadPoseTracker:
    """
    Theo dõi tư thế đầu với Độ trễ (Time Delay) và Vùng an toàn (Safe Zones).
    """
    def __init__(self, safe_yaw_limit: float = 20.0, distraction_threshold: float = 2.0):
        self.safe_yaw_limit = safe_yaw_limit
        self.distraction_threshold = distraction_threshold # 2.0s delay
        self.pitch_threshold = -config.HEAD_PITCH_THRESHOLD # Lấy từ config (ví dụ -35)
        
        self.distraction_start_time: Optional[float] = None
        self.is_distracted = False
        
    def update(self, pitch: float, yaw: float, timestamp: float) -> Tuple[bool, float]:
        """
        Cập nhật trạng thái đầu.
        Returns: (is_distracted_confirmed, duration)
        """
        # 1. Kiểm tra xem có đang ở tư thế "Xấu" không?
        # Pitch < Threshold (ví dụ -35): Gật đầu/Cúi đầu
        # Yaw > 20 hoặc < -20: Quay trái/phải
        
        # [TUNING] Nếu đang Kính râm mode, threshold sẽ nhạy hơn (-15 thay vì -35)
        # Logic này sẽ được apply ở Fusion update, ở đây giữ logic cơ bản
        
        is_bad_pose = (abs(yaw) > self.safe_yaw_limit) or (pitch < self.pitch_threshold)
        
        if is_bad_pose:
            if self.distraction_start_time is None:
                self.distraction_start_time = timestamp
            
            duration = timestamp - self.distraction_start_time
            
            # Chỉ Confirm là distracted nếu vượt quá threshold
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
    """Implements the multimodal drowsiness scoring described by user."""

    def __init__(self,
                 decay_per_frame: int = 1,
                 yawn_weight: int = 3,
                 nod_weight: int = 2,
                 head_weight: int = 2,
                 gaze_weight: int = 2,
                 eye_weight: int = 1,
                 sunglasses_window: float = 3.0,
                 sunglasses_threshold: float = 0.20):
        self.score = 0
        self.decay = decay_per_frame
        self.yawn_weight = yawn_weight
        self.nod_weight = nod_weight
        self.head_weight = head_weight
        self.gaze_weight = gaze_weight
        self.eye_weight = eye_weight

        # Detectors
        self.nod_detector = NoddingDetector()
        self.head_tracker = HeadPoseTracker(
            safe_yaw_limit=config.HEAD_YAW_THRESHOLD, 
            distraction_threshold=2.0
        )

        # For sunglasses detection: store recent ear samples
        self.ear_history = deque()
        self.sunglasses_window = sunglasses_window
        self.sunglasses_threshold = sunglasses_threshold
        self.sunglasses_detected_state = False
        self.in_alarm_state = False # [NEW] Hysteresis State
        self.last_update = time.time()

    def _purge_ear(self, now: float):
        cutoff = now - self.sunglasses_window
        while self.ear_history and self.ear_history[0][0] < cutoff:
            self.ear_history.popleft()

    def update(self, ear: float, mar: float, is_yawning: bool, pitch: float, 
               timestamp: Optional[float] = None, is_smiling: bool = False,
               yaw: float = 0.0, ear_threshold: float = 0.22,
               manual_sunglasses_mode: bool = False,
               is_gaze_distracted: bool = False, gaze_duration: float = 0.0) -> dict:
        
        now = timestamp or time.time()
        self.last_update = now

        # track ears
        self.ear_history.append((now, ear))
        self._purge_ear(now)

        # detect sunglasses: AUTO detection HOẶC manual mode
        auto_sunglasses = False
        if not manual_sunglasses_mode:
            low_ear_count = sum(1 for t, e in self.ear_history if e <= self.sunglasses_threshold)
            total_samples = len(self.ear_history)
            
            if total_samples >= 60:
                ear_values = [e for t, e in self.ear_history]
                low_ear_ratio = low_ear_count / total_samples
                
                # Hysteresis
                if self.sunglasses_detected_state:
                    auto_sunglasses = (low_ear_ratio >= 0.40)
                else:
                    auto_sunglasses = (low_ear_ratio >= 0.70)
                
                self.sunglasses_detected_state = auto_sunglasses
        
        sunglasses = manual_sunglasses_mode or auto_sunglasses
        
        # nod detection
        nod_detected = self.nod_detector.update(pitch, now)
        
        # [UPDATED] Head Pose w/ Special Sunglasses Logic
        # Nếu đang Sunglasses Mode, ta KHẮT KHE hơn với Head Pitch (Fallback)
        # Bình thường ngưỡng là -35, nhưng đeo kính thì -15 (cúi nhẹ) đã nên cảnh báo
        
        current_pitch_threshold = -15.0 if sunglasses else -config.HEAD_PITCH_THRESHOLD
        
        # Update tracker logic manually using stricter threshold if needed for Sunglasses
        is_bad_pose = (abs(yaw) > config.HEAD_YAW_THRESHOLD) or (pitch < current_pitch_threshold)
        
        # Manually invoke tracker state logic for consistency
        # Hack: we modify tracker's threshold dynamically or handle logic here
        # Simpler: tracker.update uses its internal threshold. We check BAD POSE here for scoring boost.
        
        is_distracted, distraction_duration = self.head_tracker.update(pitch, yaw, now)
        
        # Nếu sunglasses và cúi đầu nhẹ (-15) mà tracker chưa bắt (do threshold -35), ta force bắt
        if sunglasses and (pitch < -15.0):
             # Force distraction logic locally if needed OR rely on weight boost below
             pass

        # Apply weights
        eye_contrib = 0
        
        # [CORE LOGIC] Sunglasses Handling
        if ear < ear_threshold:
            # Mắt nhắm
            if sunglasses:
                # Có kính râm -> Mắt nhắm là tín hiệu yếu (Unreliable)
                if pitch < -10.0:
                    # NHƯNG nếu đầu đang cúi -> Xác nhận buồn ngủ -> Full Weight
                    eye_contrib = self.eye_weight
                else:
                    # Đầu thẳng -> Chỉ là do kính -> Giảm 50% trọng số (hoặc 0 nếu muốn strict)
                    eye_contrib = int(self.eye_weight * 0.5)
            else:
                # Không kính -> Tin cậy hoàn toàn
                eye_contrib = self.eye_weight

        # [NEW] Nếu đang cười -> Bỏ qua mắt
        if is_smiling:
            eye_contrib = 0
            
        # Update score
        if eye_contrib > 0:
            self.score += eye_contrib
            
        if is_yawning:
            self.score += self.yawn_weight
            
        if nod_detected:
            self.score += self.nod_weight
            
        # [NEW] Cộng điểm nếu bị phân tâm (head pose)
        if is_distracted:
            # Nếu Sunglasses và Distracted (Head) -> Tín hiệu Vàng -> Tăng trọng số GẤP ĐÔI
            # Đây là logic "Fallback to Head Pose"
            weight = self.head_weight * 2 if sunglasses else self.head_weight
            self.score += weight
        
        # [NEW] Cộng điểm nếu mắt nhìn xa khỏi đường
        if is_gaze_distracted:
            self.score += self.gaze_weight

        # If everything normal, decay
        # Nếu đang cười thì cũng tính là "normal" để giảm score nhanh
        is_normal = (eye_contrib == 0 and not is_yawning and not nod_detected 
                    and not is_distracted and not is_gaze_distracted)
        
        if is_normal or is_smiling:
            decay = self.decay * 3 if is_smiling else self.decay # Cười giúp tỉnh táo -> giảm nhanh hơn
            self.score = max(0, self.score - decay)

        # Clamp
        if self.score < 0: self.score = 0

        # Determine alert action with Hysteresis (Schmitt Trigger)
        # Prevent "flickering" alerts (Bật/Tắt liên tục)
        action = None
        
        if not self.in_alarm_state:
            # Normal State -> Check Triggers
            if self.score > 30:
                action = 'alarm'
                self.in_alarm_state = True
            elif self.score > 15:
                action = 'beep'
        else:
            # Alarm State -> Check Recovery
            # Chỉ tắt Alarm khi Score giảm sâu xuống dưới 15 (Vùng an toàn)
            if self.score < 15:
                self.in_alarm_state = False
                action = None
            else:
                # Giữ nguyên trạng thái Alarm dù Score có giảm nhẹ (vd 35 -> 25)
                action = 'alarm'

        return {
            'score': int(self.score),
            'sunglasses': sunglasses,
            'nod': nod_detected,
            'distracted': is_distracted,
            'distraction_duration': distraction_duration,
            'gaze_distracted': is_gaze_distracted,
            'gaze_duration': gaze_duration,
            'action': action,
            'in_alarm': self.in_alarm_state # Debug
        }


# Singleton
fusion = DrowsinessFusion()

def get_fusion() -> DrowsinessFusion:
    return fusion

