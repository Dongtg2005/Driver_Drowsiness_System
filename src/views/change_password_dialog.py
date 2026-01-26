
import customtkinter as ctk
from typing import Callable
from src.views.components import Colors, StyledButton, StyledLabel, StyledFrame, MessageBox
from src.controllers.auth_controller import auth_controller

class ChangePasswordDialog(ctk.CTkToplevel):
    """
    Modal dialog for changing password.
    """
    def __init__(self, parent, on_success: Callable = None):
        super().__init__(parent)
        self.on_success = on_success
        
        self.title("Đổi Mật Khẩu")
        self.geometry("400x450")
        self.resizable(False, False)
        
        # Bring to front
        self.lift()
        self.attributes("-topmost", True)
        self.transient(parent) # Associate with parent
        self.grab_set() # Modal behavior
        
        self.configure(fg_color=Colors.BG_DARK)
        self._create_widgets()
        
    def _create_widgets(self):
        # Title
        StyledLabel(self, text="🔒 Đổi Mật Khẩu", style="title", size=18).pack(pady=20)
        
        # Old Password
        self.old_pw = self._create_input("Mật khẩu hiện tại:", show="*")
        
        # New Password
        self.new_pw = self._create_input("Mật khẩu mới (tối thiểu 6 ký tự):", show="*")
        
        # Confirm Password
        self.confirm_pw = self._create_input("Xác nhận mật khẩu mới:", show="*")
        
        # Actions
        btn_frame = StyledFrame(self, style="transparent")
        btn_frame.pack(pady=30)
        
        StyledButton(
            btn_frame, text="Hủy", command=self.destroy,
            style="secondary", width=100
        ).pack(side="left", padx=10)
        
        StyledButton(
            btn_frame, text="✅ Cập nhật", command=self._submit,
            style="success", width=120
        ).pack(side="left", padx=10)
        
    def _create_input(self, label_text: str, show: str = None) -> ctk.CTkEntry:
        frame = StyledFrame(self, style="transparent")
        frame.pack(fill="x", padx=30, pady=10)
        
        StyledLabel(frame, text=label_text, style="normal").pack(anchor="w", pady=(0, 5))
        
        entry = ctk.CTkEntry(
            frame, width=300, height=40,
            fg_color=Colors.BG_INPUT, border_color=Colors.BORDER,
            text_color=Colors.TEXT_WHITE,
            show=show
        )
        entry.pack(fill="x")
        return entry
        
    def _submit(self):
        old_pw = self.old_pw.get()
        new_pw = self.new_pw.get()
        confirm_pw = self.confirm_pw.get()
        
        # Basic Validation UI side
        if not old_pw or not new_pw or not confirm_pw:
            MessageBox.show_error(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin!")
            return
            
        if len(new_pw) < 6:
            MessageBox.show_error(self, "Lỗi", "Mật khẩu mới phải có ít nhất 6 ký tự!")
            return
            
        if new_pw != confirm_pw:
            MessageBox.show_error(self, "Lỗi", "Mật khẩu xác nhận không khớp!")
            return
            
        # Call Controller
        success, msg = auth_controller.change_password(old_pw, new_pw, confirm_pw)
        
        if success:
            MessageBox.show_success(self, "Thành công", "Đổi mật khẩu thành công!\nVui lòng đăng nhập lại.")
            self.destroy()
            if self.on_success:
                self.on_success()
        else:
            MessageBox.show_error(self, "Lỗi", msg)
