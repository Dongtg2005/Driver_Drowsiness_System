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
from src.ai_core.sunglasses_detector import SunglassesDetector  # [NEW] Sunglasses Detection
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
        self.sunglasses_detector = SunglassesDetector()  # [NEW] Kính râm detector
        
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
        
        # Sunglasses detection state tracking
        self._sunglasses_detected = False
        self._last_sunglasses_notification_time = 0.0
        self._auto_sunglasses_detected = False  # [NEW] Auto-detection result
        self._sunglasses_notification_cooldown = 30.0  # 30 giây cooldown
        
        # User settings storage (for sunglasses_mode, etc.)
        self._user_settings: Optional[Dict] = None
    
    def set_user(self, user_id: int) -> None:
        self._user_id = user_id
        try:
            from src.models.user_model import user_model
            settings = user_model.get_user_settings(user_id)
            if settings:
                self._user_settings = settings  # [FIX] Store full settings for runtime flags like sunglasses_mode
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
    
    def start_monitoring(self, spawn_camera: bool = True) -> bool:
        # [NEW] Force reload settings to ensure latest calibration is used
        if self._user_id:
            self.set_user(self._user_id)

        if spawn_camera:
            if not self._camera or not self._camera.isOpened():
                if not self.start_camera():
                    return False
        
        self._is_running = True
        self._is_paused = False
        self._start_time = time.time() # [RESTORED]
        self._reset_counters()
        self._last_alert_type: Optional[str] = None

        # Startup Grace Period
        self._startup_grace_period = 3.0 # seconds
        
        # Reset detectors to clean state
        self.feature_extractor.reset()
        
        # [NEW] Sync PERCLOS threshold with user settings
        try:
            from src.ai_core.perclos_detector import get_perclos_detector
            pd = get_perclos_detector()
            pd.set_threshold(self._ear_threshold)
        except Exception as e:
            logger.error(f"Failed to sync PERCLOS threshold: {e}")
        
        if self._user_id:
            self._session_id = session_model.start_session(self._user_id)
        logger.log_session_start(self._user_id or 0)
        return True

    def set_user(self, user_id: int) -> None:
        self._user_id = user_id
        try:
            from src.database.db_connection import execute_query
            # Fetch settings directly using raw SQL
            rows = execute_query("SELECT * FROM user_settings WHERE user_id = %s", (user_id,), fetch=True)
            if rows and len(rows) > 0:
                settings = rows[0]
                self._ear_threshold = float(settings.get('ear_threshold', config.EAR_THRESHOLD))
                self._mar_threshold = float(settings.get('mar_threshold', config.MAR_THRESHOLD))
                self._head_threshold = float(settings.get('head_threshold', config.HEAD_PITCH_THRESHOLD))
                vol = settings.get('alert_volume', config.ALERT_VOLUME)
                audio_manager.set_volume(float(vol) if vol is not None else 1.0)
                logger.info(f"Loaded settings for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
    
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
        
        # [NEW] Store current frame for sunglasses detector
        self._current_frame = frame.copy()

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
            if self._current_pitch < -10.0:
                 self._state = DetectionState.HEAD_DOWN
                 self._alert_level = AlertLevel.CRITICAL
                 self._trigger_alert(score=100)
                 msg = "PHAT HIEN GUC DAU"
                 frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, msg)
                 data['state'] = DetectionState.HEAD_DOWN.value
                 data['alert_level'] = AlertLevel.CRITICAL.value
                 return frame, data

            # [NEW] DISTRACTION PERSISTENCE
            # Nếu mất mặt khi đang quay đầu (Yaw lớn) -> Giả định vẫn đang quay đầu
            if abs(self._current_yaw) > 15.0:
                 # Tiếp tục update fusion với giá trị cũ để timer không bị reset
                 self._check_drowsiness_fusion(self._current_features, self._current_pitch, self._current_yaw, False)
                 
                 # Nếu fusion xác nhận distracted -> Báo động ngay
                 if self._state == DetectionState.DISTRACTED:
                     self._alert_level = AlertLevel.WARNING # Set warning level
                     self._trigger_alert(score=20) # Score đủ để trigger TTS priority 2
                     msg = "MAT TAP TRUNG"
                     frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, msg)
                     data['state'] = DetectionState.DISTRACTED.value
                     data['alert_level'] = self._alert_level.value
                     return frame, data

            # Nếu mất mặt quá 5 frames (và không phải gục đầu/quay đầu) -> Reset
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
        fusion_result = self._check_drowsiness_fusion(features, pitch, yaw, is_smiling)
        
        # 5.1. Handle Sunglasses Detection
        sunglasses_detected = fusion_result.get('sunglasses', False)
        if sunglasses_detected and not self._sunglasses_detected:
            # First time detection
            current_time = time.time()
            if current_time - self._last_sunglasses_notification_time > self._sunglasses_notification_cooldown:
                logger.warning("⚠️ [SUNGLASSES DETECTED] Switching to behavior monitoring mode (Eye tracking disabled, focusing on Head & Mouth)")
                # Voice notification (non-blocking)
                if config.ENABLE_TTS:
                    threading.Thread(
                        target=audio_manager.speak,
                        args=("Phát hiện kính râm. Chuyển sang chế độ giám sát hành vi.",),
                        daemon=True
                    ).start()
                self._last_sunglasses_notification_time = current_time
            self._sunglasses_detected = True
        elif not sunglasses_detected and self._sunglasses_detected:
            # No longer detected
            logger.info("✅ [SUNGLASSES CLEARED] Resuming normal eye tracking mode")
            self._sunglasses_detected = False

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
            'score': fusion_result.get('score', 0),
            'distracted': fusion_result.get('distracted', False),
            'gaze_distracted': fusion_result.get('gaze_distracted', False),
            'gaze_direction': features.get('gaze_direction', 'center'),
            'gaze_ratio': features.get('gaze_ratio', (0.0, 0.0)),
            'gaze_duration': fusion_result.get('gaze_duration', 0.0)
        })

        # Thông tin cảnh báo cho UI (Toast/đếm số)
        data['alert_triggered'] = (self._alert_level != AlertLevel.NONE)
        data['alert_message'] = self._get_alert_message() if self._alert_level != AlertLevel.NONE else ""
        if self._state == DetectionState.EYES_CLOSED:
            data['alert_type'] = 'DROWSY'
        elif self._state == DetectionState.YAWNING:
            data['alert_type'] = 'YAWN'
        elif self._state == DetectionState.HEAD_DOWN:
            data['alert_type'] = 'HEAD_DOWN'

        # 7. Drawing
        try:
            # Vẽ khung xanh/đỏ
            eyes_closed = self._state == DetectionState.EYES_CLOSED
            yawning = self._state == DetectionState.YAWNING
            
            frame = self.frame_drawer.draw_detected_outlines(frame, face)
            # Draw eyes with gaze tracking visualization
            gaze_ratio = data.get('gaze_ratio', (0.0, 0.0))
            draw_gaze = data.get('gaze_distracted', False) or abs(gaze_ratio[0]) > 0.2 or abs(gaze_ratio[1]) > 0.2
            frame = self.frame_drawer.draw_eyes(frame, face, closed=eyes_closed, 
                                               draw_iris=draw_gaze, gaze_ratio=gaze_ratio)
            # [REMOVED] Mouth Frame per user request
            # frame = self.frame_drawer.draw_mouth(frame, face, yawning=yawning)
            
            # [RESTORED] Head Bounding Box
            frame = self.frame_drawer.draw_bounding_box(
                frame, face, color=Colors.get_status_color(self._alert_level)
            )
            
            # Chuẩn bị Status Text (Icons)
            secondary_status = ""
            if is_smiling: secondary_status += "😊 Smiling "
            if features.get('is_just_blinking', False): secondary_status += "👁️ Blink "
            if data['sunglasses']: secondary_status += "🕶️ Sunglasses "
            if data.get('distracted'): secondary_status += "👀 Distracted "
            if data.get('gaze_distracted'): secondary_status += "👁️ Gaze Off "

            # Cập nhật lời gọi hàm draw_status_panel với Score và Status + Gaze
            frame = self.frame_drawer.draw_status_panel(
                frame, self._current_ear, self._current_mar,
                self._current_pitch, self._current_yaw, self._fps,
                self._alert_level, data['perclos'], str(self._state),
                score=data['score'], 
                secondary_status=secondary_status,
                gaze_direction=data.get('gaze_direction'),
                gaze_duration=data.get('gaze_duration', 0.0)
            )
            
            # Vẽ Sunglasses Warning Banner (nếu phát hiện)
            if data.get('sunglasses', False):
                frame = self.frame_drawer.draw_sunglasses_warning(frame, alpha=0.7)
            
            # Vẽ Gaze Distraction Warning (nếu phát hiện nhìn lệch khỏi đường)
            if data.get('gaze_distracted', False):
                frame = self.frame_drawer.draw_gaze_distraction_warning(
                    frame, 
                    data.get('gaze_direction', 'off_road'),
                    data.get('gaze_duration', 0.0),
                    alpha=0.75
                )
            
            # Vẽ Alert Overlay (nếu có) và được bật trong cấu hình
            if self._alert_level != AlertLevel.NONE and config.SHOW_ALERT_OVERLAY_ON_FRAME:
                msg = self._get_alert_message()
                frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, msg)
                
            # [REMOVED] Drawing manual text here to avoid overlap
            # status_text logic moved into draw_status_panel
                           
        except Exception as e:
            logger.error(f"Drawing error: {e}")

        # Callback
        if self._on_frame_callback:
            self._on_frame_callback(frame, data)

        return frame, data

    def _check_drowsiness_fusion(self, features: Dict, pitch: float, yaw: float, is_smiling: bool) -> Dict:
        """
        Sử dụng DrowsinessFusion Engine để đánh giá tổng thể.
        """
        is_yawning = (features.get('mar', 0) > self._mar_threshold)
        
        # Đọc manual sunglasses mode từ settings
        manual_sunglasses_mode = self._user_settings.get('sunglasses_mode', False) if self._user_settings else False
        
        # [NEW] Auto-detect kính râm bằng variance detector (chỉ khi chưa bật manual mode)
        auto_sunglasses_detected = False
        if not manual_sunglasses_mode:
            left_eye = features.get('left_eye_landmarks', [])
            right_eye = features.get('right_eye_landmarks', [])
            
            if left_eye and right_eye and hasattr(self, '_current_frame'):
                auto_sunglasses_detected, debug_info = self.sunglasses_detector.detect(
                    self._current_frame, left_eye, right_eye
                )
                self._auto_sunglasses_detected = auto_sunglasses_detected
        
        # Kết hợp manual và auto detection
        final_sunglasses_mode = manual_sunglasses_mode or auto_sunglasses_detected
        
        # Cập nhật Fusion Engine
        # EAR, MAR, Pitch, Yawn status, Timestamp, Smiling Status, Yaw, Sunglasses Mode (manual OR auto)
        # + Gaze Distraction (NEW)
        result = fusion.update(
            ear=features.get('ear', 0.3),
            mar=features.get('mar', 0.0),
            is_yawning=is_yawning,
            pitch=pitch,
            timestamp=time.time(),
            is_smiling=is_smiling,
            yaw=yaw,
            ear_threshold=self._ear_threshold,  # [NEW] Pass calibrated threshold
            manual_sunglasses_mode=final_sunglasses_mode,
            is_gaze_distracted=features.get('is_gaze_distracted', False),
            gaze_duration=features.get('gaze_duration', 0.0)
        )
        
        # Mapping action từ Fusion sang AlertLevel
        action = result.get('action')
        score = result.get('score', 0)
        is_distracted = result.get('distracted', False)
        is_gaze_distracted = result.get('gaze_distracted', False)
        
        # Xác định State & Alert Level
        if action == 'alarm':
            self._alert_level = AlertLevel.ALARM
            # Đoán nguyên nhân chính để set state
            # Prioritize gaze distraction first (most immediate danger)
            if is_gaze_distracted: self._state = DetectionState.DISTRACTED
            elif is_distracted: self._state = DetectionState.DISTRACTED
            elif is_yawning: self._state = DetectionState.YAWNING
            # Prioritize HEAD_DOWN if pitch is visibly down (<-12) during alarm, 
            # as looking down often causes low EAR (squinting/eyelids lowering)
            elif pitch < -12.0: self._state = DetectionState.HEAD_DOWN
            else: self._state = DetectionState.EYES_CLOSED
        elif action == 'beep':
            self._alert_level = AlertLevel.WARNING
            if is_gaze_distracted: self._state = DetectionState.DISTRACTED
            elif is_distracted: self._state = DetectionState.DISTRACTED
            elif is_yawning: self._state = DetectionState.YAWNING
            elif pitch < -12.0: self._state = DetectionState.HEAD_DOWN
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
        
        # [NEW] Kiểm tra startup grace period
        if self._start_time and (curr_time - self._start_time < self._startup_grace_period):
            return

        # TTS Logic (Smart Recommendations)
        if config.ENABLE_TTS:
            # Chỉ nói mỗi 8 giây một lần để tránh spam (đã giảm từ 10s xuống 8s cho phản ứng nhanh hơn)
            if not self._last_tts_time or (curr_time - self._last_tts_time) > 8.0:
                hint = ""
                
                # Priority 1: Critical Head Down / Microsleep
                if self._state == DetectionState.HEAD_DOWN:
                    hint = "Nguy hiểm! Đừng cúi đầu, hãy nhìn đường."
                elif score > 50: 
                    hint = "Nguy hiểm! Dừng xe ngay lập tức!"
                
                # Priority 2: Distraction (Quay đầu) - User reported this was missing
                elif self._state == DetectionState.DISTRACTED:
                    hint = "Vui lòng tập trung lái xe."
                
                # Priority 3: Yawning
                elif self._state == DetectionState.YAWNING:
                    hint = "Bạn đang ngáp nhiều. Hãy nghỉ ngơi."
                
                # Priority 4: General Drowsiness (High Score)
                elif score > 30:
                    hint = "Bạn đang buồn ngủ. Hãy tỉnh táo lại."
                
                if hint:
                    audio_manager.speak(hint)
                    self._last_tts_time = curr_time
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