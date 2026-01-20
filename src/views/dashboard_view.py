"""
======================================================
📊 Dashboard View (SQLAlchemy Version)
Driver Drowsiness Detection System
Statistics and reports screen
======================================================
"""

import customtkinter as ctk
from typing import Callable, Optional, List
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame,
    StyledOptionMenu
)
from src.models.user_model import User
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession
from src.controllers import stats_controller # Import the new controller
from src.database.connection import SessionLocal

class DashboardView(ctk.CTkFrame):
    """Dashboard view for statistics and reports"""
    
    def __init__(self, master, user: Optional[User] = None,
                 on_back: Optional[Callable] = None):
        """
        Create dashboard view.
        
        Args:
            master: Parent widget
            user: The logged-in User object
            on_back: Callback to go back
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user = user
        self.on_back = on_back

        self._create_widgets()
        # Use after() to ensure the main window is fully loaded before DB access
        self.after(100, self._load_data)
    
    def _create_widgets(self):
        """Create all widgets"""
        self._create_header()
        main_frame = StyledFrame(self, style="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._create_stats_panel(main_frame)
        self._create_history_panel(main_frame)
    
    def _create_header(self):
        """Create header bar"""
        header = StyledFrame(self, style="card")
        header.pack(fill="x", padx=10, pady=10)
        
        StyledButton(
            header, text="← Quay lại", command=self.on_back,
            style="secondary", width=100, height=35
        ).pack(side="left", padx=10)
        
        StyledLabel(header, text="📊 Báo cáo & Thống kê", style="title", size=18).pack(side="left", padx=20)
        
        filter_frame = StyledFrame(header, style="transparent")
        filter_frame.pack(side="right", padx=10)
        
        StyledLabel(filter_frame, text="Thời gian:", style="normal").pack(side="left", padx=5)
        
        self.date_filter = StyledOptionMenu(
            filter_frame, values=["Hôm nay", "7 ngày", "30 ngày", "Tất cả"],
            default="Hôm nay", command=lambda _: self._load_data(), width=120
        )
        self.date_filter.pack(side="left", padx=5)
        
        StyledButton(
            filter_frame, text="🔄 Làm mới", command=self._load_data,
            style="info", width=100, height=35
        ).pack(side="left", padx=5)
    
    def _create_stats_panel(self, parent):
        """Create statistics panel"""
        stats_frame = StyledFrame(parent, style="card")
        stats_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        StyledLabel(stats_frame, text="📈 Tổng quan", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        
        cards_frame = StyledFrame(stats_frame, style="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)
        
        row1 = StyledFrame(cards_frame, style="transparent")
        row1.pack(fill="x", pady=5)
        self.total_alerts_card = self._create_stat_card(row1, "🚨 Tổng cảnh báo", "0", Colors.DANGER)
        self.total_alerts_card.pack(side="left", fill="x", expand=True, padx=5)
        self.drowsy_card = self._create_stat_card(row1, "😴 Buồn ngủ", "0", Colors.WARNING)
        self.drowsy_card.pack(side="left", fill="x", expand=True, padx=5)
        
        row2 = StyledFrame(cards_frame, style="transparent")
        row2.pack(fill="x", pady=5)
        self.yawn_card = self._create_stat_card(row2, "🥱 Ngáp", "0", Colors.INFO)
        self.yawn_card.pack(side="left", fill="x", expand=True, padx=5)
        self.head_down_card = self._create_stat_card(row2, "⬇️ Cúi đầu", "0", Colors.PRIMARY)
        self.head_down_card.pack(side="left", fill="x", expand=True, padx=5)
        
        # Chart section will be updated in _update_chart
        chart_section = StyledFrame(stats_frame, style="transparent")
        chart_section.pack(fill="both", expand=True, padx=20, pady=10)
        StyledLabel(chart_section, text="📅 Thống kê 7 ngày gần nhất", style="title", size=14).pack(anchor="w", pady=(10, 5))
        self.chart_canvas = ctk.CTkCanvas(chart_section, bg=Colors.BG_CARD, highlightthickness=0, height=200)
        self.chart_canvas.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_history_panel(self, parent):
        """Create history panel"""
        history_frame = StyledFrame(parent, style="card")
        history_frame.pack(side="right", fill="both", padx=(10, 0), ipadx=10)

        StyledLabel(history_frame, text="📜 Lịch sử cảnh báo", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        self.history_list = ctk.CTkScrollableFrame(history_frame, fg_color=Colors.BG_INPUT, corner_radius=10, width=350)
        self.history_list.pack(fill="both", expand=True, padx=20, pady=10)

        StyledLabel(history_frame, text="🚗 Phiên lái xe gần đây", style="title", size=14).pack(anchor="w", padx=20, pady=(15, 5))
        self.sessions_list = ctk.CTkScrollableFrame(history_frame, fg_color=Colors.BG_INPUT, corner_radius=10, width=350, height=150)
        self.sessions_list.pack(fill="x", padx=20, pady=(5, 15))

    def _load_data(self):
        """Load data from the database using the stats_controller."""
        if not self.user:
            return

        db = SessionLocal()
        try:
            filter_value = self.date_filter.get()
            end_date = datetime.now()
            
            if filter_value == "Hôm nay":
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif filter_value == "7 ngày":
                start_date = end_date - timedelta(days=7)
            elif filter_value == "30 ngày":
                start_date = end_date - timedelta(days=30)
            else: # "Tất cả"
                start_date = end_date - timedelta(days=3650) # A long time ago

            stats = stats_controller.get_aggregated_stats(db, self.user.id, start_date, end_date)
            alerts = stats_controller.get_alerts_by_date_range(db, self.user.id, start_date, end_date)
            
            self._update_stats(stats)
            self._update_history(alerts)
            
            # Chart and sessions are loaded separately
            weekly_stats = stats_controller.get_weekly_statistics(db, self.user.id)
            self._update_chart(weekly_stats)

            sessions = stats_controller.get_session_history(db, self.user.id, limit=10)
            self._load_sessions(sessions)
        finally:
            db.close()

    def _update_stats(self, stats: dict):
        """Update statistics cards from a dictionary."""
        self.total_alerts_card.value_label.configure(text=str(stats.get('total_alerts', 0)))
        self.drowsy_card.value_label.configure(text=str(stats.get('drowsy_count', 0)))
        self.yawn_card.value_label.configure(text=str(stats.get('yawn_count', 0)))
        self.head_down_card.value_label.configure(text=str(stats.get('head_down_count', 0)))

    def _update_history(self, alerts: List[AlertHistory]):
        """Update history list from a list of AlertHistory objects."""
        for widget in self.history_list.winfo_children():
            widget.destroy()
        
        if not alerts:
            StyledLabel(self.history_list, text="Không có dữ liệu", style="muted").pack(pady=20)
            return
        
        for alert in alerts[:20]: # Show last 20 alerts
            self._create_alert_item(alert)

    def _create_alert_item(self, alert: AlertHistory):
        """Create an alert history item from an AlertHistory object."""
        frame = StyledFrame(self.history_list, style="transparent")
        frame.pack(fill="x", pady=2)

        type_icons = {'DROWSY': '😴', 'YAWN': '🥱', 'HEAD_DOWN': '⬇️'}
        icon = type_icons.get(alert.alert_type, '⚠️')
        
        level_colors = {1: Colors.WARNING, 2: Colors.DANGER, 3: Colors.DANGER}
        color = level_colors.get(alert.alert_level, Colors.WARNING)
        
        time_str = alert.timestamp.strftime("%d/%m %H:%M:%S")
        
        StyledLabel(frame, text=f"{icon} {time_str}", style="normal", size=12).pack(side="left")
        level_label = StyledLabel(frame, text=f"Lv.{alert.alert_level}", size=11, text_color=color)
        level_label.pack(side="right")

    def _update_chart(self, weekly_stats: List[dict]):
        """Update the weekly chart from a list of daily stats."""
        self.chart_canvas.delete("all")
        self.chart_canvas.update()
        width, height = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
        if width < 100 or height < 100: return

        padding = 40
        bar_width = (width - 2 * padding) / 7 - 10
        max_value = max([s['total_alerts'] for s in weekly_stats] + [1])
        
        for i, stats in enumerate(reversed(weekly_stats)):
            value = stats['total_alerts']
            bar_height = (value / max_value) * (height - 2 * padding) if max_value > 0 else 0
            x, y = padding + i * (bar_width + 10), height - padding - bar_height
            
            self.chart_canvas.create_rectangle(x, y, x + bar_width, height - padding, fill=Colors.PRIMARY, outline="")
            self.chart_canvas.create_text(x + bar_width / 2, y - 10, text=str(value), fill=Colors.TEXT_PRIMARY, font=("Arial", 10))
            self.chart_canvas.create_text(x + bar_width / 2, height - padding + 15, text=stats['date'].strftime("%d/%m"), fill=Colors.TEXT_MUTED, font=("Arial", 9))

    def _load_sessions(self, sessions: List[DrivingSession]):
        """Load driving sessions from a list of DrivingSession objects."""
        for widget in self.sessions_list.winfo_children():
            widget.destroy()

        if not sessions:
            StyledLabel(self.sessions_list, text="Chưa có phiên lái xe", style="muted").pack(pady=20)
            return
        
        for session in sessions:
            self._create_session_item(session)

    def _create_session_item(self, session: DrivingSession):
        """Create a session history item from a DrivingSession object."""
        frame = StyledFrame(self.sessions_list, style="transparent")
        frame.pack(fill="x", pady=3)

        time_str = session.start_time.strftime("%d/%m %H:%M")
        duration = 0
        if session.end_time:
            duration = round((session.end_time - session.start_time).total_seconds() / 60)
        
        status_icons = {'ACTIVE': '🟢', 'COMPLETED': '✅', 'INTERRUPTED': '⚠️'}
        
        StyledLabel(frame, text=f"{status_icons.get(session.status, '⚪')} {time_str}", style="normal", size=11).pack(side="left")
        StyledLabel(frame, text=f"{duration}ph | {session.total_alerts} cảnh báo", style="muted", size=10).pack(side="right")

    def _create_stat_card(self, parent, title: str, value: str, color: str) -> ctk.CTkFrame:
        """Helper to create a statistics card."""
        card = StyledFrame(parent, style="bordered")
        StyledLabel(card, text=title, style="muted", size=12).pack(anchor="w", padx=15, pady=(10, 0))
        value_label = StyledLabel(card, text=value, style="title", size=28, text_color=color)
        value_label.pack(anchor="w", padx=15, pady=(5, 10))
        card.value_label = value_label
        return card

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Dashboard Test")
    root.geometry("1200x700")
    
    # This test will now require a running database with some data
    # For simple layout testing, we can pass a dummy user
    test_user = User(id=1, username='test_user')
    view = DashboardView(root, user=test_user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
