"""
============================================
🎨 UI Components (Final Full Version)
Driver Drowsiness Detection System
Custom styled widgets (Button, Entry, Switch, Slider, Spinner...)
============================================
"""

import customtkinter as ctk
import tkinter as tk
from typing import Callable, Optional
import sys
import os
from tkinter import messagebox

# Add parent directory to path to import constants
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.constants import Colors, UIConstants

class StyledFrame(ctk.CTkFrame):
    """Custom Frame with card style"""
    def __init__(self, master, style="card", **kwargs):
        color = Colors.BG_CARD if style == "card" else "transparent"
        super().__init__(master, fg_color=color, corner_radius=15, **kwargs)

class StyledLabel(ctk.CTkLabel):
    """Custom Label with preset styles"""
    def __init__(self, master, style="normal", size=14, text_color=None, **kwargs):
        font_weight = "bold" if style in ["title", "subtitle"] else "normal"
        
        if style == "title":
            real_size = 24
            def_color = Colors.TEXT_PRIMARY
        elif style == "subtitle":
            real_size = 16
            def_color = Colors.TEXT_SECONDARY
        elif style == "danger":
            real_size = size
            def_color = Colors.DANGER
        elif style == "muted":
            real_size = 12
            def_color = Colors.TEXT_MUTED
        else:
            real_size = size
            def_color = Colors.TEXT_PRIMARY
            
        color = text_color if text_color else def_color
        
        super().__init__(
            master, 
            font=("Roboto", real_size, font_weight), 
            text_color=color, 
            **kwargs
        )

class StyledButton(ctk.CTkButton):
    """Custom Button"""
    def __init__(self, master, style="primary", **kwargs):
        colors = {
            "primary": Colors.PRIMARY,
            "success": Colors.SUCCESS,
            "danger": Colors.DANGER,
            "warning": Colors.WARNING_HEX if hasattr(Colors, 'WARNING_HEX') else "#E9B604",
            "secondary": "#6C757D",
            "info": Colors.INFO if hasattr(Colors, 'INFO') else "#0DCAF0"
        }
        fg_color = colors.get(style, Colors.PRIMARY)
        
        # Remove height from kwargs if present to avoid duplicate
        height = kwargs.pop('height', 40)
        
        super().__init__(
            master, 
            fg_color=fg_color, 
            corner_radius=8, 
            height=height,
            font=("Roboto", 14, "bold"), 
            **kwargs
        )

class StyledEntry(ctk.CTkEntry):
    """Custom Entry"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=40,
            corner_radius=8,
            border_width=1,
            fg_color=Colors.BG_DARK,
            border_color=Colors.TEXT_MUTED,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_MUTED,
            **kwargs
        )

class StyledSwitch(ctk.CTkSwitch):
    """Custom Switch"""
    def __init__(self, master, default=False, **kwargs):
        super().__init__(
            master,
            progress_color=Colors.SUCCESS,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.TEXT_MUTED,
            **kwargs
        )
        # Set default value after initialization
        if default:
            self.select()
        else:
            self.deselect()

class StyledSlider(ctk.CTkSlider):
    """Custom Slider"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            progress_color=Colors.PRIMARY,
            button_color=Colors.PRIMARY,
            button_hover_color=Colors.SUCCESS,
            fg_color=Colors.BG_DARK,
            **kwargs
        )

class StyledOptionMenu(ctk.CTkOptionMenu):
    """Custom Dropdown"""
    def __init__(self, master, default=None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_DARK,
            button_color=Colors.PRIMARY,
            button_hover_color=Colors.SUCCESS,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_fg_color=Colors.BG_CARD,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            **kwargs
        )
        # Set default value after initialization
        if default is not None:
            self.set(default)

class LoadingSpinner(ctk.CTkCanvas):
    """Custom Loading Spinner Animation"""
    def __init__(self, master, size=30, color=Colors.PRIMARY, **kwargs):
        # Canvas background must match parent to look transparent
        bg_color = kwargs.pop("bg_color", Colors.BG_DARK) 
        super().__init__(master, width=size, height=size, highlightthickness=0, bg=bg_color, **kwargs)
        self.size = size
        self.color = color
        self.angle = 0
        self.is_running = False
        self.arc = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.pack(pady=10)
            self._animate()

    def stop(self):
        self.is_running = False
        self.pack_forget()

    def _animate(self):
        if not self.is_running: return
        self.delete("all")
        w = self.size
        # Draw rotating arc
        start = self.angle
        extent = 120
        self.create_arc(2, 2, w-2, w-2, start=start, extent=extent, style="arc", width=3, outline=self.color)
        self.angle = (self.angle - 15) % 360
        self.after(20, self._animate)

class MessageBox:
    @staticmethod
    def show_success(master, title, message):
        messagebox.showinfo(title, message)
    
    @staticmethod
    def show_error(master, title, message):
        messagebox.showerror(title, message)
        
    @staticmethod
    def ask_yes_no(master, title, message):
        return messagebox.askyesno(title, message)

class StatusBar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, height=30, fg_color=Colors.BG_CARD)
        self.label = ctk.CTkLabel(self, text="Ready", text_color=Colors.TEXT_SECONDARY, font=("Roboto", 12))
        self.label.pack(side="left", padx=10)
        self.fps_label = ctk.CTkLabel(self, text="FPS: 0", text_color=Colors.TEXT_MUTED, font=("Roboto", 12))
        self.fps_label.pack(side="right", padx=10)

    def set_status(self, text):
        self.label.configure(text=text)
    
    def set_fps(self, fps):
        self.fps_label.configure(text=f"FPS: {int(fps)}")

class SideMenu(ctk.CTkFrame):
    def __init__(self, master, command=None):
        super().__init__(master, width=200, corner_radius=0, fg_color=Colors.BG_CARD)
        self.command = command
        
        self.logo_label = ctk.CTkLabel(self, text="DRIVER\nGUARD AI", font=("Roboto", 20, "bold"), text_color=Colors.PRIMARY)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        self.btn_camera = self._create_menu_btn("📷 Camera Monitoring", "camera", 1)
        self.btn_dash = self._create_menu_btn("📊 Dashboard", "dashboard", 2)
        self.btn_settings = self._create_menu_btn("⚙️ Settings", "settings", 3)
        
        self.grid_rowconfigure(4, weight=1)
        self.btn_logout = self._create_menu_btn("🚪 Logout", "logout", 5, fg_color=Colors.DANGER)

    def _create_menu_btn(self, text, value, row, fg_color="transparent"):
        btn = ctk.CTkButton(
            self, text=text, fg_color=fg_color, anchor="w", height=45, font=("Roboto", 14),
            command=lambda: self.command(value) if self.command else None
        )
        btn.grid(row=row, column=0, sticky="ew", padx=20, pady=5)
        return btn