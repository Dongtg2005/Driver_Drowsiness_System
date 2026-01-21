"""
============================================
🔐 Login View
Driver Drowsiness Detection System
Login screen GUI
============================================
"""

import customtkinter as ctk
from typing import Callable, Optional
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledEntry, StyledLabel, 
    StyledFrame, MessageBox
)
from src.controllers.auth_controller import auth_controller


class LoginView(ctk.CTkFrame):
    """Login screen view"""
    
    def __init__(self, master, on_login_success: Callable = None,
                 on_register_click: Callable = None):
        """
        Create login view.
        
        Args:
            master: Parent widget
            on_login_success: Callback when login succeeds
            on_register_click: Callback when register button clicked
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.on_login_success = on_login_success
        self.on_register_click = on_register_click
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create login form widgets"""
        # Center container
        center_frame = StyledFrame(self, style="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo/Title
        logo_frame = StyledFrame(center_frame, style="transparent")
        logo_frame.pack(pady=(0, 30))
        
        StyledLabel(
            logo_frame, 
            text="🚗", 
            size=64
        ).pack()
        
        StyledLabel(
            logo_frame,
            text="Driver Drowsiness Detection",
            style="title"
        ).pack(pady=(10, 0))
        
        StyledLabel(
            logo_frame,
            text="Hệ thống phát hiện lái xe ngủ gật",
            style="subtitle"
        ).pack()
        
        # Login form card
        form_card = StyledFrame(center_frame, style="card")
        form_card.pack(padx=40, pady=20, ipadx=30, ipady=30)
        
        StyledLabel(
            form_card,
            text="Đăng nhập",
            style="title"
        ).pack(pady=(0, 20))
        
        # Username
        username_frame = StyledFrame(form_card, style="transparent")
        username_frame.pack(fill="x", pady=10)
        
        StyledLabel(
            username_frame,
            text="👤 Tên đăng nhập",
            style="normal"
        ).pack(anchor="w")
        
        self.username_entry = StyledEntry(
            username_frame,
            placeholder_text="Nhập tên đăng nhập",
            width=300
        )
        self.username_entry.pack(fill="x", pady=(5, 0))
        
        # Password
        password_frame = StyledFrame(form_card, style="transparent")
        password_frame.pack(fill="x", pady=10)
        
        StyledLabel(
            password_frame,
            text="🔒 Mật khẩu",
            style="normal"
        ).pack(anchor="w")
        
        self.password_entry = StyledEntry(
            password_frame,
            placeholder_text="Nhập mật khẩu",
            width=300,
            show="•"
        )
        self.password_entry.pack(fill="x", pady=(5, 0))
        
        # Remember Me Checkbox
        self.remember_var = ctk.StringVar(value="off")
        self.chk_remember = ctk.CTkCheckBox(
            form_card, 
            text="Ghi nhớ đăng nhập",
            variable=self.remember_var,
            onvalue="on", 
            offvalue="off",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.chk_remember.pack(anchor="w", pady=(15, 0))

        # Error message label
        self.error_label = StyledLabel(
            form_card,
            text="",
            style="danger",
            size=12
        )
        self.error_label.pack(pady=5)
        
        # Login button
        self.login_btn = StyledButton(
            form_card,
            text="Đăng nhập",
            command=self._on_login,
            style="primary",
            width=300,
            height=45
        )
        self.login_btn.pack(pady=(20, 10))
        
        # Register link
        register_frame = StyledFrame(form_card, style="transparent")
        register_frame.pack(pady=10)
        
        StyledLabel(
            register_frame,
            text="Chưa có tài khoản?",
            style="muted"
        ).pack(side="left")
        
        register_btn = ctk.CTkButton(
            register_frame,
            text="Đăng ký ngay",
            command=self._on_register_click,
            fg_color="transparent",
            hover_color=Colors.PRIMARY,
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(size=14, underline=True),
            width=100
        )
        register_btn.pack(side="left", padx=5)
        
        # Bind Enter key
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self._on_login())
        
        # Fill saved credentials
        saved_user, saved_pass = auth_controller.get_saved_credentials()
        if saved_user:
            self.username_entry.insert(0, saved_user)
            self.password_entry.insert(0, saved_pass)
            self.remember_var.set("on")
            self.login_btn.focus() # Focus on login button if autofilled
        else:
            # Focus username entry
            self.username_entry.focus()
    
    def _on_login(self):
        """Handle login button click"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        remember = (self.remember_var.get() == "on")
        
        # Clear previous error
        self.error_label.configure(text="")
        
        # Attempt login
        success, message, user = auth_controller.login(username, password, remember=remember)
        
        if success:
            if self.on_login_success:
                self.on_login_success(user)
        else:
            self.error_label.configure(text=message)
            self.password_entry.delete(0, "end")
    
    def _on_register_click(self):
        """Handle register link click"""
        if self.on_register_click:
            self.on_register_click()
    
    def clear_form(self):
        """Clear form fields"""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")


if __name__ == "__main__":
    # Test login view
    root = ctk.CTk()
    root.title("Login Test")
    root.geometry("800x600")
    
    def on_success(user):
        print(f"Login success: {user}")
    
    def on_register():
        print("Register clicked")
    
    view = LoginView(root, on_login_success=on_success, on_register_click=on_register)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
