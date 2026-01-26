"""
======================================================
🚗 DRIVER DROWSINESS DETECTION SYSTEM (SQLAlchemy Version)
======================================================
Main Application Entry Point
"""

import customtkinter as ctk
import sys
import os
import threading
import warnings
from typing import Optional

# Suppress the protobuf SymbolDatabase.GetPrototype() deprecation warning
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")
from PIL import Image
import pystray
from pystray import MenuItem as item

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config
from config import config

# Import utils
from src.utils.logger import logger as app_logger
from src.utils.audio_manager import audio_manager

# Import models for type hinting
from src.models.user_model import User

# Import views
from src.views.account_view import AccountView  # [NEW]
from src.views.login_view import LoginView
from src.views.register_view import RegisterView
from src.views.camera_view import CameraView
from src.views.dashboard_view import DashboardView
from src.views.settings_view import SettingsView
from src.views.calibration_view import CalibrationView
from src.views.components import Colors, MessageBox

    # ... existing methods ...



class DriverDrowsinessApp:
    """Main Application Class"""
    
    def __init__(self):
        """Initialize the application"""
        app_logger.info("="*50)
        app_logger.info("Starting Driver Drowsiness Detection System")
        app_logger.info("="*50)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
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
        
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        self.root.configure(fg_color=Colors.BG_DARK)
        
        # --- Application state updated to use User object ---
        self.current_user: Optional[User] = None
        self.current_view: Optional[ctk.CTkFrame] = None
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._show_login()
    
    def run(self):
        """Start the application"""
        app_logger.info("Application started")
        self.root.mainloop()
    
    def _clear_view(self):
        """Clear current view and call cleanup if it exists"""
        if self.current_view:
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
            on_back_to_login=self._show_login
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing register view")
    
    # --- All views now receive the User object ---
    def _show_camera(self):
        """Show camera monitoring view"""
        self._clear_view()
        self.current_view = CameraView(
            self.root,
            user=self.current_user,
            on_dashboard=self._show_dashboard,
            on_settings=self._show_settings,
            on_logout=self._on_logout,
            on_account=self._show_account
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing camera view")
    
    def _show_dashboard(self):
        """Show dashboard view"""
        self._clear_view()
        self.current_view = DashboardView(
            self.root,
            user=self.current_user,
            on_back=self._show_camera
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing dashboard view")
    
    def _show_settings(self):
        """Show settings view"""
        self._clear_view()
        self.current_view = SettingsView(
            self.root,
            user=self.current_user,
            on_back=self._show_camera,
            on_account=self._show_account,
            on_logout=self._on_logout  # [NEW] Pass callback for password change
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing settings view")

    def _show_account(self):
        """Show account management view"""
        self._clear_view()
        self.current_view = AccountView(
            self.root,
            user=self.current_user,
            on_back=self._show_camera
        )
        self.current_view.pack(fill="both", expand=True)
        app_logger.info("Showing account view")
    
    # --- Handler updated to use User object ---
    def _on_login_success(self, user_object: User):
        """Handle successful login"""
        self.current_user = user_object
        app_logger.info(f"User logged in: {self.current_user.username} (ID: {self.current_user.id})")
        # After login, require calibration before starting monitoring
        self._show_calibration()

    def _show_calibration(self):
        """Show calibration view before allowing monitoring/dashboard."""
        self._clear_view()

        user_id = None
        try:
            # Use object attribute access
            user_id = int(self.current_user.id)
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
        """Handle successful registration"""
        app_logger.info("New user registered successfully, switching to login view.")
        self._show_login()
    
    def _on_logout(self):
        """Handle logout"""
        if self.current_user:
            app_logger.info(f"User logged out: {self.current_user.username}")
        self.current_user = None
        audio_manager.stop()
        self._show_login()
    
    def _create_image(self):
        """Create an image for the tray icon"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except Exception:
            pass
            
        # Create a basic image if icon doesn't exist or fails to load
        width = 64
        height = 64
        color1 = (52, 152, 219) # Blue
        color2 = (255, 255, 255) # White
        image = Image.new('RGB', (width, height), color1)
        # Draw a simple rectangle/symbol
        for x in range(width):
            for y in range(height):
                if 20 < x < 44 and 20 < y < 44:
                    image.putpixel((x, y), color2)
        return image

    def _minimize_to_tray(self):
        """Hide window and create system tray icon"""
        self.root.withdraw()
        
        image = self._create_image()
        menu = (
            item('Restored', self._show_window, default=True),
            item('Quit', self._quit_app_from_tray)
        )
        self.tray_icon = pystray.Icon("driver_drowsiness_system", image, "Driver Drowsiness System", menu)
        
        # Run tray icon in a separate thread so it doesn't block Tkinter
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        app_logger.info("Application minimized to system tray")

    def _show_window(self, icon, item):
        """Show the window again"""
        self.tray_icon.stop()
        self.root.after(0, self.root.deiconify)
        app_logger.info("Application restored from system tray")

    def _quit_app_from_tray(self, icon, item):
        """Quit application from tray"""
        # 1. Ngắt kết nối sự kiện đóng cửa sổ ngay lập tức để ngăn vòng lặp
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # 2. Dừng icon
        self.tray_icon.stop()
        
        # 3. Thực hiện thoát hoàn toàn
        def force_exit():
            try:
                # Đợi rất ngắn để menu kịp đóng
                time.sleep(0.1)
                app_logger.info("Exiting application from tray...")
                
                # Cleanup tài nguyên
                try:
                    audio_manager.stop()
                    audio_manager.cleanup()
                    if self.current_view and hasattr(self.current_view, 'cleanup'):
                        self.current_view.cleanup()
                except: 
                    pass
                
                # Hủy cửa sổ Tkinter (nếu còn)
                try:
                    self.root.quit() 
                except:
                    pass

                # Tắt nóng tiến trình
                os._exit(0)
            except:
                os._exit(0)

        threading.Thread(target=force_exit, daemon=True).start()

    def _perform_exit(self):
        """Perform actual exit cleanup"""
        app_logger.info("Application closing...")
        try:
            # Ngừng âm thanh và camera trước
            audio_manager.stop()
            if self.current_view and hasattr(self.current_view, 'cleanup'):
                self.current_view.cleanup()
            
            # Hủy GUI
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        finally:
            # Buộc tắt chương trình và Hủy mọi luồng (Thread)
            os._exit(0)
    
    def _on_close(self):
        """Handle window close - direct exit per user request"""
        # Thoát
        self._perform_exit()

def main():
    """Main entry point"""
    try:
        print("="*50)
        print("🚗 DRIVER DROWSINESS DETECTION SYSTEM")
        print("="*50)
        app = DriverDrowsinessApp()
        app.run()
    except Exception as e:
        try:
            from src.utils.logger import logger
            logger.error(f"Fatal error: {e}")
            # logger.error(traceback.format_exc()) # Optional: log traceback manually if needed
        except ImportError:
            pass
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()