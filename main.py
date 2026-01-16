"""
============================================
🚗 DRIVER DROWSINESS DETECTION SYSTEM
============================================
Main Application Entry Point (Final Version)
"""

import customtkinter as ctk
import sys
import os
from typing import Optional, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config
from config import config

# Import utils
# [FIX 1] Import đúng tên 'logger' từ file logger.py
from src.utils.logger import logger as app_logger
from src.utils.audio_manager import audio_manager

# Import views
from src.views.login_view import LoginView
from src.views.register_view import RegisterView
from src.views.camera_view import CameraView
from src.views.dashboard_view import DashboardView
from src.views.settings_view import SettingsView
from src.views.calibration_view import CalibrationView
from src.views.components import Colors, MessageBox

class DriverDrowsinessApp:
    """Main Application Class"""
    
    def __init__(self):
        """Initialize the application"""
        # [FIX 2] Dùng .info() thay vì .log_info()
        app_logger.info("="*50)
        app_logger.info("Starting Driver Drowsiness Detection System")
        app_logger.info("="*50)
        
        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("🚗 Driver Drowsiness Detection System")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.minsize(1024, 768)
        # Ensure a Unicode font that supports Vietnamese is used
        try:
            # Prefer Segoe UI on Windows, fallback to Arial
            self.root.option_add("*Font", ("Segoe UI", 12))
        except Exception:
            try:
                self.root.option_add("*Font", ("Arial", 12))
            except Exception:
                pass
        
        # Set window icon (if available)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # Configure window
        self.root.configure(fg_color=Colors.BG_DARK)
        
        # Application state
        self.current_user: Optional[Dict] = None
        self.current_view: Optional[ctk.CTkFrame] = None
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Show login view
        self._show_login()
    
    def run(self):
        """Start the application"""
        app_logger.info("Application started")
        self.root.mainloop()
    
    def _clear_view(self):
        """Clear current view"""
        if self.current_view:
            # Gọi cleanup nếu view đó có hỗ trợ (ví dụ CameraView cần tắt cam)
            if hasattr(self.current_view, 'cleanup'):
                self.current_view.cleanup()
            self.current_view.destroy()
            self.current_view = None
    
    def _show_login(self):
        """Show login view"""
        self._clear_view()
        
        self.current_view = LoginView(
            self.root,
            on_login_success=self._on_login_success,
            on_register_click=self._show_register
        )
        self.current_view.pack(fill="both", expand=True)
        
        app_logger.info("Showing login view")
    
    def _show_register(self):
        """Show register view"""
        self._clear_view()
        
        self.current_view = RegisterView(
            self.root,
            on_register_success=self._on_register_success,
            # [FIX 3] Sửa tên tham số thành on_back_to_login cho khớp RegisterView
            on_back_to_login=self._show_login
        )
        self.current_view.pack(fill="both", expand=True)
        
        app_logger.info("Showing register view")
    
    def _show_camera(self):
        """Show camera monitoring view"""
        self._clear_view()
        
        self.current_view = CameraView(
            self.root,
            user_data=self.current_user,
            on_dashboard=self._show_dashboard,
            on_settings=self._show_settings,
            on_logout=self._on_logout
        )
        self.current_view.pack(fill="both", expand=True)
        
        app_logger.info("Showing camera view")
    
    def _show_dashboard(self):
        """Show dashboard view"""
        self._clear_view()
        
        self.current_view = DashboardView(
            self.root,
            user_data=self.current_user,
            on_back=self._show_camera
        )
        self.current_view.pack(fill="both", expand=True)
        
        app_logger.info("Showing dashboard view")
    
    def _show_settings(self):
        """Show settings view"""
        self._clear_view()
        
        self.current_view = SettingsView(
            self.root,
            user_data=self.current_user,
            on_back=self._show_camera
        )
        self.current_view.pack(fill="both", expand=True)
        
        app_logger.info("Showing settings view")
    
    def _on_login_success(self, user_data: Dict):
        """Handle successful login"""
        self.current_user = user_data
        app_logger.info(f"User logged in: {user_data.get('username')}")
        # After login, require calibration before starting monitoring
        self._show_calibration()

    def _show_calibration(self):
        """Show calibration view before allowing monitoring/dashboard."""
        self._clear_view()

        user_id = None
        try:
            user_id = int(self.current_user.get('id'))
        except Exception:
            user_id = 1

        self.current_view = CalibrationView(
            self.root,
            on_finish=self._after_calibration,
            user_id=user_id
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing calibration view")

    def _after_calibration(self):
        """Called after calibration completes — proceed to camera view."""
        app_logger.info("Calibration finished; entering camera view")
        self._show_camera()
    
    def _on_register_success(self): 
        # [FIX 4] Bỏ tham số user_data vì đăng ký xong cần đăng nhập lại
        """Handle successful registration"""
        app_logger.info("New user registered successfully")
        
        # Show success message not needed here if RegisterView already showed it, 
        # but let's keep logic simple: just switch to login
        self._show_login()
    
    def _on_logout(self):
        """Handle logout"""
        if self.current_user:
            app_logger.info(f"User logged out: {self.current_user.get('username')}")
        
        self.current_user = None
        
        # Stop audio
        audio_manager.stop()
        
        # Show login
        self._show_login()
    
    def _on_close(self):
        """Handle window close"""
        app_logger.info("Application closing...")
        
        # Cleanup current view
        if self.current_view and hasattr(self.current_view, 'cleanup'):
            self.current_view.cleanup()

        # Stop audio manager
        audio_manager.stop()
        audio_manager.cleanup()
        
        # Destroy window
        self.root.destroy()
        sys.exit(0)


def main():
    """Main entry point"""
    try:
        # Print startup banner
        print("="*50)
        print("🚗 DRIVER DROWSINESS DETECTION SYSTEM")
        print("="*50)
        print(f"Python Version: {sys.version}")
        print(f"Working Directory: {os.getcwd()}")
        print("="*50)
        
        # Create and run app
        app = DriverDrowsinessApp()
        app.run()
        
    except Exception as e:
        # [FIX 5] Dùng .error() cho khớp
        try:
            from src.utils.logger import logger
            logger.error(f"Fatal error: {e}")
        except:
            pass
            
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()