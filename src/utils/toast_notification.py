"""
============================================
🔔 Toast Notification System
Driver Drowsiness Detection System
Non-blocking toast messages with animation
============================================
"""

import customtkinter as ctk
import tkinter as tk
from typing import Literal, Callable, Optional
import threading


class ToastNotification(ctk.CTkToplevel):
    """
    Toast Notification widget - Floating Window version.
    """
    
    # ... (STYLES dict remains the same) ...
    STYLES = {
        "success": {"bg_color": "#2D6A4F", "fg_color": "#D8F3DC", "icon": "✓"},
        "danger": {"bg_color": "#7D2C2C", "fg_color": "#F8D7DA", "icon": "✕"},
        "warning": {"bg_color": "#8B6F47", "fg_color": "#FFF3CD", "icon": "⚠"},
        "info": {"bg_color": "#2C5282", "fg_color": "#D1ECF1", "icon": "ℹ"}
    }
    
    def __init__(
        self,
        master: tk.Widget,
        message: str,
        notification_type: Literal["success", "danger", "warning", "info"] = "info",
        duration: int = 3000,
        position: Literal["top-right", "bottom-right", "top-left", "bottom-left", "top-center"] = "top-center",
        width: int = 300, # Reduced width
        height: int = 60, # Reduced height slightly
        on_close: Optional[Callable] = None
    ):
        super().__init__(master)
        
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self.position = position
        self.width = width
        self.height = height
        self.on_close = on_close
        
        # Window configuration
        self.overrideredirect(True) # Remove title bar
        self.attributes("-topmost", True) # Always on top
        self.attributes("-alpha", 0.0) # Start transparent
        
        # Style
        self.style = self.STYLES.get(notification_type, self.STYLES["info"])
        self.configure(fg_color=self.style["bg_color"])
        
        # Animation
        self.animation_frame = 0
        self.max_animation_frames = 20
        self.is_closing = False
        self.after_id = None
        
        self._create_content()
        
    def _create_content(self):
        # Create a frame inside the window to hold content
        self.container = ctk.CTkFrame(self, fg_color=self.style["bg_color"], corner_radius=10)
        self.container.pack(fill="both", expand=True, padx=2, pady=2) # Small padding for border effect if needed
        
        content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Icon
        icon_label = ctk.CTkLabel(
            content_frame, text=self.style["icon"], font=("Roboto", 20, "bold"),
            text_color=self.style["fg_color"]
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        # Message
        message_label = ctk.CTkLabel(
            content_frame, text=self.message, font=("Roboto", 13),
            text_color=self.style["fg_color"], wraplength=230, justify="left"
        )
        message_label.pack(side="left", fill="both", expand=True)
        
        # Close btn
        close_btn = ctk.CTkButton(
            content_frame, text="✕", width=25, height=25,
            fg_color="transparent", hover_color=self.style["fg_color"],
            text_color=self.style["fg_color"], font=("Roboto", 12, "bold"),
            command=self.close
        )
        close_btn.pack(side="right", padx=(5, 0))

    def show(self):
        self._animate_in()
        self.after_id = self.after(self.duration, self.close)

    def _animate_in(self):
        # Get dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Use master geometry if possible to position relative to window
        try:
            parent_x = self.master.winfo_rootx()
            parent_y = self.master.winfo_rooty()
            parent_w = self.master.winfo_width()
            parent_h = self.master.winfo_height()
        except:
            # Fallback to screen coordinates
            parent_x, parent_y = 0, 0
            parent_w, parent_h = screen_width, screen_height

        # Calculate target positions
        pad = 20
        if self.position == "top-center":
            target_x = parent_x + (parent_w - self.width) // 2
            target_y = parent_y + pad + 20 # A bit lower
            start_y = parent_y - self.height
        elif self.position == "top-right":
            target_x = parent_x + parent_w - self.width - pad
            target_y = parent_y + pad
            start_y = parent_y - self.height 
        elif self.position == "bottom-right":
            target_x = parent_x + parent_w - self.width - pad
            target_y = parent_y + parent_h - self.height - pad
            start_y = parent_y + parent_h + self.height 
        else:
             target_x = parent_x + parent_w - self.width - pad
             target_y = parent_y + pad
             start_y = parent_y - self.height

        # Animation logic: Interpolate Y and Alpha
        progress = self.animation_frame / self.max_animation_frames
        eased_progress = 1 - (1 - progress) ** 3
        
        current_y = start_y + (target_y - start_y) * eased_progress
        
        # Update Geometry
        self.geometry(f"{self.width}x{self.height}+{int(target_x)}+{int(current_y)}")
        self.attributes("-alpha", min(1.0, progress * 1.5)) # Fade in
        
        if self.animation_frame < self.max_animation_frames:
            self.animation_frame += 1
            self.after(16, self._animate_in)
        else:
             # Ensure final position
             self.geometry(f"{self.width}x{self.height}+{int(target_x)}+{int(target_y)}")
             self.attributes("-alpha", 1.0)

    def close(self):
        if self.is_closing: return
        self.is_closing = True
        if self.after_id: self.after_cancel(self.after_id)
        self._animate_out()

    def _animate_out(self, frame=0):
        max_frames = 15
        if frame < max_frames:
            alpha = 1.0 - (frame / max_frames)
            self.attributes("-alpha", alpha)
            self.after(16, lambda: self._animate_out(frame + 1))
        else:
            self.destroy()
            if self.on_close: self.on_close()


class ToastContainer:
    """
    Container to manage multiple toast notifications.
    
    Handles stacking toasts vertically so they don't overlap.
    
    Example:
        container = ToastContainer(root)
        container.show_toast("Đã lưu!", "success")
        container.show_toast("Lỗi kết nối", "danger")
    """
    
    def __init__(self, master: tk.Widget, max_toasts: int = 5):
        """
        Initialize ToastContainer.
        
        Args:
            master: Parent widget (usually root window)
            max_toasts: Maximum number of visible toasts
        """
        self.master = master
        self.max_toasts = max_toasts
        self.toasts = []
    
    def show_toast(
        self,
        message: str,
        notification_type: Literal["success", "danger", "warning", "info"] = "info",
        duration: int = 3000,
        position: Literal["top-right", "bottom-right", "top-left", "bottom-left", "top-center"] = "top-center"
    ):
        """
        Show a toast notification, removing old ones if necessary.
        
        Args:
            message: Text to display
            notification_type: Type of notification
            duration: How long to show (ms)
            position: Position on screen
        """
        # Remove old toasts if exceeding max
        while len(self.toasts) >= self.max_toasts:
            old_toast = self.toasts.pop(0)
            if old_toast.winfo_exists():
                old_toast.close()
        
        # Create and show new toast
        toast = ToastNotification(
            master=self.master,
            message=message,
            notification_type=notification_type,
            duration=duration,
            position=position,
            on_close=lambda: self._remove_toast(toast)
        )
        
        self.toasts.append(toast)
        toast.show()
    
    def _remove_toast(self, toast: ToastNotification):
        """Remove a closed toast from tracking."""
        if toast in self.toasts:
            self.toasts.remove(toast)
    
    def clear_all(self):
        """Close all visible toasts."""
        for toast in self.toasts[:]:  # Create a copy to iterate
            if toast.winfo_exists():
                toast.close()
