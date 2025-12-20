"""
============================================
📹 Monitor Controller
Driver Drowsiness Detection System
Main monitoring and detection logic
============================================
"""

import cv2
import time
import numpy as np
from typing import Optional, Dict, Tuple, Callable
from datetime import datetime
import threading
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from src.ai_core.face_mesh import FaceMeshDetector, FaceLandmarks
from src.ai_core.features import FeatureExtractor
from src.ai_core.head_pose import HeadPoseEstimator
from src.ai_core.drawer import FrameDrawer
from src.models.alert_model import alert_model, session_model
from src.utils.constants import AlertType, AlertLevel, DetectionState, Colors, Thresholds, Messages
from src.utils.audio_manager import audio_manager
from src.utils.logger import logger


class MonitorController:
    """
    Main controller for drowsiness monitoring.
    Manages camera, detection, alerts, and logging.
    """
    
    def __init__(self, user_id: int = None):
        """Initialize monitor controller"""
        # Components
        self.face_detector = FaceMeshDetector()
        self.feature_extractor = FeatureExtractor()
        self.head_pose_estimator = HeadPoseEstimator()
        self.frame_drawer = FrameDrawer()
        
        # Camera
        self._camera: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._is_paused = False
        
        # User
        self._user_id: Optional[int] = user_id
        self._session_id: Optional[int] = None
        
        # Detection state
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE
        
        # Counters
        self._drowsy_frames = 0
        self._yawn_frames = 0
        self._head_down_frames = 0
        self._no_face_frames = 0
        
        # Timing
        self._start_time: Optional[float] = None
        self._last_alert_time: Optional[float] = None
        self._frame_count = 0
        self._fps = 0.0
        self._last_fps_time = time.time()
        
        # Current values
        self._current_ear = 0.0
        self._current_mar = 0.0
        self._current_pitch = 0.0
        self._current_yaw = 0.0
        
        # Callbacks
        self._on_frame_callback: Optional[Callable] = None
        self._on_alert_callback: Optional[Callable] = None
        self._on_state_change_callback: Optional[Callable] = None
        
        # Settings (can be customized per user)
        self._ear_threshold = config.EAR_THRESHOLD
        self._mar_threshold = config.MAR_THRESHOLD
        self._head_threshold = config.HEAD_PITCH_THRESHOLD
    
    def set_user(self, user_id: int) -> None:
        """Set current user and load their settings"""
        self._user_id = user_id
        
        # Load user settings from database
        from src.models.user_model import user_model
        settings = user_model.get_user_settings(user_id)
        
        if settings:
            self._ear_threshold = settings.get('ear_threshold', config.EAR_THRESHOLD)
            self._mar_threshold = settings.get('mar_threshold', config.MAR_THRESHOLD)
            self._head_threshold = settings.get('head_threshold', config.HEAD_PITCH_THRESHOLD)
            audio_manager.set_volume(settings.get('alert_volume', config.ALERT_VOLUME))
    
    def start_camera(self, camera_index: int = None) -> bool:
        """
        Start the camera.
        
        Args:
            camera_index: Camera device index
            
        Returns:
            True if successful
        """
        if camera_index is None:
            camera_index = config.CAMERA_INDEX
        
        try:
            self._camera = cv2.VideoCapture(camera_index)
            
            if not self._camera.isOpened():
                logger.error(f"Cannot open camera {camera_index}")
                return False
            
            # Set camera properties
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            self._camera.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)
            
            logger.info(f"Camera {camera_index} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self) -> None:
        """Stop and release the camera"""
        if self._camera:
            self._camera.release()
            self._camera = None
            logger.info("Camera stopped")
    
    def start_monitoring(self) -> bool:
        """
        Start the monitoring session.
        
        Returns:
            True if started successfully
        """
        if not self._camera or not self._camera.isOpened():
            if not self.start_camera():
                return False
        
        self._is_running = True
        self._is_paused = False
        self._start_time = time.time()
        self._frame_count = 0
        
        # Reset counters
        self._reset_counters()
        
        # Start driving session
        if self._user_id:
            self._session_id = session_model.start_session(self._user_id)
        
        logger.log_session_start(self._user_id or 0)
        
        return True
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring session"""
        self._is_running = False
        
        # Calculate duration
        duration = 0.0
        if self._start_time:
            duration = time.time() - self._start_time
        
        # End driving session
        if self._session_id:
            session_model.end_session(self._session_id)
        
        # Stop any playing alerts
        audio_manager.stop()
        
        # Log session end
        total_alerts = self._get_total_alerts()
        logger.log_session_end(self._user_id or 0, duration, total_alerts)
        
        # Reset
        self._session_id = None
        self._start_time = None
    
    def pause_monitoring(self) -> None:
        """Pause monitoring"""
        self._is_paused = True
        audio_manager.stop()
    
    def resume_monitoring(self) -> None:
        """Resume monitoring"""
        self._is_paused = False
        self._reset_counters()
    
    def _reset_counters(self) -> None:
        """Reset detection counters"""
        self._drowsy_frames = 0
        self._yawn_frames = 0
        self._head_down_frames = 0
        self._no_face_frames = 0
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE
    
    def _get_total_alerts(self) -> int:
        """Get total alerts in current session"""
        # This would be tracked through the session
        return 0
    
    def stop_alert(self) -> None:
        """Stop current audio alert"""
        audio_manager.stop()
    
    def process_external_frame(self, frame: np.ndarray) -> Dict:
        """
        Process an external frame (not from internal camera).
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            Dictionary with detection results and processed frame
        """
        if frame is None:
            return {'frame': None, 'ear': 0, 'mar': 0, 'pitch': 0, 'yaw': 0, 'alert_level': 0}
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Update FPS
        self._update_fps()
        
        # Detect faces
        faces = self.face_detector.detect(frame)
        
        result = {
            'frame': frame,
            'ear': 0.0,
            'mar': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'alert_level': 0,
            'alert_type': None,
            'alert_triggered': False,
            'face_detected': False
        }
        
        if not faces:
            # No face detected
            self._no_face_frames += 1
            cv2.putText(frame, "No Face Detected", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            result['frame'] = frame
            return result
        
        self._no_face_frames = 0
        face = faces[0]
        result['face_detected'] = True
        
        # Extract features
        features = self.feature_extractor.extract_all_features(face)
        ear = features.get('ear_smoothed', features.get('ear', 0))
        mar = features.get('mar_smoothed', features.get('mar', 0))
        
        # Estimate head pose
        pitch, yaw, roll = self.head_pose_estimator.estimate(face)
        
        result['ear'] = ear
        result['mar'] = mar
        result['pitch'] = pitch
        result['yaw'] = yaw
        
        # Check drowsiness
        alert_level = 0
        alert_type = None
        
        # Eyes closed check
        if ear < self._ear_threshold:
            self._drowsy_frames += 1
            if self._drowsy_frames >= config.EAR_CONSEC_FRAMES:
                alert_level = 2
                alert_type = 'DROWSY'
        else:
            self._drowsy_frames = 0
        
        # Yawning check
        if mar > self._mar_threshold:
            self._yawn_frames += 1
            if self._yawn_frames >= 10:
                if alert_level < 1:
                    alert_level = 1
                    alert_type = 'YAWN'
        else:
            self._yawn_frames = 0
        
        # Head down check (pitch > threshold means head tilted significantly)
        # Use absolute value to detect both head down and head up
        if abs(pitch) > self._head_threshold:
            self._head_down_frames += 1
            if self._head_down_frames >= 20:  # Increased to reduce false positives
                if alert_level < 2:
                    alert_level = 2
                    alert_type = 'HEAD_DOWN'
        else:
            self._head_down_frames = 0
        
        result['alert_level'] = alert_level
        result['alert_type'] = alert_type
        
        # Trigger alert and save to database (only once per alert event)
        if alert_level > 0:
            audio_manager.play_alert(alert_level)
            result['alert_triggered'] = True
            
            # Only log alert when it STARTS (not every frame)
            # Check if this is a NEW alert (previous state was normal)
            is_new_alert = not hasattr(self, '_last_alert_type') or self._last_alert_type != alert_type
            
            if is_new_alert:
                # Update internal state for logging
                self._alert_level = alert_level
                self._current_ear = ear
                self._current_mar = mar
                self._current_pitch = pitch
                self._current_yaw = yaw
                
                # Set detection state based on alert type
                if alert_type == 'DROWSY':
                    self._state = DetectionState.EYES_CLOSED
                elif alert_type == 'YAWN':
                    self._state = DetectionState.YAWNING
                elif alert_type == 'HEAD_DOWN':
                    self._state = DetectionState.HEAD_DOWN
                
                # Log alert to database (only once)
                self._log_alert()
            
            self._last_alert_type = alert_type
        else:
            # Reset when back to normal state
            self._last_alert_type = None
        
        # Draw on frame
        h, w = frame.shape[:2]
        
        # Draw EAR/MAR values
        cv2.putText(frame, f"EAR: {ear:.3f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"MAR: {mar:.3f}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Pitch: {pitch:.1f}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw alert
        if alert_level >= 2:
            cv2.putText(frame, "DROWSY ALERT!", (w//2 - 100, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            # Draw red border
            cv2.rectangle(frame, (0, 0), (w-1, h-1), (0, 0, 255), 5)
        elif alert_level == 1:
            cv2.putText(frame, "Warning!", (w//2 - 60, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        result['frame'] = frame
        return result

    def process_frame(self) -> Tuple[Optional[np.ndarray], Dict]:
        """
        Process a single frame from camera.
        
        Returns:
            Tuple of (processed_frame, detection_data)
        """
        if not self._camera or not self._is_running:
            return None, {}
        
        if self._is_paused:
            ret, frame = self._camera.read()
            if ret:
                cv2.putText(frame, "PAUSED", (250, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2, Colors.YELLOW, 3)
            return frame, {'state': 'paused'}
        
        # Read frame
        ret, frame = self._camera.read()
        if not ret:
            return None, {}
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Update FPS
        self._update_fps()
        
        # Detect faces
        faces = self.face_detector.detect(frame)
        
        detection_data = {
            'ear': 0.0,
            'mar': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'fps': self._fps,
            'state': self._state.value,
            'alert_level': self._alert_level.value,
            'face_detected': False
        }
        
        if not faces:
            # No face detected
            self._no_face_frames += 1
            self._state = DetectionState.NO_FACE
            
            # Reset other counters
            self._drowsy_frames = 0
            self._yawn_frames = 0
            self._head_down_frames = 0
            
            frame = self.frame_drawer.draw_no_face_message(frame)
            
        else:
            self._no_face_frames = 0
            face = faces[0]  # Use first detected face
            detection_data['face_detected'] = True
            
            # Extract features
            features = self.feature_extractor.extract_all_features(face)
            self._current_ear = features['ear_smoothed']
            self._current_mar = features['mar_smoothed']
            
            # Estimate head pose
            pitch, yaw, roll = self.head_pose_estimator.estimate(face)
            self._current_pitch = pitch
            self._current_yaw = yaw
            
            # Update detection data
            detection_data.update({
                'ear': self._current_ear,
                'mar': self._current_mar,
                'pitch': self._current_pitch,
                'yaw': self._current_yaw
            })
            
            # Check for drowsiness signs
            self._check_drowsiness()
            
            # Update state in detection data
            detection_data['state'] = self._state.value
            detection_data['alert_level'] = self._alert_level.value
            
            # Draw on frame
            eyes_closed = self._current_ear < self._ear_threshold
            yawning = self._current_mar > self._mar_threshold
            
            frame = self.frame_drawer.draw_face_mesh(frame, face)
            frame = self.frame_drawer.draw_eyes(frame, face, closed=eyes_closed)
            frame = self.frame_drawer.draw_mouth(frame, face, yawning=yawning)
            frame = self.frame_drawer.draw_bounding_box(
                frame, face, 
                color=Colors.get_status_color(self._alert_level)
            )
        
        # Draw status panel
        frame = self.frame_drawer.draw_status_panel(
            frame,
            self._current_ear,
            self._current_mar,
            self._current_pitch,
            self._current_yaw,
            self._fps,
            self._alert_level
        )
        
        # Draw alert overlay if needed
        if self._alert_level != AlertLevel.NONE:
            message = self._get_alert_message()
            frame = self.frame_drawer.draw_alert_overlay(frame, self._alert_level, message)
        
        # Call frame callback
        if self._on_frame_callback:
            self._on_frame_callback(frame, detection_data)
        
        return frame, detection_data
    
    def _check_drowsiness(self) -> None:
        """Check for drowsiness signs and trigger alerts"""
        prev_state = self._state
        prev_level = self._alert_level
        
        # Check eyes closed
        if self._current_ear < self._ear_threshold:
            self._drowsy_frames += 1
            self._state = DetectionState.EYES_CLOSED
        else:
            self._drowsy_frames = max(0, self._drowsy_frames - 2)  # Decay
        
        # Check yawning
        if self._current_mar > self._mar_threshold:
            self._yawn_frames += 1
            if self._state != DetectionState.EYES_CLOSED:
                self._state = DetectionState.YAWNING
        else:
            self._yawn_frames = max(0, self._yawn_frames - 1)
        
        # Check head down
        if self._current_pitch < -self._head_threshold:
            self._head_down_frames += 1
            if self._state == DetectionState.NORMAL:
                self._state = DetectionState.HEAD_DOWN
        else:
            self._head_down_frames = max(0, self._head_down_frames - 1)
        
        # Determine alert level
        self._alert_level = AlertLevel.NONE
        
        # Drowsy alerts (highest priority)
        if self._drowsy_frames >= Thresholds.DROWSY_FRAMES_LEVEL_3:
            self._alert_level = AlertLevel.CRITICAL
        elif self._drowsy_frames >= Thresholds.DROWSY_FRAMES_LEVEL_2:
            self._alert_level = AlertLevel.DANGER
        elif self._drowsy_frames >= Thresholds.DROWSY_FRAMES_LEVEL_1:
            self._alert_level = AlertLevel.WARNING
        
        # Yawn alert
        elif self._yawn_frames >= Thresholds.YAWN_FRAMES_MIN:
            self._alert_level = AlertLevel.WARNING
        
        # Head down alert
        elif self._head_down_frames >= Thresholds.DROWSY_FRAMES_LEVEL_1:
            self._alert_level = AlertLevel.WARNING
        
        # If normal, reset state
        if self._alert_level == AlertLevel.NONE:
            if self._drowsy_frames == 0 and self._yawn_frames == 0 and self._head_down_frames == 0:
                self._state = DetectionState.NORMAL
        
        # Trigger alerts
        if self._alert_level != AlertLevel.NONE:
            self._trigger_alert()
        else:
            audio_manager.stop()
        
        # State change callback
        if self._on_state_change_callback and (prev_state != self._state or prev_level != self._alert_level):
            self._on_state_change_callback(self._state, self._alert_level)
    
    def _trigger_alert(self) -> None:
        """Trigger audio and visual alerts"""
        current_time = time.time()
        
        # Cooldown between alerts (prevent spam)
        if self._last_alert_time and (current_time - self._last_alert_time) < 1.0:
            return
        
        # Play appropriate sound
        if self._alert_level == AlertLevel.CRITICAL:
            audio_manager.play_siren(loop=True)
        elif self._alert_level == AlertLevel.DANGER:
            audio_manager.play_alarm()
        elif self._alert_level == AlertLevel.WARNING:
            audio_manager.play_beep()
        
        self._last_alert_time = current_time
        
        # Log alert to database
        self._log_alert()
        
        # Alert callback
        if self._on_alert_callback:
            self._on_alert_callback(self._state, self._alert_level)
    
    def _log_alert(self) -> None:
        """Log current alert to database (Non-blocking / Async)"""
        # 1. Kiểm tra nhanh điều kiện
        if not self._user_id:
            return

        # 2. Xác định loại cảnh báo (Logic này chạy cực nhanh, làm ở Main Thread ok)
        if self._state == DetectionState.EYES_CLOSED:
            alert_type = AlertType.DROWSY
        elif self._state == DetectionState.YAWNING:
            alert_type = AlertType.YAWN
        elif self._state == DetectionState.HEAD_DOWN:
            alert_type = AlertType.HEAD_DOWN
        else:
            return

        # 3. ĐÓNG GÓI DỮ LIỆU (Snapshot)
        # Quan trọng: Phải lấy giá trị các biến ngay lúc này. 
        # Nếu đưa 'self._current_ear' vào trong thread, giá trị có thể bị thay đổi 
        # bởi vòng lặp camera tiếp theo trước khi thread kịp chạy.
        alert_data = {
            'user_id': self._user_id,
            'session_id': self._session_id,
            'alert_type': alert_type,
            'alert_level': self._alert_level,
            'ear': float(self._current_ear),
            'mar': float(self._current_mar),
            'pitch': float(self._current_pitch),
            'yaw': float(self._current_yaw),
            'duration': self._drowsy_frames / max(self._fps, 1)
        }

        # 4. Định nghĩa hàm chạy ngầm (Worker Function)
        def save_task(data):
            try:
                # Ghi vào DB (Thao tác tốn 50ms-100ms sẽ chạy ở đây)
                alert_model.log_alert(
                    user_id=data['user_id'],
                    alert_type=data['alert_type'],
                    alert_level=data['alert_level'],
                    ear_value=data['ear'],
                    mar_value=data['mar'],
                    head_pitch=data['pitch'],
                    head_yaw=data['yaw'],
                    duration=data['duration']
                )

                # Cập nhật Session
                if data['session_id']:
                    session_model.update_session_counts(
                        data['session_id'], 
                        data['alert_type']
                    )
                
                # Ghi Log file (Disk I/O)
                logger.log_alert(
                    data['alert_type'].value,
                    int(data['alert_level']),
                    data['ear'],
                    data['mar'],
                    data['pitch']
                )
            except Exception as e:
                # Nếu lỗi DB thì chỉ in ra log, không làm crash app
                print(f"❌ Error saving alert async: {e}")

        # 5. KHỞI CHẠY THREAD (Fire & Forget)
        # daemon=True: Thread này sẽ tự chết khi App chính tắt
        threading.Thread(target=save_task, args=(alert_data,), daemon=True).start()
    
    def _get_alert_message(self) -> str:
        """Get appropriate alert message based on state"""
        if self._state == DetectionState.EYES_CLOSED:
            if self._alert_level == AlertLevel.CRITICAL:
                return Messages.STATUS_CRITICAL
            elif self._alert_level == AlertLevel.DANGER:
                return Messages.STATUS_DANGER
            else:
                return Messages.STATUS_WARNING
        elif self._state == DetectionState.YAWNING:
            return Messages.STATUS_YAWN
        elif self._state == DetectionState.HEAD_DOWN:
            return Messages.ALERT_HEAD_DOWN
        
        return ""
    
    def _update_fps(self) -> None:
        """Update FPS counter"""
        self._frame_count += 1
        current_time = time.time()
        elapsed = current_time - self._last_fps_time
        
        if elapsed >= 1.0:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._last_fps_time = current_time
    
    # Callback setters
    def set_on_frame_callback(self, callback: Callable) -> None:
        """Set callback for each processed frame"""
        self._on_frame_callback = callback
    
    def set_on_alert_callback(self, callback: Callable) -> None:
        """Set callback for alerts"""
        self._on_alert_callback = callback
    
    def set_on_state_change_callback(self, callback: Callable) -> None:
        """Set callback for state changes"""
        self._on_state_change_callback = callback
    
    # Getters
    def is_running(self) -> bool:
        """Check if monitoring is running"""
        return self._is_running
    
    def is_paused(self) -> bool:
        """Check if monitoring is paused"""
        return self._is_paused
    
    def get_current_state(self) -> DetectionState:
        """Get current detection state"""
        return self._state
    
    def get_current_alert_level(self) -> AlertLevel:
        """Get current alert level"""
        return self._alert_level
    
    def get_fps(self) -> float:
        """Get current FPS"""
        return self._fps
    
    def get_session_duration(self) -> float:
        """Get current session duration in seconds"""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0
    
    # Settings
    def update_thresholds(self, ear: float = None, mar: float = None, 
                          head: float = None) -> None:
        """Update detection thresholds"""
        if ear is not None:
            self._ear_threshold = ear
        if mar is not None:
            self._mar_threshold = mar
        if head is not None:
            self._head_threshold = head
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop_monitoring()
        self.stop_camera()
        self.face_detector.release()
        audio_manager.cleanup()
        logger.info("Monitor controller cleaned up")


# Create singleton instance
monitor_controller = MonitorController()


def get_monitor_controller() -> MonitorController:
    """Get monitor controller instance"""
    return monitor_controller


if __name__ == "__main__":
    print("Monitor Controller Test")
    
    controller = MonitorController()
    
    if controller.start_monitoring():
        print("Monitoring started. Press 'q' to quit.")
        
        while controller.is_running():
            frame, data = controller.process_frame()
            
            if frame is not None:
                cv2.imshow('Drowsiness Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        controller.stop_monitoring()
        cv2.destroyAllWindows()
    
    controller.cleanup()
