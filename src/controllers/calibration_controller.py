import cv2
import time
import numpy as np
from src.ai_core.face_mesh import FaceMeshDetector, FaceLandmarks
from src.ai_core.features import FeatureExtractor
from src.models.user_model import user_model
from src.ai_core.drawer import frame_drawer

class CalibrationController:
    def __init__(self):
        self.face_detector = FaceMeshDetector()
        self.feature_extractor = FeatureExtractor()
        self.camera = None
        self.is_running = False
        
        # Dữ liệu thu thập
        self.ear_samples = []
        self.mar_samples = []
        self.calibration_frames = 150  # ~5 giây ở 30fps
        self._frame_width = 640
        self._frame_height = 480
        
    def start_camera(self, camera_index: int = 0):
        self.camera = cv2.VideoCapture(camera_index)
        # Try to set resolution (not all cameras respect it)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)
        self.is_running = True
        self.ear_samples = []
        self.mar_samples = []
        self._start_time = time.time()
        
    def stop_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_running = False

    def process_frame(self):
        if not self.camera or not self.is_running:
            return None, 0.0

        ret, frame = self.camera.read()
        if not ret:
            return None, 0.0
        
        frame = cv2.flip(frame, 1)
        faces = self.face_detector.detect(frame)
        
        # progress computed based on collected samples
        progress = min(len(self.ear_samples) / max(1, self.calibration_frames), 1.0)
        
        if faces:
            face = faces[0]
            features = self.feature_extractor.extract_all_features(face)
            
            # Thu thập mẫu EAR và MAR
            try:
                ear_val = float(features.get('ear', 0.0))
            except Exception:
                ear_val = 0.0
            self.ear_samples.append(ear_val)

            try:
                mar_val = float(features.get('mar', 0.0))
            except Exception:
                mar_val = 0.0
            self.mar_samples.append(mar_val)
            
            # Vẽ tiến trình
            cv2.putText(frame, f"Dang do... {int(progress*100)}%", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Vẽ một số điểm thưa để hiển thị (dùng pixel_landmarks nếu có)
            if hasattr(face, 'pixel_landmarks') and face.pixel_landmarks:
                for pt in face.pixel_landmarks[0:468:5]:
                    cv2.circle(frame, (int(pt[0]), int(pt[1])), 1, (0, 255, 255), -1)
            elif hasattr(face, 'landmarks') and face.landmarks:
                h, w = frame.shape[:2]
                for p in face.landmarks[0:468:5]:
                    x = int(p[0] * w)
                    y = int(p[1] * h)
                    cv2.circle(frame, (x, y), 1, (0, 255, 255), -1)
            elif hasattr(face, 'landmark') and face.landmark:
                # Legacy mediapipe objects
                h, w = frame.shape[:2]
                for lm in face.landmark[0:468:5]:
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    cv2.circle(frame, (x, y), 1, (0, 255, 255), -1)

            # Optional: draw ROI boxes
            try:
                frame = frame_drawer.draw_roi_boxes(frame, face)
            except Exception:
                pass

        # If we've collected enough samples, stop and mark done
        if len(self.ear_samples) >= self.calibration_frames:
            self.is_running = False
            progress = 1.0

        return frame, progress

    def finish_calibration(self, user_id: int):
        if not self.ear_samples:
            return False
            
        # Tính trung bình và ngưỡng
        avg_ear = float(np.mean(self.ear_samples))
        
        # Ngưỡng cảnh báo = 80% mức bình thường của người đó
        new_threshold = avg_ear * 0.8
        
        # Lưu vào Database
        try:
            user_model.update_settings(user_id, {'ear_threshold': new_threshold})
        except Exception:
            # If DB update fails, still return the computed value
            print("Cảnh báo: không lưu được vào cơ sở dữ liệu.")
        print(f"Đã hiệu chuẩn xong! Ngưỡng mới cho User {user_id}: {new_threshold:.3f}")
        return True
