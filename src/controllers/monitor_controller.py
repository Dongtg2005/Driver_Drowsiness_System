"""
======================================================
📹 Monitor Controller (SQLAlchemy Version)
Driver Drowsiness Detection System
Main monitoring and detection logic
======================================================
"""

import cv2
import time
import numpy as np
from typing import Optional, Dict, Tuple, Callable
from datetime import datetime
import threading
import sys
import os
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from src.ai_core.face_mesh import FaceMeshDetector
from src.ai_core.features import FeatureExtractor
from src.ai_core.head_pose import HeadPoseEstimator
from src.ai_core.drawer import FrameDrawer
from src.utils.constants import AlertType, AlertLevel, DetectionState
from src.utils.audio_manager import audio_manager
from src.utils.logger import logger

# Import SQLAlchemy components and models
from src.database.connection import SessionLocal
from src.models.user_model import User
from src.models.user_settings_model import UserSettings
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession


class MonitorController:
    """
    Main controller for drowsiness monitoring, refactored with SQLAlchemy.
    """
    
    def __init__(self, user_id: Optional[int] = None):
        """Initialize monitor controller"""
        self.face_detector = FaceMeshDetector()
        self.feature_extractor = FeatureExtractor()
        self.head_pose_estimator = HeadPoseEstimator()
        self.frame_drawer = FrameDrawer()
        
        self._is_running = False
        self._user_id: Optional[int] = user_id
        self._session_id: Optional[int] = None
        
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE
        
        self._drowsy_frames = 0
        self._yawn_frames = 0
        self._head_down_frames = 0

        self._last_alert_time: Optional[float] = None

        self._current_ear = 0.0
        self._current_mar = 0.0
        self._current_pitch = 0.0

        # Settings with default values
        self._ear_threshold = config.EAR_THRESHOLD
        self._mar_threshold = config.MAR_THRESHOLD
        self._head_threshold = config.HEAD_PITCH_THRESHOLD

        if self._user_id:
            self.set_user(self._user_id)

    def set_user(self, user_id: int) -> None:
        """Set current user and load their settings from the database."""
        self._user_id = user_id
        db: Session = SessionLocal()
        try:
            settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
            if settings:
                self._ear_threshold = settings.ear_threshold
                self._mar_threshold = settings.mar_threshold
                self._head_threshold = settings.head_threshold
                audio_manager.set_volume(settings.alert_volume)
                logger.info(f"Loaded custom settings for user ID: {user_id}")
        except Exception as e:
            logger.error(f"Error loading settings for user {user_id}: {e}")
        finally:
            db.close()

    def start_monitoring(self) -> None:
        """Starts the monitoring session and creates a new driving session in the DB."""
        self._is_running = True
        self._reset_counters()

        if not self._user_id:
            logger.warning("Monitoring started without a user ID. Sessions and alerts will not be saved.")
            return

        db: Session = SessionLocal()
        try:
            new_session = DrivingSession(
                user_id=self._user_id,
                start_time=datetime.now(),
                status='ACTIVE'
            )
            db.add(new_session)
            db.commit()
            self._session_id = new_session.id
            logger.info(f"Started new driving session (ID: {self._session_id}) for user ID: {self._user_id}")
        except Exception as e:
            logger.error(f"Failed to start driving session for user {self._user_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def stop_monitoring(self) -> None:
        """Stops the monitoring session and updates the driving session in the DB."""
        self._is_running = False
        audio_manager.stop()
        
        if not self._session_id:
            return

        db: Session = SessionLocal()
        try:
            session_to_end = db.query(DrivingSession).filter(DrivingSession.id == self._session_id).first()
            if session_to_end:
                session_to_end.end_time = datetime.now()
                session_to_end.status = 'COMPLETED'
                db.commit()
                logger.info(f"Ended driving session (ID: {self._session_id})")
        except Exception as e:
            logger.error(f"Failed to end driving session {self._session_id}: {e}")
            db.rollback()
        finally:
            db.close()
        
        self._session_id = None

    def _reset_counters(self) -> None:
        """Reset detection counters."""
        self._drowsy_frames = 0
        self._yawn_frames = 0
        self._head_down_frames = 0
        self._state = DetectionState.NORMAL
        self._alert_level = AlertLevel.NONE

    def process_external_frame(self, frame: np.ndarray) -> Dict:
        """Processes an external frame and returns detection results."""
        if not self._is_running or frame is None:
            return {}

        frame = cv2.flip(frame, 1)
        faces = self.face_detector.detect(frame)
        
        result = {'frame': frame, 'ear': 0.0, 'mar': 0.0, 'pitch': 0.0, 'alert_level': 0, 'alert_triggered': False}
        
        if not faces:
            self._drowsy_frames = max(0, self._drowsy_frames - 1)
            self._yawn_frames = max(0, self._yawn_frames - 1)
            self._head_down_frames = max(0, self._head_down_frames - 1)
            return result

        face = faces[0]
        features = self.feature_extractor.extract_all_features(face)
        self._current_ear = features.get('ear', 0)
        self._current_mar = features.get('mar', 0)
        self._current_pitch, _, _ = self.head_pose_estimator.estimate(face)
        
        result.update({'ear': self._current_ear, 'mar': self._current_mar, 'pitch': self._current_pitch})
        
        self._check_drowsiness()
        
        if self._alert_level != AlertLevel.NONE:
            result['alert_level'] = self._alert_level.value
            result['alert_type'] = self._state.name
            result['alert_triggered'] = self._trigger_alert()
        
        # Drawing can be done here or in the view
        # For simplicity, let's assume the view handles drawing based on the result dict
        
        return result

    def _check_drowsiness(self) -> None:
        """Check for drowsiness signs and set internal state."""
        # Reset state if no signs are present
        self._state = DetectionState.NORMAL
        
        # Check eyes closed
        if self._current_ear < self._ear_threshold:
            self._drowsy_frames += 1
            self._state = DetectionState.EYES_CLOSED
        else:
            self._drowsy_frames = max(0, self._drowsy_frames - 2)

        # Check yawning
        if self._current_mar > self._mar_threshold:
            self._yawn_frames += 1
            if self._state == DetectionState.NORMAL: # Yawn is lower priority than eyes closed
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

        # Determine alert level based on state and frame counts
        if self._state == DetectionState.EYES_CLOSED:
            if self._drowsy_frames >= config.EAR_CONSEC_FRAMES_LEVEL_3: self._alert_level = AlertLevel.CRITICAL
            elif self._drowsy_frames >= config.EAR_CONSEC_FRAMES_LEVEL_2: self._alert_level = AlertLevel.ALARM
            elif self._drowsy_frames >= config.EAR_CONSEC_FRAMES: self._alert_level = AlertLevel.WARNING
            else: self._alert_level = AlertLevel.NONE
        elif self._state == DetectionState.YAWNING and self._yawn_frames >= 30: # Tăng lên ~1s để tránh nhầm với nói chuyện
            self._alert_level = AlertLevel.WARNING
        elif self._state == DetectionState.HEAD_DOWN and self._head_down_frames >= 20:
            self._alert_level = AlertLevel.WARNING
        else:
            self._alert_level = AlertLevel.NONE

    def _trigger_alert(self) -> bool:
        """Plays audio alert and logs the event. Returns True if a new alert was logged."""
        current_time = time.time()
        if self._last_alert_time and (current_time - self._last_alert_time) < 2.0: # Cooldown
            return False

        audio_manager.play_alert(self._alert_level.value)
        self._last_alert_time = current_time

        # Log alert to database in a separate thread to avoid blocking
        threading.Thread(target=self._log_alert_async, daemon=True).start()
        return True

    def _log_alert_async(self) -> None:
        """Logs the current alert to the database."""
        if not self._user_id or not self._session_id:
            return

        db: Session = SessionLocal()
        try:
            # Create and save the alert
            new_alert = AlertHistory(
                user_id=self._user_id,
                alert_type=self._state.name,
                alert_level=self._alert_level.value,
                ear_value=self._current_ear,
                mar_value=self._current_mar,
                head_pitch=self._current_pitch
            )
            db.add(new_alert)

            # Update session counts
            session = db.query(DrivingSession).filter(DrivingSession.id == self._session_id).first()
            if session:
                session.total_alerts += 1
                if self._state == DetectionState.EYES_CLOSED:
                    session.drowsy_count += 1
                elif self._state == DetectionState.YAWNING:
                    session.yawn_count += 1

            db.commit()
            logger.info(f"Logged alert {self._state.name} for user {self._user_id}")
        except Exception as e:
            logger.error(f"Async alert logging failed: {e}")
            db.rollback()
        finally:
            db.close()

    def stop_alert(self) -> None:
        """Stops the current audio alert."""
        audio_manager.stop()

    def cleanup(self) -> None:
        """Cleans up resources."""
        if self._is_running:
            self.stop_monitoring()
        self.face_detector.release()
        audio_manager.cleanup()
        logger.info("Monitor controller cleaned up")

# Singleton instance
monitor_controller = MonitorController()

def get_monitor_controller() -> MonitorController:
    """Get the singleton instance of the monitor controller."""
    return monitor_controller
