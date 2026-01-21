"""
======================================================
📊 Dashboard View (SQLAlchemy Version)
Driver Drowsiness Detection System
Statistics and reports screen
======================================================
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict
from datetime import datetime, timedelta
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

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

# Configure Matplotlib for Dark Theme
plt.style.use('dark_background')

class DashboardView(ctk.CTkFrame):
    """Dashboard view for statistics and reports with advanced visualization"""
    
    def __init__(self, master, user: Optional[User] = None,
                 on_back: Optional[Callable] = None):
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user = user
        self.on_back = on_back
        self.figures = {} # Store figures to clear them later

        self._create_widgets()
        # Use after() to ensure the main window is fully loaded before DB access
        self.after(100, self._load_data)
    
    def _create_widgets(self):
        """Create all widgets"""
        self._create_header()
        
        main_content = StyledFrame(self, style="transparent")
        main_content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Split into Left (Charts) and Right (History)
        # Ratio approx 2:1
        left_panel = StyledFrame(main_content, style="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_panel = StyledFrame(main_content, style="card", width=350)
        right_panel.pack(side="right", fill="y", padx=(10, 0))
        
        self._create_stats_summary(left_panel)
        self._create_charts_panel(left_panel)
        self._create_history_panel(right_panel)
    
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
            filter_frame, values=["Hôm nay", "7 ngày", "30 ngày"],
            default="Hôm nay", command=lambda _: self._load_data(), width=120
        )
        self.date_filter.pack(side="left", padx=5)
        
        StyledButton(
            filter_frame, text="🔄 Làm mới", command=self._load_data,
            style="info", width=100, height=35
        ).pack(side="left", padx=5)
    
    def _create_stats_summary(self, parent):
        """Create statistics cards row"""
        cards_frame = StyledFrame(parent, style="transparent")
        cards_frame.pack(fill="x", pady=(0, 10))
        
        # Create 4 equal cards
        self.total_alerts_card = self._create_stat_card(cards_frame, "🚨 Tổng cảnh báo", "0", Colors.DANGER)
        self.total_alerts_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.drowsy_card = self._create_stat_card(cards_frame, "😴 Buồn ngủ", "0", Colors.WARNING)
        self.drowsy_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.yawn_card = self._create_stat_card(cards_frame, "🥱 Ngáp", "0", Colors.INFO)
        self.yawn_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.head_down_card = self._create_stat_card(cards_frame, "⬇️ Cúi đầu", "0", Colors.PRIMARY)
        self.head_down_card.pack(side="left", fill="x", expand=True, padx=5)

    def _create_charts_panel(self, parent):
        """Create area for matplotlib charts"""
        chart_frame = StyledFrame(parent, style="card")
        chart_frame.pack(fill="both", expand=True) # Takes remaining space
        
        # Use TabView for multiple charts
        self.tab_view = ctk.CTkTabview(chart_frame, fg_color="transparent")
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_view.add("📈 Xu hướng (EAR)")
        self.tab_view.add("📊 Cảnh báo tuần")
        
        # Placeholders for canvases
        self.line_chart_frame = StyledFrame(self.tab_view.tab("📈 Xu hướng (EAR)"), style="transparent")
        self.line_chart_frame.pack(fill="both", expand=True)
        
        self.bar_chart_frame = StyledFrame(self.tab_view.tab("📊 Cảnh báo tuần"), style="transparent")
        self.bar_chart_frame.pack(fill="both", expand=True)

    def _create_history_panel(self, parent):
        """Create history panel"""
        StyledLabel(parent, text="📜 Lịch sử cảnh báo", style="title", size=16).pack(anchor="w", padx=20, pady=(15, 10))
        self.history_list = ctk.CTkScrollableFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=10)
        self.history_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        StyledLabel(parent, text="🚗 Phiên lái xe", style="title", size=14).pack(anchor="w", padx=20, pady=(15, 5))
        self.sessions_list = ctk.CTkScrollableFrame(parent, fg_color=Colors.BG_INPUT, corner_radius=10, height=200)
        self.sessions_list.pack(fill="x", padx=10, pady=(0, 20))

    def _load_data(self):
        """Load data from the database."""
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
            else:
                start_date = end_date - timedelta(days=1) # Default

            # 1. Stats Summary
            stats = stats_controller.get_aggregated_stats(db, self.user.id, start_date, end_date)
            self._update_stats(stats)
            
            # 2. History & Sessions
            alerts = stats_controller.get_alerts_by_date_range(db, self.user.id, start_date, end_date)
            self._update_history(alerts)
            
            sessions = stats_controller.get_session_history(db, self.user.id, limit=10)
            self._load_sessions(sessions)
            
            # 3. Charts Data
            # A. Weekly Stats (Bar Chart)
            weekly_stats = stats_controller.get_weekly_statistics(db, self.user.id)
            
            # B. EAR Trend (Line Chart)
            # Fetch EAR data points for the selected period
            ear_data = stats_controller.get_ear_history(db, self.user.id, start_date, end_date)
            
            self._draw_charts(weekly_stats, ear_data)
            
        finally:
            db.close()

    def _update_stats(self, stats: dict):
        self.total_alerts_card.value_label.configure(text=str(stats.get('total_alerts', 0)))
        self.drowsy_card.value_label.configure(text=str(stats.get('drowsy_count', 0)))
        self.yawn_card.value_label.configure(text=str(stats.get('yawn_count', 0)))
        self.head_down_card.value_label.configure(text=str(stats.get('head_down_count', 0)))

    def _draw_charts(self, weekly_stats: List[dict], ear_data: List[dict]):
        """Render charts using Matplotlib"""
        self._draw_bar_chart(weekly_stats)
        self._draw_line_chart(ear_data)

    def _draw_bar_chart(self, data: List[dict]):
        """Draw Weekly Alerts Bar Chart"""
        # Clear previous
        for widget in self.bar_chart_frame.winfo_children():
            widget.destroy()

        # Prepare Data
        dates = [d['date'].strftime('%d/%m') for d in reversed(data)]
        counts = [d['total_alerts'] for d in reversed(data)]

        # Create Figure
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(Colors.BG_CARD) # Match card background
        ax = fig.add_subplot(111)
        ax.set_facecolor(Colors.BG_CARD)
        
        # Draw Bars
        bars = ax.bar(dates, counts, color=Colors.PRIMARY, width=0.5)
        
        # Style
        ax.set_title("Số lượng cảnh báo 7 ngày qua", color='white', pad=15)
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Annotate values
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', color='white')

        # Hover annotation
        annot = ax.annotate("", xy=(0,0), xytext=(0,20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="black", ec="white", alpha=0.9),
                            arrowprops=dict(arrowstyle="->", color="white"))
        annot.set_visible(False)

        def update_annot(bar):
            x = bar.get_x() + bar.get_width() / 2.
            y = bar.get_height()
            annot.xy = (x, y)
            text = f"{int(y)} cảnh báo"
            annot.set_text(text)
            annot.get_bbox_patch().set_alpha(0.9)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                for bar in bars:
                    cont, _ = bar.contains(event)
                    if cont:
                        update_annot(bar)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)

        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.bar_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_line_chart(self, data: List[dict]):
        """Draw EAR Trend Line Chart"""
        # Clear previous
        for widget in self.line_chart_frame.winfo_children():
            widget.destroy()

        if not data:
            StyledLabel(self.line_chart_frame, text="Không có dữ liệu chi tiết", style="muted").pack(pady=50)
            return

        # Prepare Data
        timestamps = [d['timestamp'] for d in data]
        values = [d['ear'] for d in data]

        # Create Figure
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(Colors.BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(Colors.BG_CARD)

        # Plot Line
        line, = ax.plot(timestamps, values, color=Colors.WARNING, marker='o', markersize=4, linestyle='-')
        
        # Reference Line (Drowsiness Threshold)
        ax.axhline(y=0.25, color=Colors.DANGER, linestyle='--', alpha=0.5, label='Ngưỡng buồn ngủ (0.25)')

        # Format Axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_title("Xu hướng chỉ số mắt (EAR)", color='white', pad=15)
        ax.set_ylim(0, 0.5) # EAR typically 0.0 to 0.4
        
        ax.tick_params(axis='x', colors='white', rotation=0)
        ax.tick_params(axis='y', colors='white')
        
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(facecolor=Colors.BG_CARD, edgecolor='white', labelcolor='white')

        # Hover
        annot = ax.annotate("", xy=(0,0), xytext=(20,20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="black", ec="white", alpha=0.8),
                            arrowprops=dict(arrowstyle="->", color="white"))
        annot.set_visible(False)

        def update_annot(ind):
            x, y = line.get_data()
            index = ind['ind'][0] # Get closest point
            
            # Use index to access original list
            dt_str = timestamps[index].strftime("%H:%M:%S")
            val = values[index]
            
            annot.xy = (x[index], y[index])
            text = f"Time: {dt_str}\nEAR: {val:.2f}"
            annot.set_text(text)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = line.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                    return
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)

        # Embed
        canvas = FigureCanvasTkAgg(fig, master=self.line_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _update_history(self, alerts: List[AlertHistory]):
        """Update history list"""
        for widget in self.history_list.winfo_children():
            widget.destroy()
        
        if not alerts:
            StyledLabel(self.history_list, text="Không có dữ liệu", style="muted").pack(pady=20)
            return
        
        for alert in alerts[:50]: # Increased limit
            self._create_alert_item(alert)

    def _create_alert_item(self, alert: AlertHistory):
        frame = StyledFrame(self.history_list, style="transparent")
        frame.pack(fill="x", pady=2)

        type_icons = {'DROWSY': '😴', 'YAWN': '🥱', 'HEAD_DOWN': '⬇️'}
        icon = type_icons.get(alert.alert_type, '⚠️')
        
        # Use proper colors
        level_colors = {
            1: Colors.WARNING_HEX, # Warning (Hex)
            2: Colors.ORANGE,      # Verify if this is Hex or skip
            3: Colors.DANGER       # Red
        }
        
        # FIX: Ensure color is HEX string, NOT Tuple
        raw_color = level_colors.get(alert.alert_level, Colors.WARNING_HEX)
        if isinstance(raw_color, tuple):
             # Simple partial fallback to Hex if accidentally got a Tuple
             color = Colors.DANGER
        else:
             color = raw_color
             
        time_str = alert.timestamp.strftime("%H:%M:%S %d/%m")
        
        # Layout: Icon | Time ----- Type | Level
        StyledLabel(frame, text=f"{icon}", size=14).pack(side="left", padx=(0, 5))
        StyledLabel(frame, text=time_str, style="normal", size=12).pack(side="left")
        
        info_str = f"{alert.alert_type}"
        StyledLabel(frame, text=f"Lv.{alert.alert_level}", size=11, text_color=color).pack(side="right")
        StyledLabel(frame, text=info_str, style="muted", size=11).pack(side="right", padx=10)

    def _load_sessions(self, sessions: List[DrivingSession]):
        for widget in self.sessions_list.winfo_children():
            widget.destroy()

        if not sessions:
            StyledLabel(self.sessions_list, text="Chưa có phiên", style="muted").pack(pady=20)
            return
        
        for session in sessions:
            self._create_session_item(session)

    def _create_session_item(self, session: DrivingSession):
        frame = StyledFrame(self.sessions_list, style="transparent")
        frame.pack(fill="x", pady=3)

        time_str = session.start_time.strftime("%d/%m %H:%M")
        duration_min = 0
        if session.end_time:
            duration = session.end_time - session.start_time
            duration_min = int(duration.total_seconds() / 60)
        else:
            # Active session
            duration = datetime.now() - session.start_time
            duration_min = int(duration.total_seconds() / 60)
        
        status_colors = {'ACTIVE': Colors.SUCCESS, 'COMPLETED': Colors.TEXT_SECONDARY}
        st_color = status_colors.get(session.status, Colors.TEXT_SECONDARY)
        
        StyledLabel(frame, text=f"{time_str}", style="normal", size=11).pack(side="left")
        StyledLabel(frame, text=f"{duration_min}m", style="muted", size=11).pack(side="right")
        StyledLabel(frame, text=f"•", text_color=st_color, size=16).pack(side="right", padx=5)

    def _create_stat_card(self, parent, title: str, value: str, color: str) -> ctk.CTkFrame:
        card = StyledFrame(parent, style="bordered")
        StyledLabel(card, text=title, style="muted", size=12).pack(anchor="w", padx=15, pady=(10, 0))
        value_label = StyledLabel(card, text=value, style="title", size=24, text_color=color)
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
