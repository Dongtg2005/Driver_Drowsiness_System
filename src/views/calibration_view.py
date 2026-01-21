import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
from src.controllers.calibration_controller import CalibrationController
from src.utils.audio_manager import get_audio_manager

class CalibrationView(ctk.CTkFrame):
    def __init__(self, master, on_finish, user_id: int = 1):
        super().__init__(master)
        self.on_finish = on_finish
        self.user_id = user_id
        self.controller = CalibrationController()
        self._imgtk = None
        self.audio = get_audio_manager()
        self._last_speech_milestone = -1
        
        # Giao diện
        self.lbl_title = ctk.CTkLabel(self, text="HIỆU CHUẨN HỆ THỐNG", font=("Arial", 24, "bold"))
        self.lbl_title.pack(pady=20)
        
        self.lbl_guide = ctk.CTkLabel(self, text="Nhìn thẳng vào camera trong 5 giây\nđể hệ thống đo mắt của bạn.", font=("Arial", 16))
        self.lbl_guide.pack(pady=10)
        
        self.camera_frame = ctk.CTkLabel(self, text="")
        self.camera_frame.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)
        
        self.btn_start = ctk.CTkButton(self, text="BẮT ĐẦU", command=self.start_calibration, height=40, width=200)
        self.btn_start.pack(pady=10)

    def start_calibration(self):
        self.controller.start_camera()
        self.btn_start.configure(state="disabled", text="ĐANG ĐO...")
        self.audio.speak("Vui lòng nhìn thẳng vào camera và giữ nguyên đầu")
        self.update_frame()

    def update_frame(self):
        if not self.controller.is_running:
            # If finished, immediately call finish actions
            if len(self.controller.ear_samples) >= self.controller.calibration_frames:
                # retrieve threshold and show to user briefly
                try:
                    new_threshold = self.controller.finish_calibration(user_id=self.user_id)
                    if isinstance(new_threshold, float):
                        self.lbl_guide.configure(text=f"Hiệu chuẩn xong! Ngưỡng EAR: {new_threshold:.3f}")
                        self.audio.speak("Hiệu chuẩn thành công")
                        # show for 2 seconds then finish
                        self.after(2000, self.finish)
                        return
                except Exception:
                    pass
                self.finish()
            return
        
        frame, progress = self.controller.process_frame()
        self.progress_bar.set(progress)
        
        if frame is not None:
            # --- VISUAL FEEDBACK: Loading Circle ---
            h, w = frame.shape[:2]
            center = (w // 2, h // 2)
            radius = 120
            thickness = 6
            
            # Draw static background circle (dimmed)
            cv2.circle(frame, center, radius, (50, 50, 50), thickness, cv2.LINE_AA)
            
            # Draw animated progress arc
            # Angle: -90 (top) to 270 (full circle)
            start_angle = -90
            end_angle = start_angle + (360 * progress)
            
            # Color transition: Blue -> Cyan -> Green
            color = (255, 0, 0) # Blue
            if progress > 0.5: color = (255, 255, 0) # Cyan
            if progress > 0.8: color = (0, 255, 0)   # Green
            
            cv2.ellipse(frame, center, (radius, radius), 0, start_angle, end_angle, color, thickness, cv2.LINE_AA)
            
            # Draw percentage text in center
            text = f"{int(progress*100)}%"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
            cv2.putText(frame, text, (center[0] - tw//2, center[1] + th//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            # Chuyển đổi ảnh cho tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            self._imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.camera_frame.configure(image=self._imgtk)

        # --- VOICE GUIDANCE ---
        # Milestones: 0.2 (20%), 0.5 (50%), 0.8 (80%)
        current_milestone = int(progress * 10) # 0 to 10
        
        if current_milestone > self._last_speech_milestone:
            if current_milestone == 2: # 20%
                 self.audio.speak("Đang xác định mắt")
            elif current_milestone == 5: # 50%
                 self.audio.speak("Giữ nguyên đầu")
            elif current_milestone == 8: # 80%
                 self.audio.speak("Sắp hoàn tất")
            
            self._last_speech_milestone = current_milestone

        # Update guidance text based on progress
        if progress < 0.25:
            self.lbl_guide.configure(text="Hãy nhìn thẳng vào camera\nGiữ cố định mặt của bạn")
        elif progress < 0.6:
            self.lbl_guide.configure(text="Bình thường... giữ yên — hệ thống đang đo")
        else:
            self.lbl_guide.configure(text="Gần xong... Nháy mắt nhẹ nếu được yêu cầu")

        if progress >= 1.0:
            self.finish()
        else:
            self.after(30, self.update_frame) # Loop 30ms
            
    def finish(self):
        self.controller.stop_camera()
        # Lưu settings cho user được cung cấp
        try:
            # Ensure settings saved (finish_calibration returns threshold)
            self.controller.finish_calibration(user_id=self.user_id)
        except Exception:
            pass
        self.on_finish() # Chuyển màn hình
