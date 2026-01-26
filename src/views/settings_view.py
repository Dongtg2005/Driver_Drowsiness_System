"""
======================================================
⚙️ Settings View (SQLAlchemy Version)
Driver Drowsiness Detection System
Settings configuration screen
======================================================
"""

import customtkinter as ctk
from typing import Callable, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.change_password_dialog import ChangePasswordDialog # [NEW]
from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame,
    MessageBox
)
from src.utils.toast_notification import ToastContainer
from src.controllers.settings_controller import settings_controller
from src.utils.audio_manager import audio_manager
from src.models.user_model import User

# ...

class SettingsView(ctk.CTkFrame):
    """Settings configuration view"""
    
    def __init__(self, master, user: Optional[User] = None,
                 on_back: Optional[Callable] = None,
                 on_account: Optional[Callable] = None,
                 on_logout: Optional[Callable] = None):
        """
        Create settings view.
        
        Args:
            master: Parent widget
            user: The logged-in User object
            on_back: Callback to go back
            on_account: Callback to open account view
            on_logout: Callback to logout (after password change)
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.toast_container = ToastContainer(self.winfo_toplevel())
        
        self.user = user
        self.on_back = on_back
        self.on_account = on_account
        self.on_logout = on_logout
        
        # Set user in settings controller
        if self.user:
            settings_controller.set_user(self.user.id)
        
        self._create_widgets()
        self.after(100, self._load_settings) # Load settings after UI is drawn
    
    def _create_widgets(self):
        """Create all widgets"""
        self._create_header()
        
        main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._create_detection_section(main_frame)
        self._create_alert_section(main_frame)
        self._create_preset_section(main_frame)
        self._create_account_section(main_frame)
        self._create_action_buttons(main_frame)
    
    def _create_header(self):
        """Create header bar"""
        header = StyledFrame(self, style="card")
        header.pack(fill="x", padx=10, pady=10)
        
        StyledButton(
            header, text="← Quay lại", command=self.on_back,
            style="secondary", width=100, height=35
        ).pack(side="left", padx=10)
        
        StyledLabel(header, text="⚙️ Cài đặt", style="title", size=18).pack(side="left", padx=20)
    
    def _create_detection_section(self, parent):
        """Create detection settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)

        StyledLabel(section, text="👁️ Cài đặt phát hiện", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        StyledLabel(section, text="Điều chỉnh ngưỡng phát hiện buồn ngủ", style="muted", size=12).pack(anchor="w", padx=20, pady=(0, 15))
        
        # EAR Threshold
        self.ear_slider, self.ear_value_label = self._create_slider(
            section, "Ngưỡng EAR (Mắt)", "Giá trị thấp = nhạy hơn (0.15 - 0.40)",
            0.15, 0.40, 25, "{:.2f}"
        )

        # MAR Threshold
        self.mar_slider, self.mar_value_label = self._create_slider(
            section, "Ngưỡng MAR (Miệng)", "Giá trị cao = ít nhạy hơn (0.50 - 1.00)",
            0.50, 1.00, 50, "{:.2f}"
        )

        # Head Threshold
        self.head_slider, self.head_value_label = self._create_slider(
            section, "Ngưỡng góc đầu (độ)", "Góc cúi đầu tối đa cho phép (15° - 60°)",
            15, 60, 45, "{:.0f}°"
        )

    def _create_slider(self, parent, title, subtitle, from_, to, steps, format_str):
        """Helper to create a slider widget."""
        frame = StyledFrame(parent, style="transparent")
        frame.pack(fill="x", padx=20, pady=10)
        StyledLabel(frame, text=title, style="normal").pack(anchor="w")
        StyledLabel(frame, text=subtitle, style="muted", size=11).pack(anchor="w")
        
        slider = ctk.CTkSlider(frame, from_=from_, to=to, number_of_steps=steps)
        slider.pack(fill="x", pady=5)
        
        value_label = StyledLabel(frame, text=format_str.format(slider.get()), style="normal")
        value_label.pack(anchor="e")
        
        slider.configure(command=lambda v: value_label.configure(text=format_str.format(v)))
        return slider, value_label

    def _create_alert_section(self, parent):
        """Create alert settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)

        StyledLabel(section, text="🔊 Cài đặt cảnh báo", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.sound_switch = ctk.CTkSwitch(
            section, text="Bật âm thanh cảnh báo", progress_color=Colors.SUCCESS,
            fg_color=Colors.TEXT_MUTED, button_color=Colors.BG_DARK,
            button_hover_color=Colors.BG_INPUT
        )
        self.sound_switch.pack(anchor="w", padx=20, pady=10)
        
        # [NEW] Sunglasses Mode Switch
        self.sunglasses_switch = ctk.CTkSwitch(
            section, text="Chế độ Kính râm (Giảm độ nhạy mắt)", progress_color=Colors.WARNING,
            fg_color=Colors.TEXT_MUTED, button_color=Colors.BG_DARK,
            button_hover_color=Colors.BG_INPUT
        )
        self.sunglasses_switch.pack(anchor="w", padx=20, pady=10)
        
        self.volume_slider, self.volume_value_label = self._create_slider(
            section, "Âm lượng cảnh báo", "", 0, 1, 10, "{:.0%}"
        )

        StyledButton(
            section, text="🔔 Test âm thanh", command=lambda: audio_manager.play_beep(),
            style="info", width=150
        ).pack(anchor="w", padx=20, pady=(5, 20))
    
    def _create_preset_section(self, parent):
        """Create sensitivity presets section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)

        StyledLabel(section, text="📊 Mức độ nhạy", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        StyledLabel(section, text="Chọn preset hoặc tự điều chỉnh ở trên", style="muted", size=12).pack(anchor="w", padx=20, pady=(0, 15))
        
        preset_frame = StyledFrame(section, style="transparent")
        preset_frame.pack(fill="x", padx=20, pady=(0, 20))

        StyledButton(preset_frame, text="🟢 Thấp", command=lambda: self._apply_preset("LOW"), style="success", width=100).pack(side="left", padx=5)
        StyledButton(preset_frame, text="🟡 Trung bình", command=lambda: self._apply_preset("MEDIUM"), style="warning", width=120).pack(side="left", padx=5)
        StyledButton(preset_frame, text="🔴 Cao", command=lambda: self._apply_preset("HIGH"), style="danger", width=100).pack(side="left", padx=5)
        
        self.preset_label = StyledLabel(section, text="Hiện tại: ", style="muted", size=12)
        self.preset_label.pack(anchor="w", padx=20, pady=(0, 15))
    
    def _create_account_section(self, parent):
        """Create account settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)
        
        StyledLabel(section, text="👤 Tài khoản", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        
        if self.user:
            info_frame = StyledFrame(section, style="transparent")
            info_frame.pack(fill="x", padx=20, pady=10)
            StyledLabel(info_frame, text=f"Username: {self.user.username}", style="normal").pack(anchor="w")
            StyledLabel(info_frame, text=f"Email: {self.user.email or 'Chưa cập nhật'}", style="muted").pack(anchor="w")
        
        if self.on_account:
            StyledButton(
                section, text="✏️ Chỉnh sửa thông tin", command=self.on_account,
                style="info", width=150
            ).pack(anchor="w", padx=20, pady=(10, 5))

        StyledButton(
            section, text="🔒 Đổi mật khẩu", command=self._show_change_password,
            style="secondary", width=150
        ).pack(anchor="w", padx=20, pady=(5, 20))
    
    def _create_action_buttons(self, parent):
        """Create save and reset buttons"""
        btn_frame = StyledFrame(parent, style="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)
        
        StyledButton(btn_frame, text="💾 Lưu cài đặt", command=self._save_settings, style="success", width=150).pack(side="left", padx=5)
        StyledButton(btn_frame, text="🔄 Khôi phục mặc định", command=self._reset_defaults, style="secondary", width=180).pack(side="left", padx=5)
    
    def _load_settings(self):
        """Load current settings from the controller and update the UI."""
        settings = settings_controller.get_settings()

        self.ear_slider.set(settings.get('ear_threshold', 0.25))
        self.mar_slider.set(settings.get('mar_threshold', 0.70))
        self.head_slider.set(settings.get('head_threshold', 30.0))
        self.volume_slider.set(settings.get('alert_volume', 0.8))
        
        self.ear_value_label.configure(text=f"{self.ear_slider.get():.2f}")
        self.mar_value_label.configure(text=f"{self.mar_slider.get():.2f}")
        self.head_value_label.configure(text=f"{self.head_slider.get():.0f}°")
        self.volume_value_label.configure(text=f"{self.volume_slider.get():.0%}")
        
        if settings.get('enable_sound', True):
            self.sound_switch.select()
        else:
            self.sound_switch.deselect()
        
        # [NEW] Load sunglasses mode
        if settings.get('sunglasses_mode', False):
            self.sunglasses_switch.select()
        else:
            self.sunglasses_switch.deselect()
        
        preset_names = {'LOW': 'Thấp', 'MEDIUM': 'Trung bình', 'HIGH': 'Cao'}
        sensitivity = settings.get('sensitivity_level', 'MEDIUM')
        self.preset_label.configure(text=f"Hiện tại: {preset_names.get(sensitivity, 'Tùy chỉnh')}")
    
    def _apply_preset(self, level: str):
        """Apply a sensitivity preset."""
        success, message = settings_controller.set_sensitivity_level(level)
        if success:
            self._load_settings()
            self.toast_container.show_toast(f"Đã áp dụng mức độ: {level}", "success", position="top-center")
        else:
            MessageBox.show_error(self, "Lỗi", message)
    
    def _save_settings(self):
        """Save current settings from the UI to the database."""
        settings_data = {
            'ear_threshold': self.ear_slider.get(),
            'mar_threshold': self.mar_slider.get(),
            'head_threshold': self.head_slider.get(),
            'alert_volume': self.volume_slider.get(),
            'enable_sound': bool(self.sound_switch.get()),
            'sunglasses_mode': bool(self.sunglasses_switch.get())  # [NEW]
        }
        success, message = settings_controller.update_settings(**settings_data)
        
        if success:
            self.toast_container.show_toast(message, "success", position="top-center")
        else:
            MessageBox.show_error(self, "Lỗi", message)
    
    def _reset_defaults(self):
        """Reset settings to their default values."""
        if MessageBox.ask_yes_no(self, "Xác nhận", "Bạn có chắc muốn khôi phục cài đặt mặc định?"):
            success, message = settings_controller.reset_to_defaults()
            if success:
                self._load_settings()
                self.toast_container.show_toast("Đã khôi phục cài đặt mặc định!", "success", position="top-center")
            else:
                MessageBox.show_error(self, "Lỗi", message)
    
    def _show_change_password(self):
        """Show change password dialog."""
        ChangePasswordDialog(self, on_success=self.on_logout)

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Settings Test")
    root.geometry("800x700")
    
    test_user = User(id=1, username='test_user', email='test@example.com')
    view = SettingsView(root, user=test_user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
