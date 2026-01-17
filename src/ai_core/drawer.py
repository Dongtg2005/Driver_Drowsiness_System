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
        
        # Vẽ khung
        thickness = 3 if color == Colors.RED else 2
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, thickness)
        
        if label:
            image = self.put_text_utf8(image, label, (x_min, y_min - 25), color)
        
        return image
    
    def draw_status_panel(self, image: np.ndarray, ear: float, mar: float,
                          pitch: float, yaw: float, fps: float,
                          alert_level: AlertLevel = AlertLevel.NONE,
                          perclos: float = 0.0,
                          eye_state: str = "OPEN") -> np.ndarray:
        """
        Vẽ bảng thông số kỹ thuật (HUD) dùng Pillow để hỗ trợ UTF-8.
        """
        h, w = image.shape[:2]
        
        # 1. Vẽ nền mờ (Giữ nguyên OpenCV cho nhanh)
        panel_w = 260 # Rộng hơn chút để chứa text
        panel_h = 240 # Cao hơn để chứa thêm thông tin
        sub_img = image[10:10+panel_h, 10:10+panel_w]
        black_rect = np.zeros(sub_img.shape, dtype=np.uint8)
        
        res = cv2.addWeighted(sub_img, 0.4, black_rect, 0.6, 1.0)
        image[10:10+panel_h, 10:10+panel_w] = res
        
        # 2. Chuyển sang PIL drawing
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        x_text = 25
        y_offset = 20
        line_height = 30
        
        # --- EAR (Mắt) ---
        # Lấy threshold thực tế
        current_ear_thresh = config.EAR_THRESHOLD
        try:
            from src.controllers.monitor_controller import get_monitor_controller
            current_ear_thresh = get_monitor_controller()._ear_threshold
        except: pass
            
        ear_text = f"Eye (EAR): {ear:.2f} / {current_ear_thresh:.2f}"
        ear_color = (0, 255, 0) if ear >= current_ear_thresh else (255, 0, 0) # RGB: Green/Red
        draw.text((x_text, y_offset), ear_text, font=self.pil_font, fill=ear_color)
        
        # --- PERCLOS ---
        y_offset += line_height
        perclos_text = f"PERCLOS: {perclos*100:.1f}%"
        perclos_color = (255, 0, 0) if perclos > 0.20 else (0, 255, 0) # Red if > 20%
        draw.text((x_text, y_offset), perclos_text, font=self.pil_font, fill=perclos_color)

        # --- Eye State ---
        y_offset += line_height
        state_text = f"State: {str(eye_state).replace('_', ' ')}"
        state_color = (0, 255, 0) if "OPEN" in str(eye_state) else (255, 255, 0)
        draw.text((x_text, y_offset), state_text, font=self.pil_font, fill=state_color)
        
        # --- MAR (Miệng) ---
        y_offset += line_height
        mar_color = (255, 255, 0) if mar > config.MAR_THRESHOLD else (0, 255, 0)
        draw.text((x_text, y_offset), f"Mouth (MAR): {mar:.2f}", font=self.pil_font, fill=mar_color)
        
        # --- Head Pitch ---
        y_offset += line_height
        pitch_color = (255, 0, 0) if pitch < -config.HEAD_PITCH_THRESHOLD else (0, 255, 0)
        draw.text((x_text, y_offset), f"Head Pitch: {pitch:.1f}", font=self.pil_font, fill=pitch_color)
        
        # --- Head Yaw ---
        y_offset += line_height
        yaw_val = abs(yaw)
        yaw_color = (255, 255, 0) if yaw_val > 40 else (0, 255, 0)
        draw.text((x_text, y_offset), f"Head Yaw: {yaw:.1f}", font=self.pil_font, fill=yaw_color)
        
        # --- FPS ---
        y_offset += line_height
        draw.text((x_text, y_offset), f"FPS: {int(fps)}", font=self.pil_font, fill=(255, 255, 255))
        
        # Convert back to OpenCV
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
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
        
        # 2. Vẽ thông báo dùng PIL
        if message:
            img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            # Dùng font lớn
            font = self.pil_font_large
            
            # Tính kích thước text (ước lượng hoặc dùng bbox nếu có)
            bbox = draw.textbbox((0, 0), message, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            text_x = (w - text_w) // 2
            text_y = h - 80
            
            # Vẽ nền chữ
            padding = 10
            draw.rectangle(
                [(text_x - padding, text_y - padding), 
                 (text_x + text_w + padding, text_y + text_h + padding)],
                fill=(color_bgr[2], color_bgr[1], color_bgr[0]) # BGR -> RGB fill
            )
            
            # Vẽ chữ (Đen hoặc Trắng)
            text_color = (0, 0, 0) if alert_level == AlertLevel.WARNING else (255, 255, 255)
            draw.text((text_x, text_y), message, font=font, fill=text_color)
            
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
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