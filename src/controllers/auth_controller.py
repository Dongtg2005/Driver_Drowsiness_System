"""
================================================================
🔐 Authentication Controller (Refactored with SQLAlchemy)
Driver Drowsiness Detection System
Handles login, register, logout logic using SQLAlchemy ORM.
================================================================
"""
from typing import Optional, Tuple
import re
import bcrypt
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal, get_db
from src.models.user_model import User
from src.models.user_settings_model import UserSettings
from src.utils.logger import logger

# --- Password Hashing Utilities ---

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

import json
import os
import base64

# --- Main Controller Class ---

class AuthController:
    """
    Controller for authentication operations using SQLAlchemy.
    """
    
    def __init__(self):
        """Initialize auth controller"""
        self._current_user: Optional[User] = None
        self._credentials_file = "saved_credentials.json"

    def save_credentials(self, username: str, password: str):
        """Save credentials to local file (simple encoding)"""
        try:
            data = {
                "username": username,
                "password": base64.b64encode(password.encode()).decode() 
            }
            with open(self._credentials_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def clear_saved_credentials(self):
        """Remove saved credentials"""
        if os.path.exists(self._credentials_file):
            try:
                os.remove(self._credentials_file)
            except Exception:
                pass

    def get_saved_credentials(self) -> Tuple[str, str]:
        """Get saved credentials if they exist"""
        if not os.path.exists(self._credentials_file):
            return "", ""
        
        try:
            with open(self._credentials_file, "r") as f:
                data = json.load(f)
                username = data.get("username", "")
                encoded_pw = data.get("password", "")
                password = base64.b64decode(encoded_pw.encode()).decode() if encoded_pw else ""
                return username, password
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return "", ""
    
    def login(self, username: str, password: str, remember: bool = False) -> Tuple[bool, str, Optional[User]]:
        """
        Handles user login using SQLAlchemy.
        Returns: (success, message, user_object)
        """
        if not username or not password:
            return False, "Vui lòng nhập đầy đủ thông tin!", None
        
        username = username.strip()
        db: Session = SessionLocal()
        try:
            # Find the user by username
            user = db.query(User).filter(User.username == username).first()
            
            # Verify user existence and password
            if user and verify_password(password, user.password):
                if not user.is_active:
                    return False, "Tài khoản đã bị khóa!", None

                self._current_user = user
                
                # Handle Remember Me
                if remember:
                    self.save_credentials(username, password)
                else:
                    self.clear_saved_credentials()
                    
                logger.info(f"User logged in: {username}")
                return True, "Đăng nhập thành công!", user
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                return False, "Sai tên đăng nhập hoặc mật khẩu!", None
                
        except Exception as e:
            logger.error(f"Database error during login: {e}")
            return False, "Lỗi kết nối cơ sở dữ liệu!", None
        finally:
            db.close()


    def register(self, username: str, password: str, confirm_password: str,
                 full_name: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Handles new user registration using SQLAlchemy.
        """
        # --- Input Validation ---
        if not username or not password:
            return False, "Vui lòng nhập tên đăng nhập và mật khẩu!"
        username = username.strip()
        if len(username) < 3:
            return False, "Tên đăng nhập phải có ít nhất 3 ký tự!"
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return False, "Tên đăng nhập chỉ chứa chữ, số và gạch dưới!"
        if len(password) < 6:
            return False, "Mật khẩu phải có ít nhất 6 ký tự!"
        if password != confirm_password:
            return False, "Mật khẩu xác nhận không khớp!"
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
            return False, "Email không hợp lệ!"

        db: Session = SessionLocal()
        try:
            # Check if username already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                return False, f"Tên đăng nhập '{username}' đã tồn tại!"

            # Create new user object
            hashed_pwd = hash_password(password)
            new_user = User(
                username=username,
                password=hashed_pwd,
                full_name=full_name.strip() if full_name else None,
                email=email.strip() if email else None
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user) # To get the new user's ID

            logger.info(f"New user registered: {username} (ID: {new_user.id})")
            return True, "Đăng ký thành công! Vui lòng đăng nhập."
                
        except Exception as e:
            logger.error(f"Database error during registration: {e}")
            db.rollback()
            return False, "Lỗi hệ thống! Vui lòng thử lại sau."
        finally:
            db.close()

    def logout(self) -> None:
        """Logs out the current user."""
        if self._current_user:
            logger.info(f"User logged out: {self._current_user.username}")
        self._current_user = None

    def is_logged_in(self) -> bool:
        return self._current_user is not None
    
    def get_current_user(self) -> Optional[User]:
        return self._current_user

    def change_password(self, old_password: str, new_password: str,
                        confirm_password: str) -> Tuple[bool, str]:
        """Changes the current user's password."""
        if not self._current_user:
            return False, "Chưa đăng nhập!"
        
        # --- Input Validation ---
        if not old_password or not new_password:
            return False, "Vui lòng nhập đầy đủ thông tin!"
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự!"
        if new_password != confirm_password:
            return False, "Mật khẩu xác nhận không khớp!"
        if old_password == new_password:
            return False, "Mật khẩu mới phải khác mật khẩu cũ!"

        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == self._current_user.id).first()
            if not user or not verify_password(old_password, user.password):
                return False, "Mật khẩu cũ không chính xác!"

            user.password = hash_password(new_password)
            db.commit()

            logger.info(f"Password changed for user: {self._current_user.username}")
            return True, "Đổi mật khẩu thành công!"
        except Exception as e:
            logger.error(f"Database error during password change: {e}")
            db.rollback()
            return False, "Lỗi hệ thống khi đổi mật khẩu."
        finally:
            db.close()

    def update_profile(self, full_name: str, email: str, phone: str = None, avatar_path: str = None) -> Tuple[bool, str]:
        """
        Updates current user's profile information.
        """
        if not self._current_user:
            return False, "Chưa đăng nhập!"

        # Input Validation
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
            return False, "Email không hợp lệ!"
            
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == self._current_user.id).first()
            if not user:
                return False, "Không tìm thấy người dùng!"
                
            # Update fields
            user.full_name = full_name.strip() if full_name else user.full_name
            user.email = email.strip() if email else user.email
            user.phone = phone.strip() if phone else user.phone
            if avatar_path:
                user.avatar = avatar_path
            
            db.commit()
            
            # Update local cache
            self._current_user = user
            
            logger.info(f"Profile updated for user: {user.username}")
            return True, "Cập nhật thông tin thành công!"
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            db.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            db.close()

# --- Singleton Instance ---
# The rest of the application will use this single instance.
auth_controller = AuthController()

def get_auth_controller() -> AuthController:
    """Returns the singleton instance of the AuthController."""
    return auth_controller
