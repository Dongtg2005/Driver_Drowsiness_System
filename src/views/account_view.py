
import customtkinter as ctk
from typing import Callable, Optional
from tkinter import filedialog
from PIL import Image
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame, MessageBox
)
from src.utils.toast_notification import ToastContainer
from src.controllers.auth_controller import auth_controller
from src.models.user_model import User
from config import config

class AccountView(ctk.CTkFrame):
    """
    User Account Management View.
    Allows editing profile info and changing avatar.
    """
    
    def __init__(self, master, user: Optional[User] = None, on_back: Optional[Callable] = None):
        super().__init__(master, fg_color=Colors.BG_DARK)
        self.user = user
        self.on_back = on_back
        self.avatar_path = user.avatar if user else None
        
        # Initialize Toast Container
        self.toast_container = ToastContainer(self.winfo_toplevel())
        
        self._create_widgets()

    # ... (rest of methods) ...

    def _save_changes(self):
        full_name = self.name_entry.get()
        email = self.email_entry.get()
        phone = self.phone_entry.get()
        
        success, msg = auth_controller.update_profile(
            full_name=full_name,
            email=email,
            phone=phone,
            avatar_path=self.avatar_path
        )
        
        if success:
            # Use Toast instead of MessageBox
            self.toast_container.show_toast(
                message=msg,
                notification_type="success",
                position="top-right"
            )
            # Update local user reference display immediately
             # (In a real app, might need to refresh parent view too)
        else:
            MessageBox.show_error(self, "Lỗi", msg)
        
    def _create_widgets(self):
        # Header
        header = StyledFrame(self, style="card")
        header.pack(fill="x", padx=10, pady=10)
        
        StyledButton(
            header, text="← Quay lại", command=self.on_back,
            style="secondary", width=100, height=35
        ).pack(side="left", padx=10)
        
        StyledLabel(header, text="👤 Thông tin tài khoản", style="title", size=18).pack(side="left", padx=20)
        
        # Main Content - Split into Left (Avatar) and Right (Form)
        content = StyledFrame(self, style="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- Left Side: Avatar ---
        left_panel = StyledFrame(content, style="card")
        left_panel.pack(side="left", fill="y", padx=(0, 10), ipadx=20)
        
        self.avatar_label = ctk.CTkLabel(left_panel, text="")
        self.avatar_label.pack(pady=20)
        self._load_avatar()
        
        StyledButton(
            left_panel, text="📷 Đổi ảnh", command=self._change_avatar,
            style="info", width=120
        ).pack(pady=10)
        
        StyledLabel(left_panel, text=f"@{self.user.username}", style="title", size=16).pack(pady=(10, 5))
        StyledLabel(left_panel, text=f"ID: {self.user.id}", style="muted").pack(pady=5)

        # --- Right Side: Form ---
        right_panel = StyledFrame(content, style="card")
        right_panel.pack(side="right", fill="both", expand=True)
        
        StyledLabel(right_panel, text="Chỉnh sửa thông tin", style="title", size=16).pack(anchor="w", padx=20, pady=20)
        
        # Full Name
        self.name_entry = self._create_input(right_panel, "Họ và tên:", self.user.full_name or "")
        
        # Email (Read-only)
        self.email_entry = self._create_input(right_panel, "Email (Không thể thay đổi):", self.user.email or "", readonly=True)
        
        # Phone
        self.phone_entry = self._create_input(right_panel, "Số điện thoại:", self.user.phone or "")
        
        # Actions
        btn_frame = StyledFrame(right_panel, style="transparent")
        btn_frame.pack(pady=30, padx=20, anchor="e")
        
        StyledButton(
            btn_frame, text="💾 Lưu thay đổi", command=self._save_changes,
            style="success", width=150
        ).pack(side="right")

    def _create_input(self, parent, label: str, value: str, readonly: bool = False) -> ctk.CTkEntry:
        frame = StyledFrame(parent, style="transparent")
        frame.pack(fill="x", padx=20, pady=10)
        
        StyledLabel(frame, text=label, style="normal").pack(anchor="w", pady=(0, 5))
        
        entry = ctk.CTkEntry(
            frame, width=300, height=40,
            fg_color=Colors.BG_INPUT if not readonly else "#2b2b2b", 
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_WHITE if not readonly else Colors.TEXT_MUTED
        )
        entry.pack(fill="x")
        if value:
            entry.insert(0, value)
            
        if readonly:
            entry.configure(state="disabled")
            
        return entry

    def _load_avatar(self):
        try:
            # Default placeholder logic
            size = (150, 150)
            if self.avatar_path and os.path.exists(self.avatar_path):
                img = Image.open(self.avatar_path)
            else:
                # Placeholder: create a solid color image with initials? Or just a simple gray box
                img = Image.new('RGB', size, color=(70, 70, 70))
            
            # Apply circular mask (simple resizing for now)
            img = img.resize(size)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self.avatar_label.configure(image=photo)
            self.avatar_label.image = photo 
        except Exception as e:
            print(f"Error loading avatar: {e}")

    def _change_avatar(self):
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh đại diện",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
        )
        if file_path:
            # 1. Check extensions strictly
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                MessageBox.show_error(self, "Lỗi định dạng", "Chỉ chấp nhận file ảnh .jpg, .jpeg, .png")
                return

            # 2. Check file size (max 2MB)
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb > 2.0:
                    MessageBox.show_error(self, "Ảnh quá lớn", f"Kích thước ảnh phải nhỏ hơn 2MB\n(Ảnh hiện tại: {size_mb:.1f}MB)")
                    return
            except Exception as e:
                MessageBox.show_error(self, "Lỗi", f"Không thể đọc file: {e}")
                return

            self.avatar_path = file_path
            self._load_avatar()

    def _save_changes(self):
        full_name = self.name_entry.get()
        email = self.email_entry.get()
        phone = self.phone_entry.get()
        
        success, msg = auth_controller.update_profile(
            full_name=full_name,
            email=email,
            phone=phone,
            avatar_path=self.avatar_path
        )
        
        if success:
            # Use Toast instead of MessageBox
            self.toast_container.show_toast(
                message=msg,
                notification_type="success",
                position="top-center"
            )
            # Update local user reference display immediately
             # (In a real app, might need to refresh parent view too)
        else:
            MessageBox.show_error(self, "Lỗi", msg)

