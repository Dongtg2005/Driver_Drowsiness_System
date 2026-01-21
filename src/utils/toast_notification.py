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


class ToastNotification(ctk.CTkFrame):
    """
    Toast Notification widget - Non-blocking notification that appears in corner.
    
    Features:
    - Automatic disappearance after 3 seconds
    - Slide animation (smooth entrance from bottom-right)
    - Different styles (success, warning, danger, info)
    - Can be stacked for multiple notifications
    
    Example:
        toast = ToastNotification(
            master=root,
            message="Đã lưu cài đặt!",
            notification_type="success",
            duration=3000
        )
        toast.show()
    """
    
    # Color scheme for different notification types
    STYLES = {
        "success": {
            "bg_color": "#2D6A4F",      # Dark green
            "fg_color": "#D8F3DC",      # Light green text
            "icon": "✓"
        },
        "danger": {
            "bg_color": "#7D2C2C",      # Dark red
            "fg_color": "#F8D7DA",      # Light red text
            "icon": "✕"
        },
        "warning": {
            "bg_color": "#8B6F47",      # Dark yellow/brown
            "fg_color": "#FFF3CD",      # Light yellow text
            "icon": "⚠"
        },
        "info": {
            "bg_color": "#2C5282",      # Dark blue
            "fg_color": "#D1ECF1",      # Light blue text
            "icon": "ℹ"
        }
    }
    
    def __init__(
        self,
        master: tk.Widget,
        message: str,
        notification_type: Literal["success", "danger", "warning", "info"] = "info",
        duration: int = 3000,
        position: Literal["top-right", "bottom-right", "top-left", "bottom-left"] = "bottom-right",
        width: int = 350,
        height: int = 80,
        on_close: Optional[Callable] = None
    ):
        """
        Initialize Toast Notification.
        
        Args:
            master: Parent widget (usually root window)
            message: Text to display
            notification_type: "success", "danger", "warning", "info"
            duration: How long to show (milliseconds)
            position: Where to display on screen
            width: Toast width in pixels
            height: Toast height in pixels
            on_close: Callback function when toast closes
        """
        super().__init__(master, corner_radius=10, fg_color="#000000")
        
        self.master = master
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self.position = position
        self.width = width
        self.height = height
        self.on_close = on_close
        
        # Get style
        self.style = self.STYLES.get(notification_type, self.STYLES["info"])
        self.configure(fg_color=self.style["bg_color"])
        
        # Animation variables
        self.animation_frame = 0
        self.max_animation_frames = 20  # Number of frames for slide-in animation
        self.is_closing = False
        self.after_id = None  # To track scheduled tasks
        
        # Create content
        self._create_content()
    
    def _create_content(self):
        """Create the internal content of the toast."""
        # Main container with padding
        container = ctk.CTkFrame(self, fg_color=self.style["bg_color"], corner_radius=10)
        container.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Icon and message in horizontal layout
        content_frame = ctk.CTkFrame(container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # Icon on the left
        icon_label = ctk.CTkLabel(
            content_frame,
            text=self.style["icon"],
            font=("Roboto", 20, "bold"),
            text_color=self.style["fg_color"],
            fg_color="transparent"
        )
        icon_label.pack(side="left", padx=(0, 15))
        
        # Message text
        message_label = ctk.CTkLabel(
            content_frame,
            text=self.message,
            font=("Roboto", 13),
            text_color=self.style["fg_color"],
            fg_color="transparent",
            wraplength=250,
            justify="left"
        )
        message_label.pack(side="left", fill="both", expand=True)
        
        # Close button (X) on the right
        close_btn = ctk.CTkButton(
            content_frame,
            text="✕",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color=self.style["fg_color"],
            text_color=self.style["fg_color"],
            font=("Roboto", 12, "bold"),
            command=self.close,
            border_width=0
        )
        close_btn.pack(side="right", padx=(15, 0))
    
    def show(self):
        """
        Display the toast notification with slide-in animation.
        
        This method:
        1. Places the toast on screen
        2. Animates it sliding in from bottom-right
        3. Schedules automatic close after duration
        """
        # Start the animation
        self._animate_in()
        
        # Schedule auto-close after duration
        self.after_id = self.after(self.duration, self.close)
    
    def _animate_in(self):
        """
        Animate the toast sliding in from the bottom-right corner.
        
        How it works:
        1. Calculate final position based on self.position
        2. Start from below the final position (off-screen)
        3. Gradually move upward using place() geometry manager
        4. Stop when reaching final position
        """
        # Get window dimensions for positioning
        self.update_idletasks()  # Update to get accurate dimensions
        
        # Get screen/parent dimensions
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        
        # Fallback for when parent not fully loaded
        if parent_width <= 1:
            parent_width = 1024
        if parent_height <= 1:
            parent_height = 768
        
        # Calculate starting and ending positions based on position parameter
        positions = {
            "bottom-right": {
                "start_x": parent_width - self.width - 20,
                "start_y": parent_height + 100,  # Below screen
                "end_x": parent_width - self.width - 20,
                "end_y": parent_height - self.height - 20
            },
            "bottom-left": {
                "start_x": -100,  # Left of screen
                "start_y": parent_height - self.height - 20,
                "end_x": 20,
                "end_y": parent_height - self.height - 20
            },
            "top-right": {
                "start_x": parent_width - self.width - 20,
                "start_y": -100,  # Above screen
                "end_x": parent_width - self.width - 20,
                "end_y": 20
            },
            "top-left": {
                "start_x": -100,  # Left of screen
                "start_y": 20,
                "end_x": 20,
                "end_y": 20
            }
        }
        
        pos = positions[self.position]
        
        # Calculate interpolation (easing)
        progress = self.animation_frame / self.max_animation_frames
        
        # Use ease-out cubic for smooth deceleration
        eased_progress = 1 - (1 - progress) ** 3
        
        # Interpolate position
        x = pos["start_x"] + (pos["end_x"] - pos["start_x"]) * eased_progress
        y = pos["start_y"] + (pos["end_y"] - pos["start_y"]) * eased_progress
        
        # Place the widget
        self.place(x=int(x), y=int(y), width=self.width, height=self.height)
        
        # Continue animation if not finished
        if self.animation_frame < self.max_animation_frames:
            self.animation_frame += 1
            self.after(15, self._animate_in)  # 15ms per frame = ~60fps
    
    def close(self):
        """
        Close the toast notification with fade-out animation.
        
        This method:
        1. Marks as closing to prevent multiple closes
        2. Gradually reduces opacity
        3. Destroys widget when done
        4. Calls on_close callback if provided
        """
        if self.is_closing:
            return
        
        self.is_closing = True
        
        # Cancel any pending auto-close
        if self.after_id:
            self.after_cancel(self.after_id)
        
        # Simple fade out by reducing widget height to 0
        self._animate_out()
    
    def _animate_out(self, frame: int = 0):
        """
        Animate the toast closing with fade-out effect.
        
        Args:
            frame: Current animation frame
        """
        max_frames = 10
        
        if frame < max_frames:
            # Gradually reduce opacity by decreasing visible height
            progress = frame / max_frames
            current_height = int(self.height * (1 - progress))
            
            # Update height (shrinks)
            if current_height > 0:
                self.place(width=self.width, height=current_height)
            
            self.after(20, lambda: self._animate_out(frame + 1))
        else:
            # Destroy the widget
            self.place_forget()
            self.destroy()
            
            # Call callback if provided
            if self.on_close:
                self.on_close()


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
        position: Literal["top-right", "bottom-right", "top-left", "bottom-left"] = "bottom-right"
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
