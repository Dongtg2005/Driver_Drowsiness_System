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
      - distraction (head): +2
      - gaze distraction: +2 (NEW - Looking away from road)
      - normal: -1 (decay, floor 0)

    Also supports sunglasses detection (reduces eye weight) and returns actions.
    """

    def __init__(self,
                 decay_per_frame: int = 1,
                 yawn_weight: int = 3,
                 nod_weight: int = 2,
                 head_weight: int = 2, # Trọng số cho distraction
                 gaze_weight: int = 2, # [NEW] Trọng số cho gaze distraction
                 eye_weight: int = 1,
                 sunglasses_window: float = 3.0,  # Giảm xuống 3 giây
                 sunglasses_threshold: float = 0.20):  # Ngưỡng EAR cho kính râm (tăng để dễ phát hiện)
        self.score = 0
        self.decay = decay_per_frame
        self.yawn_weight = yawn_weight
        self.nod_weight = nod_weight
        self.head_weight = head_weight
        self.gaze_weight = gaze_weight
        self.eye_weight = eye_weight

        # Detectors
        self.nod_detector = NoddingDetector()
        self.head_tracker = HeadPoseTracker(safe_yaw_limit=20.0, distraction_threshold=2.0)

        # For sunglasses detection: store recent ear samples
        self.ear_history = deque()
        self.sunglasses_window = sunglasses_window
        self.sunglasses_threshold = sunglasses_threshold  # EAR < 0.20 = kính râm/che mắt
        self.sunglasses_detected_state = False  # Track state để tránh flicker
        self.last_update = time.time()

    def _purge_ear(self, now: float):
        cutoff = now - self.sunglasses_window
        while self.ear_history and self.ear_history[0][0] < cutoff:
            self.ear_history.popleft()

    def update(self, ear: float, mar: float, is_yawning: bool, pitch: float, 
               timestamp: Optional[float] = None, is_smiling: bool = False,
               yaw: float = 0.0, ear_threshold: float = 0.22, # [NEW] Added yaw and ear_threshold param
               manual_sunglasses_mode: bool = False,
               is_gaze_distracted: bool = False, gaze_duration: float = 0.0) -> dict:
        
        now = timestamp or time.time()
        self.last_update = now

        # track ears
        self.ear_history.append((now, ear))
        self._purge_ear(now)

        # detect sunglasses: AUTO detection HOẶC manual mode
        # AUTO: EAR thấp bất thường liên tục (< 0.20) hoặc = 0
        # MANUAL: User tự bật trong settings
        
        auto_sunglasses = False
        if not manual_sunglasses_mode:  # Chỉ auto-detect khi chưa bật manual
            low_ear_count = sum(1 for t, e in self.ear_history if e <= self.sunglasses_threshold)
            total_samples = len(self.ear_history)
            
            # Phát hiện kính râm nếu:
            # 1. Có đủ samples (ít nhất 60 frames ~ 2 giây)
            # 2. 70% frames có EAR < 0.20 (thấp hơn bình thường)
            if total_samples >= 60:
                ear_values = [e for t, e in self.ear_history]
                avg_ear = sum(ear_values) / len(ear_values)
                low_ear_ratio = low_ear_count / total_samples
                
                # Hysteresis: Giữ trạng thái để tránh flicker
                if self.sunglasses_detected_state:
                    # Đã detect → Chỉ tắt khi EAR tốt trở lại (> 60% frames bình thường)
                    auto_sunglasses = (low_ear_ratio >= 0.40)  # Ngưỡng thấp hơn để tắt
                else:
                    # Chưa detect → Cần 70% frames thấp để kích hoạt
                    auto_sunglasses = (low_ear_ratio >= 0.70)
                
                self.sunglasses_detected_state = auto_sunglasses
                
                # Debug logging mỗi 60 frames (2 giây)
                if total_samples % 60 == 0:
                    print(f"[DEBUG] EAR Stats - Avg: {avg_ear:.3f}, Low: {low_ear_count}/{total_samples} ({100*low_ear_ratio:.1f}%), Auto Sunglasses: {auto_sunglasses}")
        
        # Kết hợp AUTO và MANUAL mode
        sunglasses = manual_sunglasses_mode or auto_sunglasses
        
        # Debug log - hiển thị cả auto và manual
        if manual_sunglasses_mode:
            print(f"[DEBUG] Sunglasses Mode: MANUAL ✅ (sunglasses={sunglasses})")
        elif len(self.ear_history) >= 60 and len(self.ear_history) % 60 == 0:
            # Chỉ log khi có đủ samples và mỗi 2 giây
            ear_values = [e for t, e in self.ear_history]
            avg_ear = sum(ear_values) / len(ear_values)
            low_ear_count = sum(1 for t, e in self.ear_history if e <= self.sunglasses_threshold)
            low_ear_ratio = low_ear_count / len(self.ear_history)
            print(f"[DEBUG] Sunglasses Mode: AUTO - EAR: {avg_ear:.3f}, Low: {low_ear_count}/{len(self.ear_history)} ({100*low_ear_ratio:.1f}%), Detected: {auto_sunglasses}")

        # nod detection
        nod_detected = self.nod_detector.update(pitch, now)
        
        # [NEW] Head Distraction Detection with Delay
        is_distracted, distraction_duration = self.head_tracker.update(pitch, yaw, now)

        # Apply weights, but reduce eye contribution if smiling
        eye_contrib = 0
        if ear <= 0.0:
            # treat as eye closed
            eye_contrib = self.eye_weight
        else:
            # if ear below threshold consider partial closure
            # [IMPROVED] Dùng adaptive threshold từ bên ngoài truyền vào
            if ear < ear_threshold:
                eye_contrib = self.eye_weight

        # [FIXED] Kính râm: GIẢM độ tin cậy (x0.5) thay vì bỏ qua hoàn toàn
        # Lý do: EAR thấp có thể do kính râm HOẶC buồn ngủ → Vẫn cần cảnh báo nhưng ít nhạy hơn
        if sunglasses:
            eye_contrib = int(eye_contrib * 0.5)  # Giảm 50% trọng số thay vì bỏ qua
            
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
            
        # [NEW] Cộng điểm nếu bị phân tâm quá lâu (head pose)
        if is_distracted:
            # Cộng điểm mỗi frame khi đang distracted
            self.score += self.head_weight
        
        # [NEW] Cộng điểm nếu mắt nhìn xa khỏi đường (gaze distraction)
        if is_gaze_distracted:
            # Cộng điểm mỗi frame khi đang nhìn khác chỗ quá lâu
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
            'distracted': is_distracted,
            'distraction_duration': distraction_duration,
            'gaze_distracted': is_gaze_distracted,  # [NEW]
            'gaze_duration': gaze_duration,  # [NEW]
            'action': action
        }


# Singleton
fusion = DrowsinessFusion()

def get_fusion() -> DrowsinessFusion:
    return fusion

