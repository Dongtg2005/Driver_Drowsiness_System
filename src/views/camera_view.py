"""
======================================================
📹 Camera View (SQLAlchemy Version)
Driver Drowsiness Detection System
Main monitoring screen with camera feed
======================================================
"""

import customtkinter as ctk
import cv2
from PIL import Image
import threading
import time
from typing import Callable, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame, MessageBox
)
from src.utils.toast_notification import ToastContainer
from config import config
from src.controllers.monitor_controller import MonitorController
from src.models.user_model import User # Import the User model for type hinting

class CameraView(ctk.CTkFrame):
    """Main camera monitoring view"""
    
    def __init__(self, master, user: Optional[User] = None,
                 on_dashboard: Optional[Callable] = None,
                 on_settings: Optional[Callable] = None,
                 on_logout: Optional[Callable] = None):
        """
        Create camera monitoring view.
        
        Args:
            master: Parent widget
            user: The logged-in User object
            on_dashboard: Callback to open dashboard
            on_settings: Callback to open settings
            on_logout: Callback to logout
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user = user
        self.on_dashboard = on_dashboard
        self.on_settings = on_settings
        self.on_logout = on_logout
        
        # Camera state
        self.is_running = False
        self.cap = None
        self.current_frame = None
        
        # Monitor controller - now uses user.id directly
        self.monitor = MonitorController(
            user_id=self.user.id if self.user else None
        )
        
        # Alert state
        self.alert_count = 0
        self._is_alert_active = False
        
        self._create_widgets()
        # Toast container để hiển thị thông báo ngoài khung camera
        self.toast_container = ToastContainer(self.winfo_toplevel())
        self._last_toast_time = 0
    
    def _create_widgets(self):
        """Create all widgets"""
        self._create_navbar()
        main_frame = StyledFrame(self, style="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self._create_camera_panel(main_frame)
        self._create_info_panel(main_frame)
    
    def _create_navbar(self):
        """Create navigation bar"""
        navbar = StyledFrame(self, style="card")
        navbar.pack(fill="x", padx=10, pady=10)
        
        StyledLabel(
            navbar,
            text="🚗 Driver Drowsiness Detection",
            style="title",
            size=16
        ).pack(side="left", padx=15)
        
        # User info - now uses user.username directly
        if self.user:
            StyledLabel(
                navbar,
                text=f"👤 {self.user.username}",
                style="normal"
            ).pack(side="left", padx=20)
        
        btn_frame = StyledFrame(navbar, style="transparent")
        btn_frame.pack(side="right", padx=10)
        
        StyledButton(
            btn_frame, text="📊 Dashboard", command=self._on_dashboard_click,
            style="info", width=110
        ).pack(side="left", padx=5)
        
        StyledButton(
            btn_frame, text="⚙️ Cài đặt", command=self._on_settings_click,
            style="secondary", width=100
        ).pack(side="left", padx=5)
        
        StyledButton(
            btn_frame, text="🚪 Đăng xuất", command=self._on_logout_click,
            style="danger", width=110
        ).pack(side="left", padx=5)
    
    def _create_camera_panel(self, parent):
        """Create camera display panel"""
        camera_frame = StyledFrame(parent, style="card")
        camera_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        StyledLabel(
            camera_frame, text="📹 Camera Feed", style="title", size=14
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Banner cảnh báo (Nằm trên camera)
        self.alert_banner = ctk.CTkLabel(
            camera_frame, 
            text="", 
            height=0,
            width=640, # Kích thước ngang bằng khung camera
            fg_color="transparent",
            text_color=Colors.TEXT_WHITE,
            font=("Roboto", 16, "bold"),
            corner_radius=5
        )
        self.alert_banner.pack(padx=15, pady=(0, 5))
        
        self.camera_label = ctk.CTkLabel(
            camera_frame, text="Camera không hoạt động\nNhấn 'Bắt đầu' để khởi động",
            width=640, height=480, fg_color=Colors.BG_INPUT, corner_radius=10
        )
        self.camera_label.pack(padx=15, pady=10)
        
        control_frame = StyledFrame(camera_frame, style="transparent")
        control_frame.pack(fill="x", padx=15, pady=10)
        
        self.start_btn = StyledButton(
            control_frame, text="▶️ Bắt đầu", command=self._start_monitoring,
            style="success", width=120
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = StyledButton(
            control_frame, text="⏹️ Dừng", command=self._stop_monitoring,
            style="danger", width=100, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.status_label = StyledLabel(
            control_frame, text="⚪ Sẵn sàng", style="muted"
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_info_panel(self, parent):
        """Create information panel"""
        info_frame = StyledFrame(parent, style="card")
        info_frame.pack(side="right", fill="y", ipadx=20)
        
        StyledLabel(
            info_frame, text="📊 Thông số", style="title", size=14
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        metrics_frame = StyledFrame(info_frame, style="transparent")
        metrics_frame.pack(fill="x", padx=15, pady=5)
        
        self.ear_label = self._create_metric_row(metrics_frame, "EAR (Mắt)", "--")
        self.mar_label = self._create_metric_row(metrics_frame, "MAR (Miệng)", "--")
        self.pitch_label = self._create_metric_row(metrics_frame, "Góc cúi đầu", "--")
        self.yaw_label = self._create_metric_row(metrics_frame, "Góc quay đầu", "--")
        
        sep = ctk.CTkFrame(info_frame, height=2, fg_color=Colors.BG_INPUT)
        sep.pack(fill="x", padx=15, pady=15)
        
        StyledLabel(
            info_frame, text="🚨 Trạng thái cảnh báo", style="title", size=14
        ).pack(anchor="w", padx=15, pady=(5, 10))
        
        self.alert_status_label = StyledLabel(
            info_frame, text="✅ Bình thường", style="normal", size=16, text_color=Colors.SUCCESS
        )
        self.alert_status_label.pack(anchor="w", padx=15, pady=5)

        alert_count_frame = StyledFrame(info_frame, style="bordered")
        alert_count_frame.pack(fill="x", padx=15, pady=10)
        
        StyledLabel(
            alert_count_frame, text="Số cảnh báo hôm nay:", style="muted", size=12
        ).pack(anchor="w", padx=10, pady=(10, 0))
        
        self.alert_count_label = StyledLabel(
            alert_count_frame, text="0", style="title", size=32
        )
        self.alert_count_label.pack(anchor="w", padx=10, pady=(5, 10))
        
        sep2 = ctk.CTkFrame(info_frame, height=2, fg_color=Colors.BG_INPUT)
        sep2.pack(fill="x", padx=15, pady=15)
        
        StyledLabel(
            info_frame, text="⏱️ Phiên làm việc", style="title", size=14
        ).pack(anchor="w", padx=15, pady=(5, 10))
        
        self.session_time_label = StyledLabel(
            info_frame, text="00:00:00", style="normal", size=18
        )
        self.session_time_label.pack(anchor="w", padx=15, pady=5)
    
    def _create_metric_row(self, parent, label: str, value: str) -> StyledLabel:
        """Helper to create a metric display row"""
        row = StyledFrame(parent, style="transparent")
        row.pack(fill="x", pady=5)
        StyledLabel(row, text=label, style="muted", size=12).pack(anchor="w")
        value_label = StyledLabel(row, text=value, style="normal", size=16)
        value_label.pack(anchor="w")
        return value_label
    
    def _start_monitoring(self):
        """Start camera monitoring thread with retry logic"""
        def _open_camera():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Try DirectShow for faster init on Windows
                    if not cap.isOpened():
                         # Fallback if CAP_DSHOW fails or not supported
                         cap = cv2.VideoCapture(0)
                    
                    if cap.isOpened():
                        return cap
                    print(f"⚠️ Camera init failed (Attempt {attempt+1}/{max_retries}). Retrying...")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Camera error: {e}")
                    time.sleep(1)
            return None

        try:
            # Ensure previous instance is closed
            if self.cap:
                self.cap.release()
            
            self.start_btn.configure(state="disabled", text="Đang mở...")
            self.update_idletasks() # Force UI update
            
            # Run camera acquisition in a separate thread to avoid freezing UI
            # But here we need cap before starting the loop. 
            # Ideally monitor_thread should handle opening. 
            # For now, let's keep it simple but with retries.
            
            self.cap = _open_camera()
            
            if not self.cap or not self.cap.isOpened():
                self.start_btn.configure(state="normal", text="▶️ Bắt đầu")
                MessageBox.show_error(self, "Lỗi", "Không thể kết nối Camera sau nhiều lần thử!\nHãy kiểm tra lại kết nối.")
                return
            
            self.is_running = True
            self.monitor.start_monitoring(spawn_camera=False)  # Start the detection logic and session (Camera handled here)
            self.start_btn.configure(state="disabled", text="▶️ Bắt đầu")
            self.stop_btn.configure(state="normal")
            self.status_label.configure(text="🟢 Đang giám sát")
            
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            self.session_start_time = time.time()
            self._update_session_timer()
            
        except Exception as e:
            self.start_btn.configure(state="normal", text="▶️ Bắt đầu")
            MessageBox.show_error(self, "Lỗi", f"Lỗi khởi động camera: {e}")
    
    def _stop_monitoring(self, update_ui=True):
        """Stop camera monitoring"""
        # Tránh gọi nhiều lần
        if not self.is_running and self.cap is None:
            return
            
        self.is_running = False
        self.monitor.stop_monitoring()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if update_ui:
            try:
                # Kiểm tra widget còn tồn tại không trước khi configure
                if self.winfo_exists():
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.status_label.configure(text="⚪ Đã dừng")
                    # Xóa ảnh an toàn
                    self.camera_label.configure(image=None, text="Camera đã dừng")
            except Exception:
                pass
                
        self.monitor.stop_alert()
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.is_running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                
                result = self.monitor.process_external_frame(frame)
                
                # Check if thread should stop
                if not self.is_running:
                    break
                    
                self.after(0, lambda r=result: self._update_ui(r))
                time.sleep(0.03)
        except Exception as e:
            print(f"❌ Camera thread crashed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._stop_monitoring()
    
    def _update_ui(self, result: dict):
        """Update UI with monitoring results from the controller"""
        # CỰC KỲ QUAN TRỌNG: Kiểm tra winfo_exists để tránh TclError khi chuyển view
        try:
            if not self.winfo_exists() or not self.is_running or result is None:
                return
            
            frame = result.get('frame')
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
                self.camera_label.configure(image=photo, text="")
                self.camera_label._image = photo # Keep reference to prevent GC

            self.ear_label.configure(text=f"{result.get('ear', 0):.3f}")
            self.mar_label.configure(text=f"{result.get('mar', 0):.3f}")
            self.pitch_label.configure(text=f"{result.get('pitch', 0):.1f}°")
            self.yaw_label.configure(text=f"{result.get('yaw', 0):.1f}°")
            
            alert_level = result.get('alert_level', 0)
            
            # CẬP NHẬT BANNER CẢNH BÁO (Nằm ngay trên Camera)
            sunglasses = result.get('sunglasses', False)
            
            if sunglasses:
                # Ưu tiên hiển thị cảnh báo kính râm
                self.alert_banner.configure(
                    text="PHÁT HIỆN KÍNH RÂM - Chế độ giám sát hành vi", 
                    height=40, 
                    fg_color=(255, 140, 0)  # Orange
                )
            elif alert_level > 0:
                msg = result.get('alert_message') or ("⚠️ CẢNH BÁO" if alert_level == 1 else "🚨 NGUY HIỂM")
                bg_color = Colors.WARNING if alert_level == 1 else Colors.DANGER
                self.alert_banner.configure(text=msg, height=40, fg_color=bg_color)
            else:
                self.alert_banner.configure(text="", height=0, fg_color="transparent")

            if alert_level == 0:
                self.alert_status_label.configure(text="✅ Bình thường", text_color=Colors.SUCCESS)
            elif alert_level == 1:
                self.alert_status_label.configure(text="⚠️ Cảnh báo nhẹ", text_color=Colors.WARNING)
            else:
                alert_type = result.get('alert_type', 'NGUY HIỂM')
                alert_names = {'DROWSY': 'Buồn ngủ', 'YAWN': 'Ngáp', 'HEAD_DOWN': 'Cúi đầu'}
                self.alert_status_label.configure(text=f"🚨 {alert_names.get(alert_type, alert_type)}", text_color=Colors.DANGER)
            
            # Hiển thị toast ngoài khung camera (chỉ khi tắt Overlay trên frame)
            is_triggered = result.get('alert_triggered', False)
            
            # [FIXED] Chỉ đếm 1 lần cho mỗi đợt cảnh báo (Rising Edge Detection)
            if is_triggered:
                if not self._is_alert_active:
                    self.alert_count += 1
                    self.alert_count_label.configure(text=str(self.alert_count))
                    self._is_alert_active = True
            else:
                self._is_alert_active = False

            if is_triggered:
                
                # Toast VẪN GIỮ làm kệnh phụ trợ, nhưng banner đã làm việc chính
                if not config.SHOW_ALERT_OVERLAY_ON_FRAME:
                    # Chống spam toast
                    now = time.time()
                    # ... (Logic Toast cũ) ...
                    if now - self._last_toast_time > 5:
                        msg = result.get('alert_message') or ("⚠️ Cảnh báo nhẹ" if alert_level == 1 else "🚨 Nguy hiểm")
                        style = "warning" if alert_level == 1 else "danger"
                        # Đặt ở "top-right"
                        self.toast_container.show_toast(message=msg, notification_type=style, position="top-right")
                        self._last_toast_time = now
        except Exception as e:
            # Bỏ qua lỗi UI khi widget đang bị hủy hoặc ảnh bị xóa
            # "image ... doesn't exist" là lỗi TclError phổ biến khi update ảnh trên widget đang hủy
            if "doesn't exist" in str(e) or "invalid command name" in str(e):
                pass
            else:
                print(f"❌ UI Update Error: {e}")
            pass
    
    def _update_session_timer(self):
        """Update session timer display every second"""
        try:
            if not self.winfo_exists() or not self.is_running:
                return
            elapsed = int(time.time() - self.session_start_time)
            self.session_time_label.configure(text=f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}")
            self.after(1000, self._update_session_timer)
        except Exception:
            pass
    
    def _on_dashboard_click(self):
        if self.on_dashboard: self.on_dashboard()
    
    def _on_settings_click(self):
        if self.on_settings: self.on_settings()
    
    def _on_logout_click(self):
        if MessageBox.ask_yes_no(self, "Xác nhận", "Bạn có chắc muốn đăng xuất?"):
            if self.on_logout: self.on_logout()
    
    def cleanup(self):
        """Clean up resources before destroying the widget"""
        self._stop_monitoring(update_ui=False)

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Camera View Test")
    root.geometry("1280x720")
    
    # Create a dummy User object for testing
    test_user = User(id=1, username='test_user', password='hashed_password')

    view = CameraView(root, user=test_user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()