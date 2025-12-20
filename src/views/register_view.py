"""
============================================
📝 Register View
Driver Drowsiness Detection System
Registration screen GUI
============================================
"""

import customtkinter as ctk
from typing import Callable
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledEntry, StyledLabel, 
    StyledFrame, MessageBox
)
from src.controllers.auth_controller import auth_controller


class RegisterView(ctk.CTkFrame):
    """Registration screen view"""
    
    def __init__(self, master, on_register_success: Callable = None,
                 on_back_to_login: Callable = None):
        """
        Create register view.
        
        Args:
            master: Parent widget
            on_register_success: Callback when registration succeeds
            on_back_to_login: Callback to return to login
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.on_register_success = on_register_success
        self.on_back_to_login = on_back_to_login
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create registration form widgets"""
        # Center container
        center_frame = StyledFrame(self, style="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        title_frame = StyledFrame(center_frame, style="transparent")
        title_frame.pack(pady=(0, 20))
        
        StyledLabel(
            title_frame,
            text="📝 Đăng ký tài khoản",
            style="title"
        ).pack()
        
        StyledLabel(
            title_frame,
            text="Tạo tài khoản mới để sử dụng hệ thống",
            style="subtitle"
        ).pack()
        
        # Registration form card
        form_card = StyledFrame(center_frame, style="card")
        form_card.pack(padx=40, pady=20, ipadx=30, ipady=30)
        
        # Username
        self._create_field(form_card, "👤 Tên đăng nhập *", "username")
        
        # Full name
        self._create_field(form_card, "📛 Họ và tên", "fullname")
        
        # Email
        self._create_field(form_card, "📧 Email", "email")
        
        # Password
        self._create_field(form_card, "🔒 Mật khẩu *", "password", show="•")
        
        # Confirm password
        self._create_field(form_card, "🔒 Xác nhận mật khẩu *", "confirm", show="•")
        
        # Error message label
        self.error_label = StyledLabel(
            form_card,
            text="",
            style="danger",
            size=12
        )
        self.error_label.pack(pady=5)
        
        # Buttons
        btn_frame = StyledFrame(form_card, style="transparent")
        btn_frame.pack(pady=(20, 10), fill="x")
        
        # Register button
        self.register_btn = StyledButton(
            btn_frame,
            text="Đăng ký",
            command=self._on_register,
            style="success",
            width=140,
            height=45
        )
        self.register_btn.pack(side="left", padx=5, expand=True)
        
        # Back button
        self.back_btn = StyledButton(
            btn_frame,
            text="Quay lại",
            command=self._on_back,
            style="secondary",
            width=140,
            height=45
        )
        self.back_btn.pack(side="right", padx=5, expand=True)
        
        # Required fields note
        StyledLabel(
            form_card,
            text="* Trường bắt buộc",
            style="muted",
            size=11
        ).pack(pady=(10, 0))
    
    def _create_field(self, parent, label: str, field_name: str, show: str = None):
        """Create a form field"""
        frame = StyledFrame(parent, style="transparent")
        frame.pack(fill="x", pady=8)
        
        StyledLabel(
            frame,
            text=label,
            style="normal",
            size=13
        ).pack(anchor="w")
        
        entry = StyledEntry(
            frame,
            placeholder_text=f"Nhập {label.replace('*', '').replace('👤', '').replace('📛', '').replace('📧', '').replace('🔒', '').strip().lower()}",
            width=300,
            show=show
        )
        entry.pack(fill="x", pady=(5, 0))
        
        # Store reference
        setattr(self, f"{field_name}_entry", entry)
    
    def _on_register(self):
        """Handle register button click"""
        # Get values
        username = self.username_entry.get().strip()
        fullname = self.fullname_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        # Clear previous error
        self.error_label.configure(text="")
        
        # Attempt registration
        success, message = auth_controller.register(
            username=username,
            password=password,
            confirm_password=confirm,
            full_name=fullname if fullname else None,
            email=email if email else None
        )
        
        if success:
            MessageBox.show_success(
                self,
                "Thành công",
                "Đăng ký thành công! Vui lòng đăng nhập."
            )
            if self.on_register_success:
                self.on_register_success()
        else:
            self.error_label.configure(text=message)
    
    def _on_back(self):
        """Handle back button click"""
        if self.on_back_to_login:
            self.on_back_to_login()
    
    def clear_form(self):
        """Clear all form fields"""
        self.username_entry.delete(0, "end")
        self.fullname_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.confirm_entry.delete(0, "end")
        self.error_label.configure(text="")


if __name__ == "__main__":
    # Test register view
    root = ctk.CTk()
    root.title("Register Test")
    root.geometry("800x700")
    
    def on_success():
        print("Register success")
    
    def on_back():
        print("Back to login")
    
    view = RegisterView(root, on_register_success=on_success, on_back_to_login=on_back)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
