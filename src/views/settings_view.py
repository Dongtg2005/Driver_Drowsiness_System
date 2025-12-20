"""
============================================
⚙️ Settings View
Driver Drowsiness Detection System
Settings configuration screen
============================================
"""

import customtkinter as ctk
from typing import Callable, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame,
    StyledSlider, StyledSwitch, StyledOptionMenu, MessageBox
)
from src.controllers.settings_controller import settings_controller
from src.utils.audio_manager import audio_manager


class SettingsView(ctk.CTkFrame):
    """Settings configuration view"""
    
    def __init__(self, master, user_data: dict = None,
                 on_back: Callable = None):
        """
        Create settings view.
        
        Args:
            master: Parent widget
            user_data: Logged in user data
            on_back: Callback to go back
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user_data = user_data
        self.on_back = on_back
        
        # Set user in settings controller
        if user_data:
            settings_controller.set_user(user_data.get('id'))
        
        self._create_widgets()
        self._load_settings()
    
    def _create_widgets(self):
        """Create all widgets"""
        # Header
        self._create_header()
        
        # Main content - scrollable
        main_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Detection settings
        self._create_detection_section(main_frame)
        
        # Alert settings
        self._create_alert_section(main_frame)
        
        # Sensitivity presets
        self._create_preset_section(main_frame)
        
        # Account settings
        self._create_account_section(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
    
    def _create_header(self):
        """Create header bar"""
        header = StyledFrame(self, style="card")
        header.pack(fill="x", padx=10, pady=10)
        
        # Back button
        StyledButton(
            header,
            text="← Quay lại",
            command=self._on_back_click,
            style="secondary",
            width=100,
            height=35
        ).pack(side="left", padx=10)
        
        # Title
        StyledLabel(
            header,
            text="⚙️ Cài đặt",
            style="title",
            size=18
        ).pack(side="left", padx=20)
    
    def _create_detection_section(self, parent):
        """Create detection settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)
        
        # Title
        StyledLabel(
            section,
            text="👁️ Cài đặt phát hiện",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        StyledLabel(
            section,
            text="Điều chỉnh ngưỡng phát hiện buồn ngủ",
            style="muted",
            size=12
        ).pack(anchor="w", padx=20, pady=(0, 15))
        
        # EAR Threshold
        ear_frame = StyledFrame(section, style="transparent")
        ear_frame.pack(fill="x", padx=20, pady=10)
        
        StyledLabel(ear_frame, text="Ngưỡng EAR (Mắt)", style="normal").pack(anchor="w")
        StyledLabel(
            ear_frame, 
            text="Giá trị thấp = nhạy hơn (0.15 - 0.40)",
            style="muted",
            size=11
        ).pack(anchor="w")
        
        self.ear_slider = ctk.CTkSlider(
            ear_frame,
            from_=0.15,
            to=0.40,
            number_of_steps=25,
            command=self._on_ear_change,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY
        )
        self.ear_slider.pack(fill="x", pady=5)
        
        self.ear_value_label = StyledLabel(ear_frame, text="0.25", style="normal")
        self.ear_value_label.pack(anchor="e")
        
        # MAR Threshold
        mar_frame = StyledFrame(section, style="transparent")
        mar_frame.pack(fill="x", padx=20, pady=10)
        
        StyledLabel(mar_frame, text="Ngưỡng MAR (Miệng)", style="normal").pack(anchor="w")
        StyledLabel(
            mar_frame,
            text="Giá trị cao = ít nhạy hơn (0.50 - 1.00)",
            style="muted",
            size=11
        ).pack(anchor="w")
        
        self.mar_slider = ctk.CTkSlider(
            mar_frame,
            from_=0.50,
            to=1.00,
            number_of_steps=50,
            command=self._on_mar_change,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY
        )
        self.mar_slider.pack(fill="x", pady=5)
        
        self.mar_value_label = StyledLabel(mar_frame, text="0.70", style="normal")
        self.mar_value_label.pack(anchor="e")
        
        # Head Threshold
        head_frame = StyledFrame(section, style="transparent")
        head_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        StyledLabel(head_frame, text="Ngưỡng góc đầu (độ)", style="normal").pack(anchor="w")
        StyledLabel(
            head_frame,
            text="Góc cúi đầu tối đa cho phép (15° - 60°)",
            style="muted",
            size=11
        ).pack(anchor="w")
        
        self.head_slider = ctk.CTkSlider(
            head_frame,
            from_=15,
            to=60,
            number_of_steps=45,
            command=self._on_head_change,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY
        )
        self.head_slider.pack(fill="x", pady=5)
        
        self.head_value_label = StyledLabel(head_frame, text="30°", style="normal")
        self.head_value_label.pack(anchor="e")
    
    def _create_alert_section(self, parent):
        """Create alert settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)
        
        # Title
        StyledLabel(
            section,
            text="🔊 Cài đặt cảnh báo",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Sound toggle
        sound_frame = StyledFrame(section, style="transparent")
        sound_frame.pack(fill="x", padx=20, pady=10)
        
        self.sound_switch = StyledSwitch(
            sound_frame,
            text="Bật âm thanh cảnh báo",
            command=self._on_sound_toggle,
            default=True
        )
        self.sound_switch.pack(anchor="w")
        
        # Volume
        volume_frame = StyledFrame(section, style="transparent")
        volume_frame.pack(fill="x", padx=20, pady=10)
        
        StyledLabel(volume_frame, text="Âm lượng cảnh báo", style="normal").pack(anchor="w")
        
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=1,
            number_of_steps=10,
            command=self._on_volume_change,
            fg_color=Colors.BG_INPUT,
            progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY
        )
        self.volume_slider.pack(fill="x", pady=5)
        
        self.volume_value_label = StyledLabel(volume_frame, text="80%", style="normal")
        self.volume_value_label.pack(anchor="e")
        
        # Test sound button
        test_frame = StyledFrame(section, style="transparent")
        test_frame.pack(fill="x", padx=20, pady=(5, 20))
        
        StyledButton(
            test_frame,
            text="🔔 Test âm thanh",
            command=self._test_sound,
            style="info",
            width=150
        ).pack(anchor="w")
    
    def _create_preset_section(self, parent):
        """Create sensitivity presets section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)
        
        # Title
        StyledLabel(
            section,
            text="📊 Mức độ nhạy",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        StyledLabel(
            section,
            text="Chọn preset hoặc tự điều chỉnh ở trên",
            style="muted",
            size=12
        ).pack(anchor="w", padx=20, pady=(0, 15))
        
        # Preset buttons
        preset_frame = StyledFrame(section, style="transparent")
        preset_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        StyledButton(
            preset_frame,
            text="🟢 Thấp",
            command=lambda: self._apply_preset("LOW"),
            style="success",
            width=100
        ).pack(side="left", padx=5)
        
        StyledButton(
            preset_frame,
            text="🟡 Trung bình",
            command=lambda: self._apply_preset("MEDIUM"),
            style="warning",
            width=120
        ).pack(side="left", padx=5)
        
        StyledButton(
            preset_frame,
            text="🔴 Cao",
            command=lambda: self._apply_preset("HIGH"),
            style="danger",
            width=100
        ).pack(side="left", padx=5)
        
        # Current preset indicator
        self.preset_label = StyledLabel(
            section,
            text="Hiện tại: Trung bình",
            style="muted",
            size=12
        )
        self.preset_label.pack(anchor="w", padx=20, pady=(0, 15))
    
    def _create_account_section(self, parent):
        """Create account settings section"""
        section = StyledFrame(parent, style="card")
        section.pack(fill="x", pady=10)
        
        # Title
        StyledLabel(
            section,
            text="👤 Tài khoản",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # User info
        if self.user_data:
            info_frame = StyledFrame(section, style="transparent")
            info_frame.pack(fill="x", padx=20, pady=10)
            
            StyledLabel(
                info_frame,
                text=f"Username: {self.user_data.get('username', 'N/A')}",
                style="normal"
            ).pack(anchor="w")
            
            StyledLabel(
                info_frame,
                text=f"Email: {self.user_data.get('email', 'Chưa cập nhật')}",
                style="muted"
            ).pack(anchor="w")
        
        # Change password button
        btn_frame = StyledFrame(section, style="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        StyledButton(
            btn_frame,
            text="🔒 Đổi mật khẩu",
            command=self._show_change_password,
            style="secondary",
            width=150
        ).pack(side="left", padx=5)
    
    def _create_action_buttons(self, parent):
        """Create action buttons"""
        btn_frame = StyledFrame(parent, style="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        StyledButton(
            btn_frame,
            text="💾 Lưu cài đặt",
            command=self._save_settings,
            style="success",
            width=150
        ).pack(side="left", padx=5)
        
        StyledButton(
            btn_frame,
            text="🔄 Khôi phục mặc định",
            command=self._reset_defaults,
            style="secondary",
            width=180
        ).pack(side="left", padx=5)
    
    def _load_settings(self):
        """Load current settings"""
        settings = settings_controller.get_settings()
        
        # Update sliders
        ear = settings.get('ear_threshold', 0.25)
        mar = settings.get('mar_threshold', 0.70)
        head = settings.get('head_threshold', 30.0)
        volume = settings.get('alert_volume', 0.8)
        sound_enabled = settings.get('enable_sound', True)
        sensitivity = settings.get('sensitivity_level', 'MEDIUM')
        
        self.ear_slider.set(ear)
        self.ear_value_label.configure(text=f"{ear:.2f}")
        
        self.mar_slider.set(mar)
        self.mar_value_label.configure(text=f"{mar:.2f}")
        
        self.head_slider.set(head)
        self.head_value_label.configure(text=f"{head:.0f}°")
        
        self.volume_slider.set(volume)
        self.volume_value_label.configure(text=f"{int(volume * 100)}%")
        
        if sound_enabled:
            self.sound_switch.select()
        else:
            self.sound_switch.deselect()
        
        # Update preset label
        preset_names = {'LOW': 'Thấp', 'MEDIUM': 'Trung bình', 'HIGH': 'Cao'}
        self.preset_label.configure(
            text=f"Hiện tại: {preset_names.get(sensitivity, 'Tùy chỉnh')}"
        )
    
    def _on_ear_change(self, value):
        """Handle EAR slider change"""
        self.ear_value_label.configure(text=f"{value:.2f}")
    
    def _on_mar_change(self, value):
        """Handle MAR slider change"""
        self.mar_value_label.configure(text=f"{value:.2f}")
    
    def _on_head_change(self, value):
        """Handle head threshold slider change"""
        self.head_value_label.configure(text=f"{value:.0f}°")
    
    def _on_volume_change(self, value):
        """Handle volume slider change"""
        self.volume_value_label.configure(text=f"{int(value * 100)}%")
        audio_manager.set_volume(value)
    
    def _on_sound_toggle(self):
        """Handle sound toggle"""
        if self.sound_switch.get():
            audio_manager.enable()
        else:
            audio_manager.disable()
    
    def _test_sound(self):
        """Test alert sound"""
        audio_manager.play_beep()
    
    def _apply_preset(self, level: str):
        """Apply sensitivity preset"""
        success, message = settings_controller.set_sensitivity_level(level)
        
        if success:
            self._load_settings()
            MessageBox.show_success(self, "Thành công", f"Đã áp dụng mức độ: {level}")
        else:
            MessageBox.show_error(self, "Lỗi", message)
    
    def _save_settings(self):
        """Save current settings"""
        ear = self.ear_slider.get()
        mar = self.mar_slider.get()
        head = self.head_slider.get()
        volume = self.volume_slider.get()
        sound = self.sound_switch.get()
        
        success, message = settings_controller.update_settings(
            ear_threshold=ear,
            mar_threshold=mar,
            head_threshold=head,
            alert_volume=volume,
            enable_sound=sound
        )
        
        if success:
            MessageBox.show_success(self, "Thành công", message)
        else:
            MessageBox.show_error(self, "Lỗi", message)
    
    def _reset_defaults(self):
        """Reset to default settings"""
        if MessageBox.ask_yes_no(
            self,
            "Xác nhận",
            "Bạn có chắc muốn khôi phục cài đặt mặc định?"
        ):
            success, message = settings_controller.reset_to_defaults()
            
            if success:
                self._load_settings()
                MessageBox.show_success(self, "Thành công", "Đã khôi phục cài đặt mặc định!")
            else:
                MessageBox.show_error(self, "Lỗi", message)
    
    def _show_change_password(self):
        """Show change password dialog"""
        MessageBox.show_info(
            self,
            "Thông báo",
            "Tính năng đổi mật khẩu đang được phát triển!"
        )
    
    def _on_back_click(self):
        """Handle back button click"""
        if self.on_back:
            self.on_back()


if __name__ == "__main__":
    # Test settings view
    root = ctk.CTk()
    root.title("Settings Test")
    root.geometry("800x700")
    
    user = {'id': 1, 'username': 'test_user', 'email': 'test@example.com'}
    view = SettingsView(root, user_data=user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
