"""
============================================
🎨 Drawing Utilities (Final Version)
Driver Drowsiness Detection System
Draw landmarks, boxes, and overlays on frames
============================================
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Config để đồng bộ ngưỡng cảnh báo
from config import config, mp_config
from src.utils.constants import Colors, AlertLevel
from src.ai_core.face_mesh import FaceLandmarks


class FrameDrawer:
    """
    Utility class for drawing on video frames.
    Draws landmarks, bounding boxes, status overlays, etc.
    """
    
    def __init__(self):
        """Initialize frame drawer"""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.thickness = 2
    
    def draw_face_mesh(self, image: np.ndarray, face: FaceLandmarks, 
                       color: Tuple[int, int, int] = Colors.GREEN,
                       draw_all: bool = False) -> np.ndarray:
        """
        Vẽ các điểm mốc trên khuôn mặt.
        """
        if draw_all:
            # Vẽ toàn bộ 468 điểm (chỉ dùng khi debug vì hơi rối)
            for point in face.pixel_landmarks:
                cv2.circle(image, point, 1, color, -1)
        else:
            # Chỉ vẽ các điểm chính (Mắt, Mũi, Miệng) cho gọn
            key_indices = (
                mp_config.LEFT_EYE + 
                mp_config.RIGHT_EYE + 
                [mp_config.MOUTH_TOP, mp_config.MOUTH_BOTTOM, 
                 mp_config.MOUTH_LEFT, mp_config.MOUTH_RIGHT,
                 mp_config.NOSE_TIP]
            )
            for idx in key_indices:
                point = face.pixel_landmarks[idx]
                cv2.circle(image, point, 1, color, -1)
        
        return image
    
    def draw_eyes(self, image: np.ndarray, face: FaceLandmarks,
                  color: Tuple[int, int, int] = Colors.YELLOW,
                  closed: bool = False) -> np.ndarray:
        """
        Vẽ viền mắt. Đổi màu đỏ nếu mắt nhắm.
        """
        draw_color = Colors.RED if closed else Colors.GREEN
        
        # Left eye
        left_eye_points = [face.pixel_landmarks[i] for i in mp_config.LEFT_EYE]
        left_eye_array = np.array(left_eye_points, dtype=np.int32)
        cv2.polylines(image, [left_eye_array], True, draw_color, 1)
        
        # Right eye
        right_eye_points = [face.pixel_landmarks[i] for i in mp_config.RIGHT_EYE]
        right_eye_array = np.array(right_eye_points, dtype=np.int32)
        cv2.polylines(image, [right_eye_array], True, draw_color, 1)
        
        return image
    
    def draw_mouth(self, image: np.ndarray, face: FaceLandmarks,
                   color: Tuple[int, int, int] = Colors.YELLOW,
                   yawning: bool = False) -> np.ndarray:
        """
        Vẽ khung chữ nhật bao quanh miệng (Thay cho hình thoi cũ).
        """
        draw_color = Colors.YELLOW if yawning else Colors.GREEN
        
        # Lấy 4 điểm cực trị của miệng
        try:
            indices = [
                mp_config.MOUTH_LEFT, 
                mp_config.MOUTH_RIGHT, 
                mp_config.MOUTH_TOP, 
                mp_config.MOUTH_BOTTOM
            ]
            
            points = []
            for idx in indices:
                points.append(face.pixel_landmarks[idx])
                
            if not points: 
                return image

            # Chuyển sang numpy để tính toán nhanh
            points_np = np.array(points, dtype=np.int32)
            
            # Tính toán hình chữ nhật bao quanh (Bounding Rect)
            # x, y là góc trái trên; w, h là chiều rộng, cao
            x, y, w, h = cv2.boundingRect(points_np)
            
            # Thêm khoảng đệm (padding) để khung không dính sát môi
            padding = 5
            
            # Vẽ hình chữ nhật
            cv2.rectangle(image, 
                          (x - padding, y - padding), 
                          (x + w + padding, y + h + padding), 
                          draw_color, 2) # Độ dày nét = 2
                          
        except Exception:
            pass # Bỏ qua nếu lỗi tính toán
        
        return image
    
    def draw_bounding_box(self, image: np.ndarray, face: FaceLandmarks,
                          color: Tuple[int, int, int] = Colors.GREEN,
                          label: str = None) -> np.ndarray:
        """
        Vẽ khung chữ nhật bao quanh mặt.
        """
        # Tính toán tọa độ bao
        x_coords = [p[0] for p in face.pixel_landmarks]
        y_coords = [p[1] for p in face.pixel_landmarks]
        
        # Thêm padding (lề) cho đẹp
        padding = 20
        x_min = max(0, min(x_coords) - padding)
        y_min = max(0, min(y_coords) - padding)
        x_max = min(face.image_width, max(x_coords) + padding)
        y_max = min(face.image_height, max(y_coords) + padding)
        
        # Vẽ khung (Bo góc nếu dùng cv2 nâng cao, ở đây dùng rectangle chuẩn)
        # Độ dày khung thay đổi theo màu (Cảnh báo thì đậm hơn)
        thickness = 3 if color == Colors.RED else 2
        
        # Vẽ 4 góc (Style Pro) hoặc vẽ full box
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, thickness)
        
        if label:
            cv2.putText(image, label, (x_min, y_min - 10),
                        self.font, self.font_scale, color, self.thickness)
        
        return image
    
    def draw_status_panel(self, image: np.ndarray, ear: float, mar: float,
                          pitch: float, yaw: float, fps: float,
                          alert_level: AlertLevel = AlertLevel.NONE,
                          perclos: float = 0.0,  # ← THÊM
                          eye_state: str = "OPEN") -> np.ndarray:  # ← THÊM
        """
        Vẽ bảng thông số kỹ thuật (HUD) bên góc trái.
        """
        h, w = image.shape[:2]
        
        # 1. Vẽ nền mờ (Semi-transparent background)
        panel_w = 220
        panel_h = 160
        overlay = image.copy()
        cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image) # Độ mờ 0.6
        
        # 2. Chuẩn bị thông số và màu sắc (Đồng bộ với Config)
        y_offset = 35
        line_height = 30
        x_text = 25
        
        # --- EAR (Mắt) ---
        ear_text = f"EAR: {ear:.2f} (T:{config.EAR_THRESHOLD:.2f})" 
        
        # Nếu muốn lấy ngưỡng thực tế từ monitor_controller (chính xác hơn)
        try:
            from src.controllers.monitor_controller import get_monitor_controller
            current_threshold = get_monitor_controller()._ear_threshold
            ear_text = f"EAR: {ear:.2f} / {current_threshold:.2f}"
        except:
            pass
        else:
            current_threshold = config.EAR_THRESHOLD
            
        ear_color = Colors.RED if ear < current_threshold else Colors.GREEN # Dùng ngưỡng thực để đổi màu
        cv2.putText(image, ear_text, (x_text, y_offset),
                self.font, 0.65, ear_color, 2)

        # --- PERCLOS (THÊM MỚI) ---
        y_offset += line_height
        perclos_percent = perclos * 100
        perclos_color = Colors.RED if perclos > 0.20 else Colors.GREEN
        cv2.putText(image, f"PERCLOS: {perclos_percent:.1f}%", (x_text, y_offset),
                self.font, 0.65, perclos_color, 2)

        # --- Eye State (THÊM MỚI) ---
        y_offset += line_height
        state_text = eye_state.replace("_", " ") if isinstance(eye_state, str) else str(eye_state)
        state_color = Colors.GREEN if state_text.upper() == "OPEN" else Colors.YELLOW
        cv2.putText(image, f"Eye: {state_text}", (x_text, y_offset),
                self.font, 0.55, state_color, 1)
        
        # --- MAR (Miệng) ---
        y_offset += line_height
        mar_color = Colors.YELLOW if mar > config.MAR_THRESHOLD else Colors.GREEN
        cv2.putText(image, f"MAR: {mar:.2f}", (x_text, y_offset),
                    self.font, 0.65, mar_color, 2)
        
        # --- Head Pitch (Gục đầu) ---
        y_offset += line_height
        # Pitch âm là cúi đầu
        pitch_color = Colors.RED if pitch < -config.HEAD_PITCH_THRESHOLD else Colors.GREEN
        cv2.putText(image, f"Pitch: {pitch:.1f}", (x_text, y_offset),
                    self.font, 0.65, pitch_color, 2)
        
        # --- Head Yaw (Quay ngang) ---
        y_offset += line_height
        yaw_val = abs(yaw)
        # Giả sử trong config chưa có HEAD_YAW_THRESHOLD, ta dùng tạm giá trị fix hoặc thêm vào config
        # Ở đây dùng 40 độ
        yaw_color = Colors.YELLOW if yaw_val > 40 else Colors.GREEN
        cv2.putText(image, f"Yaw: {yaw:.1f}", (x_text, y_offset),
                    self.font, 0.65, yaw_color, 2)
        
        # --- FPS ---
        y_offset += line_height
        cv2.putText(image, f"FPS: {int(fps)}", (x_text, y_offset),
                    self.font, 0.6, Colors.WHITE, 1)
        
        return image
    
    def draw_alert_overlay(self, image: np.ndarray, 
                           alert_level: AlertLevel,
                           message: str = "") -> np.ndarray:
        """
        Vẽ cảnh báo lớn giữa màn hình khi nguy hiểm.
        """
        if alert_level == AlertLevel.NONE:
            return image
        
        h, w = image.shape[:2]
        color = Colors.get_status_color(alert_level)
        
        # 1. Vẽ viền màn hình nhấp nháy (Giả lập bằng cách vẽ đè)
        border_thickness = 15 if alert_level == AlertLevel.CRITICAL else 8
        cv2.rectangle(image, (0, 0), (w, h), color, border_thickness)
        
        # 2. Vẽ thông báo nền đỏ/vàng giữa màn hình
        if message:
            # Tính kích thước chữ để căn giữa
            font_scale = 1.2
            thickness = 3
            text_size = cv2.getTextSize(message, self.font, font_scale, thickness)[0]
            
            text_x = (w - text_size[0]) // 2
            text_y = h - 50 # Vẽ ở gần đáy màn hình cho đỡ che mặt
            
            # Vẽ nền cho chữ dễ đọc
            padding = 10
            cv2.rectangle(image, 
                          (text_x - padding, text_y - text_size[1] - padding),
                          (text_x + text_size[0] + padding, text_y + padding),
                          color, -1) # Nền đặc
            
            # Vẽ chữ màu trắng (hoặc đen tùy nền)
            text_color = Colors.BLACK if alert_level == AlertLevel.WARNING else Colors.WHITE
            cv2.putText(image, message, (text_x, text_y),
                        self.font, font_scale, text_color, thickness)
            
        return image
    
    def draw_no_face_message(self, image: np.ndarray) -> np.ndarray:
        """Hiển thị thông báo khi không tìm thấy khuôn mặt"""
        h, w = image.shape[:2]
        msg = "KHONG TIM THAY MAT"
        
        text_size = cv2.getTextSize(msg, self.font, 1.0, 2)[0]
        text_x = (w - text_size[0]) // 2
        text_y = h // 2
        
        cv2.putText(image, msg, (text_x, text_y),
                    self.font, 1.0, Colors.WHITE, 2)
        return image

    def draw_detected_outlines(self, image: np.ndarray, face: FaceLandmarks) -> np.ndarray:
        """Draw green outlines around detected eyes, mouth and face bounding box.

        This is a convenience helper that forces green color to indicate 'recognized'.
        """
        if not face:
            return image

        # Draw eyes with green outline
        try:
            image = self.draw_eyes(image, face, color=Colors.GREEN, closed=False)
        except Exception:
            pass

        # Draw mouth with green outline
        try:
            image = self.draw_mouth(image, face, color=Colors.GREEN, yawning=False)
        except Exception:
            pass

        # Draw face bounding box in green
        try:
            image = self.draw_bounding_box(image, face, color=Colors.GREEN)
        except Exception:
            pass

        return image

    def draw_roi_boxes(self, image: np.ndarray, face_landmarks, alert_type: str = "NORMAL") -> np.ndarray:
        """Vẽ khung vùng quan tâm (mắt trái/phải, miệng).

        Hỗ trợ nhiều định dạng face_landmarks:
        - Our `FaceLandmarks` NamedTuple with `pixel_landmarks`
        - MediaPipe legacy object with `.landmark` having `.x`/`.y`
        - A simple container with `landmarks` as normalized tuples (x,y,...)
        """
        if not face_landmarks:
            return image

        h, w = image.shape[:2]

        # Convert to pixel coords list [(x,y), ...]
        pixel_points = None
        if hasattr(face_landmarks, 'pixel_landmarks') and face_landmarks.pixel_landmarks:
            pixel_points = [(int(p[0]), int(p[1])) for p in face_landmarks.pixel_landmarks]
        elif hasattr(face_landmarks, 'landmark') and face_landmarks.landmark:
            # MediaPipe legacy Landmark objects
            try:
                pixel_points = [(int(lm.x * w), int(lm.y * h)) for lm in face_landmarks.landmark]
            except Exception:
                pixel_points = None
        elif hasattr(face_landmarks, 'landmarks') and face_landmarks.landmarks:
            # Normalized tuple list [(x,y,z), ...]
            try:
                pixel_points = [(int(p[0] * w), int(p[1] * h)) for p in face_landmarks.landmarks]
            except Exception:
                pixel_points = None

        if not pixel_points:
            return image

        # Colors
        eye_color = Colors.GREEN
        mouth_color = Colors.GREEN
        if alert_type in ("DROWSY", "SLEEPING"):
            eye_color = Colors.RED
        elif alert_type == "YAWN":
            mouth_color = Colors.RED

        # Helper to compute bbox from indices
        def bbox_from_indices(indices):
            xs = [pixel_points[i][0] for i in indices if i < len(pixel_points)]
            ys = [pixel_points[i][1] for i in indices if i < len(pixel_points)]
            if not xs or not ys:
                return None, None
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            return (max(0, min_x - 5), max(0, min_y - 5)), (min(w, max_x + 5), min(h, max_y + 5))

        # Indices - prefer mp_config if available, else fall back to common indices
        try:
            left_idxs = mp_config.LEFT_EYE
            right_idxs = mp_config.RIGHT_EYE
            mouth_idxs = mp_config.MOUTH_OUTER if hasattr(mp_config, 'MOUTH_OUTER') else mp_config.MOUTH
        except Exception:
            left_idxs = [33, 133, 160, 159, 158, 144, 145, 153]
            right_idxs = [362, 263, 387, 386, 385, 373, 374, 380]
            mouth_idxs = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]

        # Draw left eye box
        p1, p2 = bbox_from_indices(left_idxs)
        if p1 and p2:
            cv2.rectangle(image, p1, p2, eye_color, 1)

        # Draw right eye box
        p1, p2 = bbox_from_indices(right_idxs)
        if p1 and p2:
            cv2.rectangle(image, p1, p2, eye_color, 1)

        # Draw mouth box
        p1, p2 = bbox_from_indices(mouth_idxs)
        if p1 and p2:
            cv2.rectangle(image, p1, p2, mouth_color, 1)

        return image


# Create singleton instance
frame_drawer = FrameDrawer()

def get_frame_drawer() -> FrameDrawer:
    return frame_drawer

if __name__ == "__main__":
    # Test nhanh
    print("Frame Drawer Initialized")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_drawer.draw_status_panel(img, 0.2, 0.8, -30, 10, 30.0)
    cv2.imshow("Test Drawer", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()