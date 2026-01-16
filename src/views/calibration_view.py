import customtkinter as ctk
import cv2
from PIL import Image
from src.controllers.calibration_controller import CalibrationController

class CalibrationView(ctk.CTkFrame):
    def __init__(self, master, on_finish, user_id: int = 1):
        super().__init__(master)
        self.on_finish = on_finish
        self.user_id = user_id
        self.controller = CalibrationController()
        self._imgtk = None
        
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
        self.update_frame()

    def update_frame(self):
        if not self.controller.is_running:
            # If finished, immediately call finish actions
            if len(self.controller.ear_samples) >= self.controller.calibration_frames:
                self.finish()
            return
        
        frame, progress = self.controller.process_frame()
        self.progress_bar.set(progress)
        
        if frame is not None:
            # Chuyển đổi ảnh cho tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            self._imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            self.camera_frame.configure(image=self._imgtk)
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
            self.controller.finish_calibration(user_id=self.user_id)
        except Exception:
            pass
        self.on_finish() # Chuyển màn hình
