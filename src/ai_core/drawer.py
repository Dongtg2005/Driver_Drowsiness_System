"""
============================================
🎨 Drawing Utilities (Final Version)
Driver Drowsiness Detection System
Draw landmarks, boxes, and overlays on frames
Updated: UTF-8 Text Support & Refined Shapes
============================================
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional
import sys
import os
from PIL import Image, ImageDraw, ImageFont

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
        # Tải font cho PIL (để viết tiếng Việt)
        try:
            self.pil_font = ImageFont.truetype("arial.ttf", 20)
            self.pil_font_large = ImageFont.truetype("arial.ttf", 40)
            self.pil_font_small = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            self.pil_font = ImageFont.load_default()
            self.pil_font_large = ImageFont.load_default()
            self.pil_font_small = ImageFont.load_default()
    
    def put_text_utf8(self, image: np.ndarray, text: str, position: Tuple[int, int], 
                      color: Tuple[int, int, int], size: str = "normal") -> np.ndarray:
        """
        Vẽ text UTF-8 (Tiếng Việt) lên ảnh OpenCV bằng PIL
        """
        # Chuyển OpenCV (BGR) -> PIL (RGB)
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # Chọn font
        font = self.pil_font
        if size == "large": font = self.pil_font_large
        elif size == "small": font = self.pil_font_small
            
        # Chuyển màu BGR -> RGB
        rgb_color = (color[2], color[1], color[0])
        
        draw.text(position, text, font=font, fill=rgb_color)
        
        # Chuyển PIL (RGB) -> OpenCV (BGR)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

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
                mp_config.MOUTH_OUTER + 
                [mp_config.NOSE_TIP]
            )
            for idx in key_indices:
                if idx < len(face.pixel_landmarks):
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
        Vẽ đường bao quanh miệng (ôm sát viền môi).
        Sử dụng MOUTH_OUTER và polylines thay vì rectangle.
        """
        draw_color = Colors.YELLOW if yawning else Colors.GREEN
        
        try:
            # Sử dụng MOUTH_OUTER để lấy bao viền chính xác hơn
            indices = mp_config.MOUTH_OUTER
            
            points = []
            for idx in indices:
                points.append(face.pixel_landmarks[idx])
                
            if not points: 
                return image

            # Chuyển sang numpy
            points_np = np.array(points, dtype=np.int32)
            
            # Vẽ đường bao (Polygon) ôm sát miệng
            # isClosed=True để nối điểm cuối với điểm đầu
            cv2.polylines(image, [points_np], True, draw_color, 2)
                          
        except Exception:
            pass
        
        return image
    
    def draw_bounding_box(self, image: np.ndarray, face: FaceLandmarks,
                          color: Tuple[int, int, int] = Colors.GREEN,
                          label: str = None) -> np.ndarray:
        """
        Vẽ khung chữ nhật bao quanh mặt phong cách Sci-Fi (Reticle).
        """
        # Tính toán tọa độ bao
        x_coords = [p[0] for p in face.pixel_landmarks]
        y_coords = [p[1] for p in face.pixel_landmarks]
        
        # Thêm padding (lề) cho đẹp
        padding = 30 # Tăng padding cho thoáng
        x_min = max(0, min(x_coords) - padding)
        y_min = max(0, min(y_coords) - padding)
        x_max = min(face.image_width, max(x_coords) + padding)
        y_max = min(face.image_height, max(y_coords) + padding)
        
        w = x_max - x_min
        h = y_max - y_min
        
        # Thay vì vẽ rectangle full, vẽ Reticle 4 góc
        self._draw_reticle(image, (x_min, y_min, w, h), color)
        
        if label:
            image = self.put_text_utf8(image, label, (x_min + 5, y_min - 25), color)
        
        return image
    
    # -------------------------------------------------------------
    # 🎨 HUD / SCI-FI DRAWING METHODS
    # -------------------------------------------------------------

    def _draw_gauge(self, image: np.ndarray, center: Tuple[int, int], radius: int, 
                    value: float, max_value: float = 1.0, 
                    label: str = "", color: Tuple[int, int, int] = Colors.GREEN) -> np.ndarray:
        """
        Vẽ đồng hồ đo dạng vòng cung (Radial Gauge) phong cách Sci-Fi.
        """
        # Cấu hình cung tròn
        start_angle = 135
        total_angle = 270
        end_angle = start_angle + total_angle
        thickness = 8
        
        # 1. Vẽ cung nền (Mờ)
        cv2.ellipse(image, center, (radius, radius), 0, start_angle, end_angle, 
                   (50, 50, 50), thickness, cv2.LINE_AA)
        
        # 2. Vẽ cung giá trị (Active)
        ratio = min(max(value / max_value, 0.0), 1.0)
        current_end_angle = start_angle + (total_angle * ratio)
        
        # Màu sắc động nếu không chỉ định cụ thể
        # Nếu là EAR: nhỏ là xấu (Red), lớn là tốt (Green) -> Cần logic riêng bên ngoài truyền vào color
        
        cv2.ellipse(image, center, (radius, radius), 0, start_angle, current_end_angle, 
                   color, thickness, cv2.LINE_AA)
        
        # 3. Vẽ Label và Giá trị ở giữa
        font_scale_val = 0.7
        font_scale_lbl = 0.4
        
        # Draw Value
        val_str = f"{value:.2f}"
        (w_val, h_val), _ = cv2.getTextSize(val_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale_val, 2)
        cv2.putText(image, val_str, (center[0] - w_val//2, center[1] + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_val, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Draw Label
        (w_lbl, h_lbl), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale_lbl, 1)
        cv2.putText(image, label, (center[0] - w_lbl//2, center[1] + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale_lbl, (200, 200, 200), 1, cv2.LINE_AA)
                   
        return image

    def _draw_reticle(self, image: np.ndarray, rect: Tuple[int, int, int, int], 
                      color: Tuple[int, int, int]) -> np.ndarray:
        """
        Vẽ khung ngăm targets (Reticle) thay vì hình chữ nhật đơn điệu.
        Chỉ vẽ 4 góc.
        """
        x, y, w, h = rect
        len_line = int(min(w, h) * 0.25)
        thickness = 2
        
        # Top-Left
        cv2.line(image, (x, y), (x + len_line, y), color, thickness, cv2.LINE_AA)
        cv2.line(image, (x, y), (x, y + len_line), color, thickness, cv2.LINE_AA)
        
        # Top-Right
        cv2.line(image, (x + w, y), (x + w - len_line, y), color, thickness, cv2.LINE_AA)
        cv2.line(image, (x + w, y), (x + w, y + len_line), color, thickness, cv2.LINE_AA)
        
        # Bottom-Left
        cv2.line(image, (x, y + h), (x + len_line, y + h), color, thickness, cv2.LINE_AA)
        cv2.line(image, (x, y + h), (x, y + h - len_line), color, thickness, cv2.LINE_AA)
        
        # Bottom-Right
        cv2.line(image, (x + w, y + h), (x + w - len_line, y + h), color, thickness, cv2.LINE_AA)
        cv2.line(image, (x + w, y + h), (x + w, y + h - len_line), color, thickness, cv2.LINE_AA)
        
        return image

    def draw_status_panel(self, image: np.ndarray, ear: float, mar: float,
                          pitch: float, yaw: float, fps: float,
                          alert_level: AlertLevel = AlertLevel.NONE,
                          perclos: float = 0.0,
                          eye_state: str = "OPEN",
                          score: int = 0,
                          secondary_status: str = "") -> np.ndarray:
        """
        Vẽ giao diện HUD Sci-Fi thay thế bảng thông số cũ, chia 4 góc.
        """
        h, w = image.shape[:2]
        
        # --- 1. GÓC TRÁI DƯỚI: EAR GAUGE & PERCLOS ---
        # EAR Gauge
        ear_color = Colors.GREEN
        if ear < 0.20: ear_color = Colors.RED
        elif ear < 0.25: ear_color = Colors.YELLOW # YELLOW (Tuple) instead of WARNING (Hex)
        
        self._draw_gauge(image, center=(80, h - 80), radius=50, 
                        value=ear, max_value=0.4, label="EAR", color=ear_color)
        
        # PERCLOS Text (Dưới gauge)
        perclos_text = f"PERCLOS: {perclos*100:.1f}%"
        p_color = (0, 0, 255) if perclos > 0.2 else (0, 255, 0) # BGR
        cv2.putText(image, perclos_text, (20, h - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, p_color, 1, cv2.LINE_AA)

        # --- 2. GÓC PHẢI DƯỚI: MAR GAUGE ---
        mar_color = Colors.GREEN
        if mar > 0.7: mar_color = Colors.RED
        elif mar > 0.5: mar_color = Colors.YELLOW
        
        self._draw_gauge(image, center=(w - 80, h - 80), radius=50, 
                        value=mar, max_value=1.0, label="MAR", color=mar_color)
                        
        # --- 3. GÓC TRÁI TRÊN: HEAD POSE & SCORE ---
        # Vẽ Pitch / Yaw / Score
        y_start = 40
        x_start = 20
        gap = 25
        
        # Pitch
        pitch_color = (0, 0, 255) if pitch < -config.HEAD_PITCH_THRESHOLD else (0, 255, 255) # BGR
        cv2.putText(image, f"PITCH: {pitch:.1f}", (x_start, y_start), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, pitch_color, 2, cv2.LINE_AA)
        
        # Yaw
        yaw_val = abs(yaw)
        yaw_color = (0, 255, 255) if yaw_val > 40 else (0, 255, 0)
        cv2.putText(image, f"YAW:   {yaw:.1f}", (x_start, y_start + gap), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, yaw_color, 2, cv2.LINE_AA)
        
        # [MOVED FROM BOTTOM-LEFT] Score - Dời lên trên góc trái
        score_color = (255, 255, 255) # White
        if score > 30: score_color = (0, 255, 255) # Yellow
        if score > 60: score_color = (0, 0, 255) # Red
        # Tính toán vị trí Y để SCORE nằm ngay dưới YAW
        score_y = y_start + gap*2
        cv2.putText(image, f"SCORE: {score}", (x_start, score_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2, cv2.LINE_AA)
                   
        # Secondary Status (Smiling, Sunglasses...)
        if secondary_status:
            status_y = score_y + gap
            cv2.putText(image, secondary_status, (x_start, status_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

        # --- 4. GÓC PHẢI TRÊN: STATUS & FPS ---
        # State
        state_str = str(eye_state).replace("DetectionState.", "")
        if "NORMAL" not in state_str:
            state_color = (0, 255, 255) if "YAWN" in state_str else (0, 0, 255)
        else:
            state_color = (0, 255, 0)
            
        (tw, th), _ = cv2.getTextSize(state_str, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(image, state_str, (w - tw - 20, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2, cv2.LINE_AA)
                   
        # FPS
        fps_str = f"FPS: {int(fps)}"
        (fw, fh), _ = cv2.getTextSize(fps_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(image, fps_str, (w - fw - 20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                   
        return image
    
    def draw_alert_overlay(self, image: np.ndarray, 
                           alert_level: AlertLevel,
                           message: str = "") -> np.ndarray:
        """
        Vẽ cảnh báo lớn.
        """
        if alert_level == AlertLevel.NONE:
            return image
        
        h, w = image.shape[:2]
        color_bgr = Colors.get_status_color(alert_level)
        
        # 1. Vẽ viền nhấp nháy
        border_thickness = 15 if alert_level == AlertLevel.CRITICAL else 8
        cv2.rectangle(image, (0, 0), (w, h), color_bgr, border_thickness)
        
        # 2. Vẽ thông báo dùng PIL (Overlay)
        if message:
            # Chuyển sang RGBA để hỗ trợ độ trong suốt
            img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).convert("RGBA")
            # Tạo layer riêng để vẽ hình chữ nhật trong suốt
            overlay = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Dùng font lớn
            font = self.pil_font_large
            
            # Tính kích thước text
            bbox = draw.textbbox((0, 0), message, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            text_x = (w - text_w) // 2
            # [MODIFIED] Đưa lên trên cùng để đỡ che mặt
            text_y = 40 
            
            # Vẽ nền chữ (Semi-transparent)
            padding = 10
            # Màu nền theo Alert Level, Alpha = 200 (hơi trong suốt)
            fill_color = (color_bgr[2], color_bgr[1], color_bgr[0], 200)
            
            draw.rectangle(
                [(text_x - padding, text_y - padding), 
                 (text_x + text_w + padding, text_y + text_h + padding)],
                fill=fill_color
            )
            
            # Vẽ chữ (Đen hoặc Trắng), Opacity 100%
            text_color = (0, 0, 0, 255) if alert_level == AlertLevel.WARNING else (255, 255, 255, 255)
            draw.text((text_x, text_y), message, font=font, fill=text_color)
            
            # Gộp overlay vào ảnh gốc
            out = Image.alpha_composite(img_pil, overlay)
            return cv2.cvtColor(np.array(out.convert("RGB")), cv2.COLOR_RGB2BGR)
            
        return image
    
    def draw_no_face_message(self, image: np.ndarray) -> np.ndarray:
        """Hiển thị thông báo khi không tìm thấy khuôn mặt"""
        h, w = image.shape[:2]
        msg = "KHÔNG TÌM THẤY MẶT" # Có dấu
        
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = self.pil_font_large
        
        bbox = draw.textbbox((0, 0), msg, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        draw.text(((w - text_w)//2, h//2 - text_h), msg, font=font, fill=(255, 255, 255))
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def draw_detected_outlines(self, image: np.ndarray, face: FaceLandmarks) -> np.ndarray:
        """
        Vẽ các đường bao quanh mắt, miệng.
        Đã xoá khung bao quanh mặt (Head box) theo yêu cầu.
        """
        if not face:
            return image

        # Draw eyes
        try:
            image = self.draw_eyes(image, face, color=Colors.GREEN, closed=False)
        except Exception:
            pass

        # [REMOVED] Mouth with green outline (User request: delete mouth frame)
        # try:
        #    image = self.draw_mouth(image, face, color=Colors.GREEN, yawning=False)
        # except Exception:
        #    pass

        # Call draw_bounding_box REMOVED per user request ("ở đầu thì xóa đi")
        # try:
        #    image = self.draw_bounding_box(image, face, color=Colors.GREEN)
        # except Exception:
        #    pass

        return image

    def draw_roi_boxes(self, image: np.ndarray, face_landmarks, alert_type: str = "NORMAL") -> np.ndarray:
        """Legacy helper"""
        return image

# Create singleton instance
frame_drawer = FrameDrawer()

def get_frame_drawer() -> FrameDrawer:
    return frame_drawer

if __name__ == "__main__":
    print("Frame Drawer Initialized (Pillow Support)")