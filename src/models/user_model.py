"""
============================================
👤 User Model
Driver Drowsiness Detection System
User data operations (CRUD)
============================================
"""

import bcrypt
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db_connection import db, execute_query


class UserModel:
    """
    Model class for user-related database operations.
    Handles authentication, registration, and profile management.
    """
    
    def __init__(self):
        """Initialize user model"""
        self._current_user: Optional[Dict] = None
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed: Stored hash
            
        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with username and password.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            User data dict if authenticated, None otherwise
        """
        query = """
            SELECT id, username, password, full_name, email, phone, avatar, 
                   is_active, created_at, last_login
            FROM users 
            WHERE username = %s AND is_active = TRUE
        """
        
        result = execute_query(query, (username,), fetch=True)
        
        if not result:
            return None
        
        user = result[0]
        
        # Verify password
        if not self.verify_password(password, user['password']):
            return None
        
        # Update last login
        self._update_last_login(user['id'])
        
        # Remove password from returned data
        del user['password']
        
        self._current_user = user
        return user
    
    def _update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = NOW() WHERE id = %s"
        execute_query(query, (user_id,))
    
    def register(self, username: str, password: str, 
                 full_name: str = None, email: str = None) -> Optional[int]:
        """
        Register a new user.
        
        Args:
            username: Desired username
            password: Plain text password
            full_name: User's full name
            email: User's email
            
        Returns:
            New user ID if successful, None otherwise
        """
        # Check if username exists
        if self.get_by_username(username):
            return None
        
        # Hash password
        hashed_password = self.hash_password(password)
        
        # Insert new user
        query = """
            INSERT INTO users (username, password, full_name, email)
            VALUES (%s, %s, %s, %s)
        """
        
        result = execute_query(query, (username, hashed_password, full_name, email))
        
        if result:
            # Create default settings for new user
            self._create_default_settings(result)
            return result
        
        return None
    
    def _create_default_settings(self, user_id: int) -> None:
        """Create default settings for new user"""
        query = "INSERT INTO user_settings (user_id) VALUES (%s)"
        execute_query(query, (user_id,))
    
    def get_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data dict or None
        """
        query = """
            SELECT id, username, full_name, email, phone, avatar,
                   is_active, created_at, last_login
            FROM users 
            WHERE id = %s
        """
        
        result = execute_query(query, (user_id,), fetch=True)
        return result[0] if result else None
    
    def get_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User data dict or None
        """
        query = """
            SELECT id, username, full_name, email, phone, avatar,
                   is_active, created_at, last_login
            FROM users 
            WHERE username = %s
        """
        
        result = execute_query(query, (username,), fetch=True)
        return result[0] if result else None
    
    def update_profile(self, user_id: int, **kwargs) -> bool:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update (full_name, email, phone, avatar)
            
        Returns:
            True if successful
        """
        allowed_fields = ['full_name', 'email', 'phone', 'avatar']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        query = f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE id = %s"
        
        params = list(updates.values()) + [user_id]
        result = execute_query(query, tuple(params))
        
        return result is not None
    
    def change_password(self, user_id: int, old_password: str, 
                        new_password: str) -> bool:
        """
        Change user's password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful
        """
        # Get current password hash
        query = "SELECT password FROM users WHERE id = %s"
        result = execute_query(query, (user_id,), fetch=True)
        
        if not result:
            return False
        
        # Verify old password
        if not self.verify_password(old_password, result[0]['password']):
            return False
        
        # Update password
        new_hash = self.hash_password(new_password)
        update_query = "UPDATE users SET password = %s, updated_at = NOW() WHERE id = %s"
        
        return execute_query(update_query, (new_hash, user_id)) is not None
    
    def get_user_settings(self, user_id: int) -> Optional[Dict]:
        """
        Get user's settings.
        
        Args:
            user_id: User ID
            
        Returns:
            Settings dict or None
        """
        query = """
            SELECT ear_threshold, mar_threshold, head_threshold,
                   alert_volume, sensitivity_level, enable_sound, enable_vibration
            FROM user_settings
            WHERE user_id = %s
        """
        
        result = execute_query(query, (user_id,), fetch=True)
        return result[0] if result else None
    
    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """
        Update user's settings.
        
        Args:
            user_id: User ID
            **kwargs: Settings to update
            
        Returns:
            True if successful
        """
        allowed_fields = ['ear_threshold', 'mar_threshold', 'head_threshold',
                         'alert_volume', 'sensitivity_level', 'enable_sound', 
                         'enable_vibration']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        query = f"UPDATE user_settings SET {set_clause}, updated_at = NOW() WHERE user_id = %s"
        
        params = list(updates.values()) + [user_id]
        result = execute_query(query, tuple(params))
        
        return result is not None
    
    def get_current_user(self) -> Optional[Dict]:
        """Get currently logged in user"""
        return self._current_user
    
    def set_current_user(self, user: Dict) -> None:
        """Set current user"""
        self._current_user = user
    
    def logout(self) -> None:
        """Clear current user"""
        self._current_user = None
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user (soft delete by deactivating).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        query = "UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s"
        result = execute_query(query, (user_id,))
        return result is not None


# Create singleton instance
user_model = UserModel()


def get_user_model() -> UserModel:
    """Get user model instance"""
    return user_model


if __name__ == "__main__":
    print("User Model Test")
    
    # Test password hashing
    password = "test123"
    hashed = UserModel.hash_password(password)
    print(f"Password: {password}")
    print(f"Hashed: {hashed}")
    print(f"Verify: {UserModel.verify_password(password, hashed)}")
    print(f"Wrong password verify: {UserModel.verify_password('wrong', hashed)}")
