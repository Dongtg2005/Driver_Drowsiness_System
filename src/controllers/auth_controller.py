"""
================================================================
🔐 Authentication Controller (Refactored with Safe DB Access)
Driver Drowsiness Detection System
Handles login, register, logout logic using Raw SQL (Offline Safe).
================================================================
"""
from typing import Optional, Tuple
import re
import bcrypt
import json
import os
import base64

from src.database.db_connection import get_db, execute_query
from src.models.user_model import User
from src.utils.logger import logger

# --- Password Hashing Utilities ---

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

# --- Main Controller Class ---

class AuthController:
    """
    Controller for authentication operations using Safe DB Connection.
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
        Handles user login using Safe DB Access.
        Returns: (success, message, user_object)
        """
        if not username or not password:
            return False, "Vui lòng nhập đầy đủ thông tin!", None
        
        username = username.strip()

        # [OFFLINE-FIRST] CHECK NETWORK STATUS
        if get_db().is_offline:
            logger.warning(f"⚠️ [OFFLINE][LOGIN] Cloud Auth skipped. Logging in as Offline User: {username}")
            
            # Create Dummy User for Offline Mode
            offline_user = User(
                id=-1,
                username=username,
                full_name="Offline User",
                email="offline@local",
                is_active=True
            )
            # Override role manually if not in constructor
            offline_user.role = "DRIVER"
            
            self._current_user = offline_user
            return True, "Đăng nhập chế độ Offline!", offline_user

        # ONLINE MODE handling via execute_query (Raw SQL)
        try:
            query = "SELECT * FROM users WHERE username = %s LIMIT 1"
            rows = execute_query(query, (username,), fetch=True)
            
            if rows and len(rows) > 0:
                user_data = rows[0]
                # Verify password
                stored_hash = user_data.get('password', '')
                if verify_password(password, stored_hash):
                    if not user_data.get('is_active', True): # Default True if missing
                        return False, "Tài khoản đã bị khóa!", None
                    
                    # Create User Object from Dict
                    # User model uses SQLAlchemy attributes, but we can init with kwargs matching columns
                    current_user = User(**{k: v for k, v in user_data.items() if k in User.__table__.columns.keys()})
                    
                    self._current_user = current_user
                    
                    # [NEW] Auto-Migrate Offline Guest Data
                    try:
                        from src.database.local_db import migrate_guest_alerts
                        # Chuyển quyền sở hữu data từ Guest -> User này
                        migrated_count = migrate_guest_alerts(int(current_user.id))
                        if migrated_count > 0:
                            logger.info(f"🧠 Migrated {migrated_count} offline alerts to user {username} (ID: {current_user.id})")
                    except Exception as me:
                        logger.error(f"Migration failed: {me}")

                    if remember:
                        self.save_credentials(username, password)
                    else:
                        self.clear_saved_credentials()
                        
                    logger.info(f"User logged in: {username}")
                    return True, "Đăng nhập thành công!", current_user
                else:
                    logger.warning(f"Failed login attempt (wrong password) for: {username}")
                    return False, "Sai tên đăng nhập hoặc mật khẩu!", None
            else:
                logger.warning(f"Failed login attempt (user not found): {username}")
                return False, "Sai tên đăng nhập hoặc mật khẩu!", None
                
        except Exception as e:
            logger.error(f"Database error during login: {e}")
            return False, "Lỗi kết nối cơ sở dữ liệu!", None

    def register(self, username: str, password: str, confirm_password: str,
                 full_name: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Handles new user registration using Safe DB Access.
        """
        if get_db().is_offline:
            return False, "Không thể đăng ký khi Offline!"

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

        try:
            # Check if username exists
            check_query = "SELECT id FROM users WHERE username = %s"
            existing = execute_query(check_query, (username,), fetch=True)
            if existing:
                return False, f"Tên đăng nhập '{username}' đã tồn tại!"

            # Insert new user
            hashed_pwd = hash_password(password)
            insert_query = """
                INSERT INTO users (username, password, full_name, email, is_active, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, 1, NOW(), NOW())
            """
            success = get_db().execute_query(insert_query, (
                username, 
                hashed_pwd, 
                full_name.strip() if full_name else None, 
                email.strip() if email else None
            ), fetch=False)
            
            if success:
                logger.info(f"New user registered: {username}")
                return True, "Đăng ký thành công! Vui lòng đăng nhập."
            else:
                 return False, "Lỗi hệ thống khi lưu dữ liệu!"
                 
        except Exception as e:
            logger.error(f"Database error during registration: {e}")
            return False, "Lỗi hệ thống! Vui lòng thử lại sau."

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
        
        if get_db().is_offline:
            return False, "Không thể đổi mật khẩu khi Offline!"

        # Input Validation
        if not old_password or not new_password:
            return False, "Vui lòng nhập đầy đủ thông tin!"
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự!"
        if new_password != confirm_password:
            return False, "Mật khẩu xác nhận không khớp!"
        if old_password == new_password:
            return False, "Mật khẩu mới phải khác mật khẩu cũ!"
        
        try:
            from datetime import datetime
            
            # Verify old password
            query = "SELECT password FROM users WHERE id = %s"
            rows = execute_query(query, (self._current_user.id,), fetch=True)
            if not rows:
                 return False, "Không tìm thấy người dùng!"
            
            stored_hash = rows[0]['password']
            if not verify_password(old_password, stored_hash):
                return False, "Mật khẩu cũ không chính xác!"

            # Update
            new_hash = hash_password(new_password)
            now_local = datetime.now()
            
            update_query = "UPDATE users SET password = %s, updated_at = %s WHERE id = %s"
            get_db().execute_query(update_query, (new_hash, now_local, self._current_user.id))
            
            logger.info(f"Password changed for user: {self._current_user.username}")
            return True, "Đổi mật khẩu thành công!"
        except Exception as e:
            logger.error(f"Database error during password change: {e}")
            return False, "Lỗi hệ thống."

    def update_profile(self, full_name: str, email: str, phone: str = None, avatar_path: str = None) -> Tuple[bool, str]:
        """Updates current user's profile information."""
        if not self._current_user:
            return False, "Chưa đăng nhập!"

        # Input Validation
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()):
            return False, "Email không hợp lệ!"
            
        if get_db().is_offline:
             # Update local object only? 
             # For safety, let's block or just update memory
             self._current_user.full_name = full_name
             self._current_user.email = email
             if phone: self._current_user.phone = phone
             if avatar_path: self._current_user.avatar = avatar_path
             return True, "Cập nhật tạm thời (Offline - Chưa lưu Cloud)!"

        try:
            from datetime import datetime
            now_local = datetime.now()
            
            # Update DB
            query = """
                UPDATE users SET 
                full_name = %s, 
                email = %s, 
                phone = %s,
                avatar = COALESCE(%s, avatar),
                updated_at = %s
                WHERE id = %s
            """
            params = (
                full_name.strip() if full_name else None,
                email.strip() if email else None,
                phone.strip() if phone else None,
                avatar_path,
                now_local,
                self._current_user.id
            )
            get_db().execute_query(query, params)
            
            # Update local memory object
            self._current_user.full_name = full_name
            self._current_user.email = email
            if phone: self._current_user.phone = phone
            if avatar_path: self._current_user.avatar = avatar_path
            
            logger.info(f"Profile updated for user: {self._current_user.username}")
            return True, "Cập nhật thông tin thành công!"
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False, f"Lỗi: {str(e)}"

# --- Singleton Instance ---
auth_controller = AuthController()

def get_auth_controller() -> AuthController:
    """Returns the singleton instance of the AuthController."""
    return auth_controller
