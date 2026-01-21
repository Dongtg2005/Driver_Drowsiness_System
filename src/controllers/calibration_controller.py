import cv2
import time
import threading
import numpy as np
from src.ai_core.face_mesh import FaceMeshDetector, FaceLandmarks
from src.ai_core.features import FeatureExtractor

from src.ai_core.drawer import frame_drawer

class CalibrationController:
    def __init__(self):
        self.face_detector = FaceMeshDetector()
        self.feature_extractor = FeatureExtractor()
        self.camera = None
        self.is_running = False
        self._thread = None
        self._latest_frame = None
        self._latest_progress = 0.0
        
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

        # Start background thread for capture + processing
        def _loop():
            try:
                while self.is_running and self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if not ret:
                        time.sleep(0.01)
                        continue

                    frame = cv2.flip(frame, 1)
                    faces = self.face_detector.detect(frame)

                    progress = min(len(self.ear_samples) / max(1, self.calibration_frames), 1.0)

                    if faces:
                        face = faces[0]
                        features = self.feature_extractor.extract_all_features(face)

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

                        # draw progress text
                        cv2.putText(frame, f"Dang do... {int(progress*100)}%", (50, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                        try:
                            frame = frame_drawer.draw_roi_boxes(frame, face)
                        except Exception:
                            pass

                    # update latest frame/progress for UI polling
                    self._latest_frame = frame
                    self._latest_progress = progress

                    # stop condition
                    if len(self.ear_samples) >= self.calibration_frames:
                        self.is_running = False
                        break

                    # small sleep to yield
                    time.sleep(0.01)
            except Exception as e:
                # ensure not to crash the thread
                print(f"❌ Calibration thread error: {e}")
                import traceback
                traceback.print_exc()
                self.is_running = False

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        
    def stop_camera(self):
        if self.camera:
            self.camera.release()
            self.camera = None
        self.is_running = False
        # join thread briefly
        try:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.5)
        except Exception:
            pass

    def process_frame(self):
        # Return latest processed frame and progress from background thread
        return self._latest_frame, self._latest_progress

    def finish_calibration(self, user_id: int):
        if not self.ear_samples:
            return False
            
        # Tính trung bình và ngưỡng
        avg_ear = float(np.mean(self.ear_samples))
        
        # Ngưỡng cảnh báo = 80% mức bình thường của người đó
        new_threshold = avg_ear * 0.7
        
        # Lưu vào Database
        saved = False
        try:
            from src.database.db_connection import execute_query
            # Update settings using raw SQL
            # Check if settings exist first, if not insert
            check = execute_query("SELECT id FROM user_settings WHERE user_id = %s", (user_id,), fetch=True)
            if check:
                execute_query("UPDATE user_settings SET ear_threshold = %s WHERE user_id = %s", (float(new_threshold), user_id))
            else:
                execute_query("INSERT INTO user_settings (user_id, ear_threshold) VALUES (%s, %s)", (user_id, float(new_threshold)))
            saved = True
        except Exception as e:
            # If DB update fails, still return the computed value
            print(f"Cảnh báo: không lưu được vào cơ sở dữ liệu: {e}")

        print(f"Đã hiệu chuẩn xong! Ngưỡng mới cho User {user_id}: {new_threshold:.3f}")
        # Trả về ngưỡng (float) để UI có thể hiển thị / áp dụng ngay lập tức
        return new_threshold if saved or not saved else new_threshold
