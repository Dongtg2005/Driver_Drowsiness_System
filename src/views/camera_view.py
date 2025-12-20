"""
============================================
📹 Camera View
Driver Drowsiness Detection System
Main monitoring screen with camera feed
============================================
"""

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
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
from src.controllers.monitor_controller import MonitorController


class CameraView(ctk.CTkFrame):
    """Main camera monitoring view"""
    
    def __init__(self, master, user_data: dict = None,
                 on_dashboard: Callable = None,
                 on_settings: Callable = None,
                 on_logout: Callable = None):
        """
        Create camera monitoring view.
        
        Args:
            master: Parent widget
            user_data: Logged in user data
            on_dashboard: Callback to open dashboard
            on_settings: Callback to open settings
            on_logout: Callback to logout
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user_data = user_data
        self.on_dashboard = on_dashboard
        self.on_settings = on_settings
        self.on_logout = on_logout
        
        # Camera state
        self.is_running = False
        self.cap = None
        self.current_frame = None
        
        # Monitor controller
        self.monitor = MonitorController(
            user_id=user_data.get('id') if user_data else None
        )
        
        # Alert state
        self.alert_count = 0
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all widgets"""
        # Navigation bar
        self._create_navbar()
        
        # Main content area
        main_frame = StyledFrame(self, style="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left: Camera panel
        self._create_camera_panel(main_frame)
        
        # Right: Info panel
        self._create_info_panel(main_frame)
    
    def _create_navbar(self):
        """Create navigation bar"""
        navbar = StyledFrame(self, style="card")
        navbar.pack(fill="x", padx=10, pady=10)
        
        # Logo/Title
        StyledLabel(
            navbar,
            text="🚗 Driver Drowsiness Detection",
            style="title",
            size=16
        ).pack(side="left", padx=15)
        
        # User info
        if self.user_data:
            username = self.user_data.get('username', 'User')
            StyledLabel(
                navbar,
                text=f"👤 {username}",
                style="normal"
            ).pack(side="left", padx=20)
        
        # Navigation buttons
        btn_frame = StyledFrame(navbar, style="transparent")
        btn_frame.pack(side="right", padx=10)
        
        StyledButton(
            btn_frame,
            text="📊 Dashboard",
            command=self._on_dashboard_click,
            style="info",
            width=110
        ).pack(side="left", padx=5)
        
        StyledButton(
            btn_frame,
            text="⚙️ Cài đặt",
            command=self._on_settings_click,
            style="secondary",
            width=100
        ).pack(side="left", padx=5)
        
        StyledButton(
            btn_frame,
            text="🚪 Đăng xuất",
            command=self._on_logout_click,
            style="danger",
            width=110
        ).pack(side="left", padx=5)
    
    def _create_camera_panel(self, parent):
        """Create camera display panel"""
        camera_frame = StyledFrame(parent, style="card")
        camera_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Camera title
        StyledLabel(
            camera_frame,
            text="📹 Camera Feed",
            style="title",
            size=14
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Camera display
        self.camera_label = ctk.CTkLabel(
            camera_frame,
            text="Camera không hoạt động\nNhấn 'Bắt đầu' để khởi động",
            width=640,
            height=480,
            fg_color=Colors.BG_INPUT,
            corner_radius=10
        )
        self.camera_label.pack(padx=15, pady=10)
        
        # Control buttons
        control_frame = StyledFrame(camera_frame, style="transparent")
        control_frame.pack(fill="x", padx=15, pady=10)
        
        self.start_btn = StyledButton(
            control_frame,
            text="▶️ Bắt đầu",
            command=self._start_monitoring,
            style="success",
            width=120
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = StyledButton(
            control_frame,
            text="⏹️ Dừng",
            command=self._stop_monitoring,
            style="danger",
            width=100
        )
        self.stop_btn.pack(side="left", padx=5)
        self.stop_btn.configure(state="disabled")
        
        # Status label
        self.status_label = StyledLabel(
            control_frame,
            text="⚪ Sẵn sàng",
            style="muted"
        )
        self.status_label.pack(side="right", padx=10)
    
    def _create_info_panel(self, parent):
        """Create information panel"""
        info_frame = StyledFrame(parent, style="card")
        info_frame.pack(side="right", fill="y", ipadx=20)
        
        # Title
        StyledLabel(
            info_frame,
            text="📊 Thông số",
            style="title",
            size=14
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Metrics
        metrics_frame = StyledFrame(info_frame, style="transparent")
        metrics_frame.pack(fill="x", padx=15, pady=5)
        
        # EAR
        self.ear_label = self._create_metric_row(metrics_frame, "EAR (Mắt)", "--")
        
        # MAR
        self.mar_label = self._create_metric_row(metrics_frame, "MAR (Miệng)", "--")
        
        # Head Pitch
        self.pitch_label = self._create_metric_row(metrics_frame, "Góc cúi đầu", "--")
        
        # Head Yaw
        self.yaw_label = self._create_metric_row(metrics_frame, "Góc quay đầu", "--")
        
        # Separator
        sep = ctk.CTkFrame(info_frame, height=2, fg_color=Colors.BG_INPUT)
        sep.pack(fill="x", padx=15, pady=15)
        
        # Alert status
        StyledLabel(
            info_frame,
            text="🚨 Trạng thái cảnh báo",
            style="title",
            size=14
        ).pack(anchor="w", padx=15, pady=(5, 10))
        
        self.alert_status_label = StyledLabel(
            info_frame,
            text="✅ Bình thường",
            style="normal",
            size=16
        )
        self.alert_status_label.pack(anchor="w", padx=15, pady=5)
        self.alert_status_label.configure(text_color=Colors.SUCCESS)
        
        # Alert counter
        alert_count_frame = StyledFrame(info_frame, style="bordered")
        alert_count_frame.pack(fill="x", padx=15, pady=10)
        
        StyledLabel(
            alert_count_frame,
            text="Số cảnh báo hôm nay:",
            style="muted",
            size=12
        ).pack(anchor="w", padx=10, pady=(10, 0))
        
        self.alert_count_label = StyledLabel(
            alert_count_frame,
            text="0",
            style="title",
            size=32
        )
        self.alert_count_label.pack(anchor="w", padx=10, pady=(5, 10))
        
        # Session info
        sep2 = ctk.CTkFrame(info_frame, height=2, fg_color=Colors.BG_INPUT)
        sep2.pack(fill="x", padx=15, pady=15)
        
        StyledLabel(
            info_frame,
            text="⏱️ Phiên làm việc",
            style="title",
            size=14
        ).pack(anchor="w", padx=15, pady=(5, 10))
        
        self.session_time_label = StyledLabel(
            info_frame,
            text="00:00:00",
            style="normal",
            size=18
        )
        self.session_time_label.pack(anchor="w", padx=15, pady=5)
    
    def _create_metric_row(self, parent, label: str, value: str) -> StyledLabel:
        """Create a metric display row"""
        row = StyledFrame(parent, style="transparent")
        row.pack(fill="x", pady=5)
        
        StyledLabel(row, text=label, style="muted", size=12).pack(anchor="w")
        value_label = StyledLabel(row, text=value, style="normal", size=16)
        value_label.pack(anchor="w")
        
        return value_label
    
    def _start_monitoring(self):
        """Start camera monitoring"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                MessageBox.show_error(self, "Lỗi", "Không thể mở camera!")
                return
            
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_label.configure(text="🟢 Đang giám sát")
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            # Start session timer
            self.session_start_time = time.time()
            self._update_session_timer()
            
        except Exception as e:
            MessageBox.show_error(self, "Lỗi", f"Lỗi khởi động camera: {e}")
    
    def _stop_monitoring(self):
        """Stop camera monitoring"""
        self.is_running = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="⚪ Đã dừng")
        
        # Reset display
        self.camera_label.configure(
            image=None,
            text="Camera đã dừng\nNhấn 'Bắt đầu' để khởi động lại"
        )
        
        # Stop audio alerts
        self.monitor.stop_alert()
    
    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread"""
        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Process frame through monitor controller
            result = self.monitor.process_external_frame(frame)
            
            # Update UI (must be done in main thread)
            self.after(0, lambda r=result: self._update_ui(r))
            
            # Small delay for frame rate control
            time.sleep(0.03)  # ~30 FPS
    
    def _update_ui(self, result: dict):
        """Update UI with monitoring results"""
        if not self.is_running:
            return
        
        # Update camera display
        frame = result.get('frame')
        if frame is not None:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize for display
            frame_rgb = cv2.resize(frame_rgb, (640, 480))
            
            # Convert to PhotoImage
            img = Image.fromarray(frame_rgb)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo  # Keep reference
        
        # Update metrics
        ear = result.get('ear', 0)
        mar = result.get('mar', 0)
        pitch = result.get('pitch', 0)
        yaw = result.get('yaw', 0)
        
        self.ear_label.configure(text=f"{ear:.3f}")
        self.mar_label.configure(text=f"{mar:.3f}")
        self.pitch_label.configure(text=f"{pitch:.1f}°")
        self.yaw_label.configure(text=f"{yaw:.1f}°")
        
        # Update alert status
        alert_level = result.get('alert_level', 0)
        alert_type = result.get('alert_type', None)
        
        if alert_level == 0:
            self.alert_status_label.configure(
                text="✅ Bình thường",
                text_color=Colors.SUCCESS
            )
        elif alert_level == 1:
            self.alert_status_label.configure(
                text="⚠️ Cảnh báo nhẹ",
                text_color=Colors.WARNING
            )
        elif alert_level >= 2:
            alert_text = "🚨 NGUY HIỂM!"
            if alert_type:
                alert_names = {
                    'DROWSY': 'Buồn ngủ',
                    'YAWN': 'Ngáp',
                    'HEAD_DOWN': 'Cúi đầu'
                }
                alert_text = f"🚨 {alert_names.get(alert_type, alert_type)}"
            
            self.alert_status_label.configure(
                text=alert_text,
                text_color=Colors.DANGER
            )
        
        # Update alert count
        if result.get('alert_triggered', False):
            self.alert_count += 1
            self.alert_count_label.configure(text=str(self.alert_count))
    
    def _update_session_timer(self):
        """Update session timer display"""
        if not self.is_running:
            return
        
        elapsed = int(time.time() - self.session_start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        
        self.session_time_label.configure(
            text=f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        
        # Schedule next update
        self.after(1000, self._update_session_timer)
    
    def _on_dashboard_click(self):
        """Handle dashboard button click"""
        if self.is_running:
            self._stop_monitoring()
        
        if self.on_dashboard:
            self.on_dashboard()
    
    def _on_settings_click(self):
        """Handle settings button click"""
        if self.is_running:
            self._stop_monitoring()
        
        if self.on_settings:
            self.on_settings()
    
    def _on_logout_click(self):
        """Handle logout button click"""
        if MessageBox.ask_yes_no(self, "Xác nhận", "Bạn có chắc muốn đăng xuất?"):
            if self.is_running:
                self._stop_monitoring()
            
            if self.on_logout:
                self.on_logout()
    
    def destroy(self):
        """Clean up resources"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        super().destroy()


if __name__ == "__main__":
    # Test camera view
    root = ctk.CTk()
    root.title("Camera View Test")
    root.geometry("1280x720")
    
    user = {'id': 1, 'username': 'test_user'}
    view = CameraView(root, user_data=user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
