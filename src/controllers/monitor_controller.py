"""
============================================
📹 Monitor Controller (Final Optimized Version)
Driver Drowsiness Detection System
- Tích hợp Fast Recovery (Hồi phục nhanh)
- Tối ưu hóa code (Giảm lặp logic)
- Xử lý đa luồng cho Logging
- Tích hợp Sensor Fusion & TTS
============================================
"""

import cv2
import time
import numpy as np
from typing import Optional, Dict, Tuple, Callable
import threading
import sys
import os
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from src.ai_core.face_mesh import FaceMeshDetector
from src.ai_core.features import FeatureExtractor
from src.ai_core.head_pose import HeadPoseEstimator
from src.ai_core.drawer import FrameDrawer
from src.ai_core.drowsiness_fusion import fusion  # [NEW] Sensor Fusion
from src.ai_core.image_enhancer import enhance_image # [NEW] Night Mode
from src.models.alert_model import alert_model, session_model
from src.utils.constants import AlertType, AlertLevel, DetectionState, Colors, Messages
from src.utils.audio_manager import audio_manager
from src.utils.logger import logger


class MonitorController:
    """
    Main controller for drowsiness monitoring.
    Manages camera, detection, alerts, and logging.
    """
    
    def __init__(self, user_id: int = None):
        # Components
        self.face_detector = FaceMeshDetector()
        self.feature_extractor = FeatureExtractor()
        self.head_pose_estimator = HeadPoseEstimator()
        self.frame_drawer = FrameDrawer()
        
        # Camera
        self._camera: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._is_paused = False
        
        # User & Session
        self._user_id: Optional[int] = user_id
        self._session_id: Optional[int] = None
        
        # Detection state
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE
        
        # Counters (Bộ đếm)
        self._drowsy_frames = 0
        self._eyes_open_frames = 0  # [MỚI] Đếm thời gian tỉnh táo để hồi phục nhanh
        self._yawn_frames = 0
        self._head_down_frames = 0
        self._no_face_frames = 0
        
        # Timing
        self._start_time: Optional[float] = None
        self._last_alert_time: Optional[float] = None
        self._last_tts_time: Optional[float] = None # Cooldown cho TTS
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.time()
        
        # Current values
        self._current_ear = 0.0
        self._current_mar = 0.0
        self._current_pitch = 0.0
        self._current_yaw = 0.0
        self._current_features: Dict = {}
        
        # Callbacks
        self._on_frame_callback: Optional[Callable] = None
        self._on_alert_callback: Optional[Callable] = None
        self._on_state_change_callback: Optional[Callable] = None
        
        # Settings
        self._ear_threshold = config.EAR_THRESHOLD
        self._mar_threshold = config.MAR_THRESHOLD
        self._head_threshold = config.HEAD_PITCH_THRESHOLD
        
        # Alert tracking
        self._last_alert_type: Optional[str] = None
    
    def set_user(self, user_id: int) -> None:
        self._user_id = user_id
        try:
            from src.models.user_model import user_model
            settings = user_model.get_user_settings(user_id)
            if settings:
                self._ear_threshold = settings.get('ear_threshold', config.EAR_THRESHOLD)
                self._mar_threshold = settings.get('mar_threshold', config.MAR_THRESHOLD)
                self._head_threshold = settings.get('head_threshold', config.HEAD_PITCH_THRESHOLD)
                audio_manager.set_volume(settings.get('alert_volume', config.ALERT_VOLUME))
                logger.info(f"Loaded settings for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
    
    def start_camera(self, camera_index: int = None) -> bool:
        if camera_index is None:
            camera_index = config.CAMERA_INDEX
        try:
            self._camera = cv2.VideoCapture(camera_index)
            if not self._camera.isOpened():
                return False
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            self._camera.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)
            logger.info(f"Camera {camera_index} started")
            return True
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self) -> None:
        if self._camera:
            self._camera.release()
            self._camera = None
    
    def start_monitoring(self) -> bool:
        if not self._camera or not self._camera.isOpened():
            if not self.start_camera():
                return False
        
        self._is_running = True
        self._is_paused = False
        self._start_time = time.time()
        self._reset_counters()
        
        # Reset detectors to clean state
        self.feature_extractor.reset()
        
        if self._user_id:
            self._session_id = session_model.start_session(self._user_id)
        logger.log_session_start(self._user_id or 0)
        return True
    
    def stop_monitoring(self) -> None:
        self._is_running = False
        duration = time.time() - self._start_time if self._start_time else 0.0
        
        if self._session_id:
            session_model.end_session(self._session_id)
        
        audio_manager.stop()
        total_alerts = self._get_total_alerts()
        logger.log_session_end(self._user_id or 0, duration, total_alerts)
        
        self._session_id = None
        self.feature_extractor.reset()
    
    def pause_monitoring(self) -> None:
        self._is_paused = True
        audio_manager.stop()
    
    def resume_monitoring(self) -> None:
        self._is_paused = False
        self._reset_counters()
    
    def _reset_counters(self) -> None:
        self._drowsy_frames = 0
        self._eyes_open_frames = 0
        self._yawn_frames = 0
        self._head_down_frames = 0
        self._no_face_frames = 0
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE
    
    def _get_total_alerts(self) -> int:
        if self._session_id:
            try:
                s = session_model.get_session(self._session_id)
                return sum([s.drowsy_count, s.yawn_count, s.head_down_count]) if s else 0
            except Exception:
                return 0
        return 0
    
    # =========================================================================
    # CORE PROCESSING LOGIC (UNIFIED)
    # =========================================================================

    def _process_image_common(self, frame: np.ndarray, is_external: bool = False) -> Tuple[np.ndarray, Dict]:
        """
        Xử lý chung cho cả Camera và Video File.
        """
        if frame is None:
            return None, {}

        # 1. Preprocessing
        if not is_external:
            frame = cv2.flip(frame, 1)
        
        # [NIGHT MODE] Tăng sáng ảnh nếu được bật
        if config.ENABLE_NIGHT_MODE:
            frame = enhance_image(frame)

        self._update_fps()

        # 2. Detect Face
        faces = self.face_detector.detect(frame)
        
        # Default Data Package
        data = {
            'ear': 0.0, 'mar': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'perclos': 0.0,
            'fps': self._fps,
            'state': DetectionState.NORMAL.value,
            'alert_level': AlertLevel.NONE.value,
            'face_detected': False,
            'is_drowsy': False, 'is_smiling': False,
            'sunglasses': False, 'score': 0
        }

        # 3. Handle No Face
        if not faces:
            self._no_face_frames += 1
            
            # [CRITICAL UPDATE] LAST KNOWN STATE HEURISTIC
            # Nếu mất mặt nhưng trước đó đầu đang chúi xuống -> Gục đầu (Head Drop)
            # Ngưỡng -20 là khá sâu (đã tính là gục)
            if self._current_pitch < -20.0:
                 self._state = DetectionState.HEAD_DOWN
                 self._alert_level = AlertLevel.CRITICAL
                 # Kích hoạt báo động ngay (Không cần đợi counters)
                 self._trigger_alert(score=100)
                 
                 # Vẽ cảnh báo lên frame dù không thấy mặt
                 msg = "HEAD DROP DETECTED"
                 frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, msg)
                 data['state'] = DetectionState.HEAD_DOWN.value
                 data['alert_level'] = AlertLevel.CRITICAL.value
                 return frame, data

            # Nếu mất mặt quá 5 frames (và không phải gục đầu) -> Reset
            if self._no_face_frames > 5:
                self._state = DetectionState.NO_FACE
                self._reset_counters() # Reset hết để không lưu alert cũ
                audio_manager.stop()
            
            frame = self.frame_drawer.draw_no_face_message(frame)
            data['state'] = DetectionState.NO_FACE.value
            return frame, data

        # 4. Handle Face Detected
        self._no_face_frames = 0
        face = faces[0]
        data['face_detected'] = True

        # Extract Features
        features = self.feature_extractor.extract_all_features(face)
        self._current_features = features
        self._current_ear = features.get('ear', 0.0)
        self._current_mar = features.get('mar', 0.0)
        is_smiling = features.get('is_smiling', False)
        
        # Head Pose
        pitch, yaw, roll = self.head_pose_estimator.estimate(face)
        self._current_pitch = pitch
        self._current_yaw = yaw

        # 5. Check Drowsiness (Unified Logic via Fusion)
        fusion_result = self._check_drowsiness_fusion(features, pitch, is_smiling)

        # 6. Update Data with Fusion Results
        data.update({
            'ear': self._current_ear,
            'mar': self._current_mar,
            'pitch': self._current_pitch,
            'yaw': self._current_yaw,
            'perclos': features.get('perclos', 0.0),
            'state': self._state.value,
            'alert_level': self._alert_level.value,
            'is_drowsy': features.get('is_drowsy', False),
            'is_smiling': is_smiling,
            'sunglasses': fusion_result.get('sunglasses', False),
            'score': fusion_result.get('score', 0)
        })

        # 7. Drawing
        try:
            # Vẽ khung xanh/đỏ
            eyes_closed = self._state == DetectionState.EYES_CLOSED
            yawning = self._state == DetectionState.YAWNING
            
            frame = self.frame_drawer.draw_detected_outlines(frame, face)
            frame = self.frame_drawer.draw_eyes(frame, face, closed=eyes_closed)
            # [REMOVED] Mouth Frame per user request
            # frame = self.frame_drawer.draw_mouth(frame, face, yawning=yawning)
            
            # [RESTORED] Head Bounding Box
            frame = self.frame_drawer.draw_bounding_box(
                frame, face, color=Colors.get_status_color(self._alert_level)
            )
            
            # Vẽ bảng thông số
            perclos_val = features.get('perclos', 0.0)
            eye_state_val = features.get('eye_state', 'OPEN')
            if hasattr(eye_state_val, 'value'): eye_state_val = eye_state_val.value

            frame = self.frame_drawer.draw_status_panel(
                frame, self._current_ear, self._current_mar,
                self._current_pitch, self._current_yaw, self._fps,
                self._alert_level, perclos_val, str(eye_state_val)
            )
            
            # Vẽ Alert Overlay (nếu có)
            if self._alert_level != AlertLevel.NONE:
                msg = self._get_alert_message()
                frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, msg)
                
            # Vẽ trạng thái phụ & Score
            status_text = f"Score: {data['score']} "
            if is_smiling: status_text += "😊 Smiling "
            if features.get('is_just_blinking', False): status_text += "👁️ Blink "
            if data['sunglasses']: status_text += "🕶️ Sunglasses "
            
            if status_text:
                cv2.putText(frame, status_text, (10, frame.shape[0]-20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                           
        except Exception as e:
            logger.error(f"Drawing error: {e}")

        # Callback
        if self._on_frame_callback:
            self._on_frame_callback(frame, data)

        return frame, data

    def _check_drowsiness_fusion(self, features: Dict, pitch: float, is_smiling: bool) -> Dict:
        """
        Sử dụng DrowsinessFusion Engine để đánh giá tổng thể.
        """
        is_yawning = (features.get('mar', 0) > self._mar_threshold)
        
        # Cập nhật Fusion Engine
        # EAR, MAR, Pitch, Yawn status, Timestamp, Smiling Status
        result = fusion.update(
            ear=features.get('ear', 0.3),
            mar=features.get('mar', 0.0),
            is_yawning=is_yawning,
            pitch=pitch,
            timestamp=time.time(),
            is_smiling=is_smiling
        )
        
        # Mapping action từ Fusion sang AlertLevel
        action = result.get('action')
        score = result.get('score', 0)
        
        # Xác định State & Alert Level
        if action == 'alarm':
            self._alert_level = AlertLevel.ALARM
            # Đoán nguyên nhân chính để set state
            if is_yawning: self._state = DetectionState.YAWNING
            elif pitch < -self._head_threshold: self._state = DetectionState.HEAD_DOWN
            else: self._state = DetectionState.EYES_CLOSED
        elif action == 'beep':
            self._alert_level = AlertLevel.WARNING
        else:
            self._alert_level = AlertLevel.NONE
            self._state = DetectionState.NORMAL
        
        # Xử lý Trigger Alert
        if self._alert_level != AlertLevel.NONE:
            self._trigger_alert(score=score)
        else:
            self.stop_alert()
            
        return result

    # =========================================================================
    # PUBLIC API WRAPPERS
    # =========================================================================

    def process_frame(self) -> Tuple[Optional[np.ndarray], Dict]:
        """API cho Camera nội bộ"""
        if not self._camera or not self._is_running:
            return None, {}
        if self._is_paused:
            ret, frame = self._camera.read()
            if ret: cv2.putText(frame, "PAUSED", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
            return frame, {'state': 'paused'}

        ret, frame = self._camera.read()
        if not ret: return None, {}
        return self._process_image_common(frame, is_external=False)

    def process_external_frame(self, frame: np.ndarray) -> Dict:
        """API cho Video ngoài"""
        processed_frame, data = self._process_image_common(frame, is_external=True)
        if processed_frame is not None:
            data['frame'] = processed_frame
        return data

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _trigger_alert(self, score: int = 0) -> None:
        curr_time = time.time()
        
        # TTS Logic (Smart Recommendations)
        if config.ENABLE_TTS:
            # Chỉ nói mỗi 10 giây một lần để tránh spam
            if not self._last_tts_time or (curr_time - self._last_tts_time) > 10.0:
                hint = ""
                if score > 40: # Rất buồn ngủ
                    hint = "DANGER! Please stop the car immediately!"
                elif score > 30:
                    hint = "You are drowsy. Please wake up."
                elif self._state == DetectionState.YAWNING:
                    hint = "You are yawning too much."
                
                if hint:
                    audio_manager.speak(hint)
                    self._last_tts_time = curr_time

        # Âm thanh cảnh báo (Beep/Siren) vẫn chạy song song
        if self._last_alert_time and (curr_time - self._last_alert_time) < 0.5:
            return

        if self._alert_level == AlertLevel.CRITICAL:
            audio_manager.play_siren(loop=True)
        elif self._alert_level == AlertLevel.ALARM:
            audio_manager.play_alarm()
        elif self._alert_level == AlertLevel.WARNING:
            audio_manager.play_beep()
        
        self._last_alert_time = curr_time
        self._log_alert()
        
        if self._on_alert_callback:
            self._on_alert_callback(self._state, self._alert_level)
            
    def stop_alert(self) -> None:
        audio_manager.stop()

    def _log_alert(self) -> None:
        if not self._user_id: return
        
        # Xác định loại alert để log
        alert_type = None
        if self._state == DetectionState.EYES_CLOSED: alert_type = AlertType.DROWSY
        elif self._state == DetectionState.YAWNING: alert_type = AlertType.YAWN
        elif self._state == DetectionState.HEAD_DOWN: alert_type = AlertType.HEAD_DOWN
        else: return # Log other types?

        if self._last_alert_type == alert_type: return # Tránh duplicate liên tục
        self._last_alert_type = alert_type
        
        # Prepare data for async logging
        alert_data = {
            'user_id': self._user_id,
            'session_id': self._session_id,
            'alert_type': alert_type,
            'alert_level': self._alert_level,
            'ear': float(self._current_ear),
            'mar': float(self._current_mar),
            'pitch': float(self._current_pitch),
            'yaw': float(self._current_yaw),
            'perclos': float(self._current_features.get('perclos', 0.0)),
            'duration': self._drowsy_frames / max(self._fps, 1.0)
        }
        
        threading.Thread(target=self._async_log_task, args=(alert_data,), daemon=True).start()

    def _async_log_task(self, data: Dict):
        try:
            alert_model.log_alert(
                user_id=data['user_id'], alert_type=data['alert_type'],
                alert_level=data['alert_level'], ear_value=data['ear'],
                mar_value=data['mar'], head_pitch=data['pitch'],
                head_yaw=data['yaw'], duration=data['duration'],
                perclos=data['perclos']
            )
            if data['session_id']:
                session_model.update_session_counts(data['session_id'], data['alert_type'])
            
            logger.log_alert(data['alert_type'].value, int(data['alert_level']), 
                           data['ear'], data['mar'], data['pitch'], data['perclos'])
        except Exception as e:
            logger.error(f"Async log error: {e}")

    def _get_alert_message(self) -> str:
        if self._state == DetectionState.EYES_CLOSED:
            if self._alert_level == AlertLevel.CRITICAL: return Messages.STATUS_CRITICAL
            elif self._alert_level == AlertLevel.ALARM: return Messages.STATUS_DANGER
            else: return Messages.STATUS_WARNING
        elif self._state == DetectionState.YAWNING: return Messages.STATUS_YAWN
        elif self._state == DetectionState.HEAD_DOWN: return Messages.ALERT_HEAD_DOWN
        return ""

    def _update_fps(self) -> None:
        self._frame_count += 1
        elapsed = time.time() - self._last_fps_time
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = time.time()

    # Getters & Setters
    def set_on_frame_callback(self, cb): self._on_frame_callback = cb
    def set_on_alert_callback(self, cb): self._on_alert_callback = cb
    def set_on_state_change_callback(self, cb): self._on_state_change_callback = cb
    def is_running(self): return self._is_running
    def is_paused(self): return self._is_paused
    def update_thresholds(self, ear=None, mar=None, head=None):
        if ear: self._ear_threshold = ear
        if mar: self._mar_threshold = mar
        if head: self._head_threshold = head
    def cleanup(self):
        self.stop_monitoring()
        self.stop_camera()
        logger.info("Monitor controller cleaned up")


# Singleton
monitor_controller = MonitorController()
def get_monitor_controller() -> MonitorController:
    return monitor_controller

if __name__ == "__main__":
    print("✅ Monitor Controller (Optimized) - Ready")