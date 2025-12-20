"""
============================================
🔐 Authentication Controller (Final Version)
Driver Drowsiness Detection System
Handle login, register, logout logic
============================================
"""

from typing import Optional, Dict, Tuple
import sys
import os
import re # Import Regular Expression để check email/username chuẩn hơn

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.user_model import user_model
from src.utils.logger import logger

class AuthController:
    """
    Controller for authentication operations.
    Handles login, registration, and session management.
    """
    
    def __init__(self):
        """Initialize auth controller"""
        self.user_model = user_model
        self._current_user: Optional[Dict] = None
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Xử lý đăng nhập.
        Returns: (success, message, user_data)
        """
        # Validate input
        if not username or not password:
            return False, "Vui lòng nhập đầy đủ thông tin!", None
        
        username = username.strip()
        
        # Gọi Model kiểm tra DB
        try:
            user = self.user_model.authenticate(username, password)
            
            if user:
                # Kiểm tra trạng thái kích hoạt
                if not user.get('is_active', True):
                    return False, "Tài khoản đã bị khóa!", None

                self._current_user = user
                
                # [FIXED] Dùng logger.info thay vì logger.log_login (vì logger cũ không có hàm này)
                logger.info(f"User logged in: {username}")
                return True, "Đăng nhập thành công!", user
            else:
                logger.info(f"Failed login attempt: {username}")
                return False, "Sai tên đăng nhập hoặc mật khẩu!", None
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, "Lỗi kết nối cơ sở dữ liệu!", None
    
    def register(self, username: str, password: str, confirm_password: str,
                 full_name: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Xử lý đăng ký.
        Returns: (success, message)
        """
        # 1. Validate Input cơ bản
        if not username or not password:
            return False, "Vui lòng nhập tên đăng nhập và mật khẩu!"
        
        username = username.strip()
        
        # 2. Validate Username (Độ dài và ký tự đặc biệt)
        if len(username) < 3:
            return False, "Tên đăng nhập phải có ít nhất 3 ký tự!"
        
        if len(username) > 50:
            return False, "Tên đăng nhập quá dài!"
        
        # Cho phép chữ, số và gạch dưới (Regex)
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return False, "Tên đăng nhập chỉ chứa chữ, số và gạch dưới!"
        
        # 3. Validate Password
        if len(password) < 6:
            return False, "Mật khẩu phải có ít nhất 6 ký tự!"
        
        if password != confirm_password:
            return False, "Mật khẩu xác nhận không khớp!"
        
        # 4. Validate Email (Regex chuẩn)
        if email:
            email = email.strip()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return False, "Email không hợp lệ!"
        
        # 5. Kiểm tra trùng Username
        if self.user_model.get_by_username(username):
            return False, f"Tên đăng nhập '{username}' đã tồn tại!"
        
        # 6. Gọi Model tạo User
        try:
            user_id = self.user_model.register(
                username=username,
                password=password,
                full_name=full_name.strip() if full_name else None,
                email=email
            )
            
            if user_id:
                logger.info(f"New user registered: {username} (ID: {user_id})")
                return True, "Đăng ký thành công! Vui lòng đăng nhập."
            else:
                return False, "Đăng ký thất bại do lỗi hệ thống."
                
        except Exception as e:
            logger.error(f"Register error: {e}")
            return False, "Lỗi hệ thống! Vui lòng thử lại sau."
    
    def logout(self) -> None:
        """Đăng xuất"""
        if self._current_user:
            logger.info(f"User logged out: {self._current_user.get('username')}")
        
        self._current_user = None
        self.user_model.logout()
    
    def is_logged_in(self) -> bool:
        return self._current_user is not None
    
    def get_current_user(self) -> Optional[Dict]:
        return self._current_user
    
    def update_profile(self, **kwargs) -> Tuple[bool, str]:
        """Cập nhật thông tin cá nhân"""
        if not self._current_user:
            return False, "Chưa đăng nhập!"
        
        user_id = self._current_user['id']
        
        # Validate Email nếu có thay đổi
        if 'email' in kwargs and kwargs['email']:
            email = kwargs['email'].strip()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return False, "Email không hợp lệ!"
            kwargs['email'] = email
        
        success = self.user_model.update_profile(user_id, **kwargs)
        
        if success:
            # Cập nhật lại dữ liệu local trong session
            for key, value in kwargs.items():
                if key in self._current_user:
                    self._current_user[key] = value
            
            logger.info(f"Profile updated for user: {self._current_user['username']}")
            return True, "Cập nhật thông tin thành công!"
        
        return False, "Cập nhật thất bại!"
    
    def change_password(self, old_password: str, new_password: str,
                        confirm_password: str) -> Tuple[bool, str]:
        """Đổi mật khẩu"""
        if not self._current_user:
            return False, "Chưa đăng nhập!"
        
        if not old_password or not new_password:
            return False, "Vui lòng nhập đầy đủ thông tin!"
        
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự!"
        
        if new_password != confirm_password:
            return False, "Mật khẩu xác nhận không khớp!"
        
        if old_password == new_password:
            return False, "Mật khẩu mới phải khác mật khẩu cũ!"
        
        success = self.user_model.change_password(
            self._current_user['id'],
            old_password,
            new_password
        )
        
        if success:
            logger.info(f"Password changed for user: {self._current_user['username']}")
            return True, "Đổi mật khẩu thành công!"
        
        return False, "Mật khẩu cũ không chính xác!"
    
    def get_user_settings(self) -> Optional[Dict]:
        """Lấy cài đặt của user hiện tại"""
        if not self._current_user:
            return None
        return self.user_model.get_user_settings(self._current_user['id'])
    
    def update_settings(self, **kwargs) -> Tuple[bool, str]:
        """Cập nhật cài đặt"""
        if not self._current_user:
            return False, "Chưa đăng nhập!"
        
        success = self.user_model.update_user_settings(
            self._current_user['id'],
            **kwargs
        )
        
        if success:
            return True, "Cập nhật cài đặt thành công!"
        
        return False, "Cập nhật thất bại!"


# Create singleton instance
auth_controller = AuthController()

def get_auth_controller() -> AuthController:
    return auth_controller