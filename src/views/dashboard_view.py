"""
============================================
📊 Dashboard View
Driver Drowsiness Detection System
Statistics and reports screen
============================================
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.views.components import (
    Colors, StyledButton, StyledLabel, StyledFrame,
    StyledOptionMenu, MessageBox
)
from src.models.alert_model import alert_model, session_model


class DashboardView(ctk.CTkFrame):
    """Dashboard view for statistics and reports"""
    
    def __init__(self, master, user_data: dict = None,
                 on_back: Callable = None):
        """
        Create dashboard view.
        
        Args:
            master: Parent widget
            user_data: Logged in user data
            on_back: Callback to go back
        """
        super().__init__(master, fg_color=Colors.BG_DARK)
        
        self.user_data = user_data
        self.on_back = on_back
        self.user_id = user_data.get('id') if user_data else None
        
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        """Create all widgets"""
        # Header
        self._create_header()
        
        # Main content
        main_frame = StyledFrame(self, style="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left panel - Statistics
        self._create_stats_panel(main_frame)
        
        # Right panel - History
        self._create_history_panel(main_frame)
    
    def _create_header(self):
        """Create header bar"""
        header = StyledFrame(self, style="card")
        header.pack(fill="x", padx=10, pady=10)
        
        # Back button
        StyledButton(
            header,
            text="← Quay lại",
            command=self._on_back_click,
            style="secondary",
            width=100,
            height=35
        ).pack(side="left", padx=10)
        
        # Title
        StyledLabel(
            header,
            text="📊 Báo cáo & Thống kê",
            style="title",
            size=18
        ).pack(side="left", padx=20)
        
        # Date filter
        filter_frame = StyledFrame(header, style="transparent")
        filter_frame.pack(side="right", padx=10)
        
        StyledLabel(filter_frame, text="Thời gian:", style="normal").pack(side="left", padx=5)
        
        self.date_filter = StyledOptionMenu(
            filter_frame,
            values=["Hôm nay", "7 ngày", "30 ngày", "Tất cả"],
            default="Hôm nay",
            command=self._on_filter_change,
            width=120
        )
        self.date_filter.pack(side="left", padx=5)
        
        # Refresh button
        StyledButton(
            filter_frame,
            text="🔄 Làm mới",
            command=self._load_data,
            style="info",
            width=100,
            height=35
        ).pack(side="left", padx=5)
    
    def _create_stats_panel(self, parent):
        """Create statistics panel"""
        stats_frame = StyledFrame(parent, style="card")
        stats_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Title
        StyledLabel(
            stats_frame,
            text="📈 Tổng quan",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Stats cards
        cards_frame = StyledFrame(stats_frame, style="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)
        
        # Row 1
        row1 = StyledFrame(cards_frame, style="transparent")
        row1.pack(fill="x", pady=5)
        
        self.total_alerts_card = self._create_stat_card(
            row1, "🚨 Tổng cảnh báo", "0", Colors.DANGER
        )
        self.total_alerts_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.drowsy_card = self._create_stat_card(
            row1, "😴 Buồn ngủ", "0", Colors.WARNING
        )
        self.drowsy_card.pack(side="left", fill="x", expand=True, padx=5)
        
        # Row 2
        row2 = StyledFrame(cards_frame, style="transparent")
        row2.pack(fill="x", pady=5)
        
        self.yawn_card = self._create_stat_card(
            row2, "🥱 Ngáp", "0", Colors.INFO
        )
        self.yawn_card.pack(side="left", fill="x", expand=True, padx=5)
        
        self.head_down_card = self._create_stat_card(
            row2, "⬇️ Cúi đầu", "0", Colors.PRIMARY
        )
        self.head_down_card.pack(side="left", fill="x", expand=True, padx=5)
        
        # Weekly chart section
        chart_section = StyledFrame(stats_frame, style="transparent")
        chart_section.pack(fill="both", expand=True, padx=20, pady=10)
        
        StyledLabel(
            chart_section,
            text="📅 Thống kê 7 ngày gần nhất",
            style="title",
            size=14
        ).pack(anchor="w", pady=(10, 5))
        
        # Simple bar chart using canvas
        self.chart_frame = StyledFrame(chart_section, style="bordered")
        self.chart_frame.pack(fill="both", expand=True, pady=10)
        
        self.chart_canvas = ctk.CTkCanvas(
            self.chart_frame,
            bg=Colors.BG_CARD,
            highlightthickness=0,
            height=200
        )
        self.chart_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Average metrics
        metrics_frame = StyledFrame(stats_frame, style="transparent")
        metrics_frame.pack(fill="x", padx=20, pady=10)
        
        StyledLabel(
            metrics_frame,
            text="📊 Giá trị trung bình",
            style="title",
            size=14
        ).pack(anchor="w", pady=(10, 5))
        
        metrics_row = StyledFrame(metrics_frame, style="transparent")
        metrics_row.pack(fill="x")
        
        self.avg_ear_label = self._create_metric_item(metrics_row, "EAR", "--")
        self.avg_mar_label = self._create_metric_item(metrics_row, "MAR", "--")
        self.max_level_label = self._create_metric_item(metrics_row, "Max Level", "--")
    
    def _create_stat_card(self, parent, title: str, value: str, 
                          color: str) -> ctk.CTkFrame:
        """Create a statistics card"""
        card = StyledFrame(parent, style="bordered")
        
        StyledLabel(
            card,
            text=title,
            style="muted",
            size=12
        ).pack(anchor="w", padx=15, pady=(10, 0))
        
        value_label = StyledLabel(
            card,
            text=value,
            style="title",
            size=28
        )
        value_label.pack(anchor="w", padx=15, pady=(5, 10))
        value_label.configure(text_color=color)
        
        # Store reference to value label
        card.value_label = value_label
        
        return card
    
    def _create_metric_item(self, parent, label: str, value: str) -> StyledLabel:
        """Create a metric display item"""
        frame = StyledFrame(parent, style="transparent")
        frame.pack(side="left", fill="x", expand=True, padx=10)
        
        StyledLabel(frame, text=label, style="muted", size=12).pack()
        value_label = StyledLabel(frame, text=value, style="normal", size=16)
        value_label.pack()
        
        return value_label
    
    def _create_history_panel(self, parent):
        """Create history panel"""
        history_frame = StyledFrame(parent, style="card")
        history_frame.pack(side="right", fill="both", padx=(10, 0), ipadx=10)
        
        # Title
        StyledLabel(
            history_frame,
            text="📜 Lịch sử cảnh báo",
            style="title",
            size=16
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # History list
        self.history_list = ctk.CTkScrollableFrame(
            history_frame,
            fg_color=Colors.BG_INPUT,
            corner_radius=10,
            width=350
        )
        self.history_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Sessions section
        StyledLabel(
            history_frame,
            text="🚗 Phiên lái xe gần đây",
            style="title",
            size=14
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.sessions_list = ctk.CTkScrollableFrame(
            history_frame,
            fg_color=Colors.BG_INPUT,
            corner_radius=10,
            width=350,
            height=150
        )
        self.sessions_list.pack(fill="x", padx=20, pady=(5, 15))
    
    def _load_data(self):
        """Load data from database"""
        if not self.user_id:
            return
        
        # Get date range based on filter
        filter_value = self.date_filter.get()
        
        if filter_value == "Hôm nay":
            stats = alert_model.get_daily_statistics(self.user_id)
            alerts = alert_model.get_today_alerts(self.user_id)
        elif filter_value == "7 ngày":
            end = datetime.now()
            start = end - timedelta(days=7)
            stats = self._aggregate_stats(self.user_id, 7)
            alerts = alert_model.get_alerts_by_date_range(self.user_id, start, end)
        elif filter_value == "30 ngày":
            end = datetime.now()
            start = end - timedelta(days=30)
            stats = self._aggregate_stats(self.user_id, 30)
            alerts = alert_model.get_alerts_by_date_range(self.user_id, start, end)
        else:
            stats = self._aggregate_stats(self.user_id, 365)
            alerts = alert_model.get_alerts_by_user(self.user_id)
        
        # Update UI
        self._update_stats(stats)
        self._update_history(alerts)
        self._update_chart()
        self._load_sessions()
    
    def _aggregate_stats(self, user_id: int, days: int) -> Dict:
        """Aggregate statistics for multiple days"""
        total = {
            'total_alerts': 0,
            'drowsy_count': 0,
            'yawn_count': 0,
            'head_down_count': 0,
            'avg_ear': 0,
            'avg_mar': 0,
            'max_alert_level': 0
        }
        
        ear_sum = 0
        mar_sum = 0
        count = 0
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            daily = alert_model.get_daily_statistics(user_id, date)
            
            total['total_alerts'] += daily.get('total_alerts', 0)
            total['drowsy_count'] += daily.get('drowsy_count', 0)
            total['yawn_count'] += daily.get('yawn_count', 0)
            total['head_down_count'] += daily.get('head_down_count', 0)
            
            if daily.get('avg_ear', 0) > 0:
                ear_sum += daily.get('avg_ear', 0)
                mar_sum += daily.get('avg_mar', 0)
                count += 1
            
            total['max_alert_level'] = max(
                total['max_alert_level'],
                daily.get('max_alert_level', 0)
            )
        
        if count > 0:
            total['avg_ear'] = round(ear_sum / count, 3)
            total['avg_mar'] = round(mar_sum / count, 3)
        
        return total
    
    def _update_stats(self, stats: Dict):
        """Update statistics cards"""
        self.total_alerts_card.value_label.configure(
            text=str(stats.get('total_alerts', 0))
        )
        self.drowsy_card.value_label.configure(
            text=str(stats.get('drowsy_count', 0))
        )
        self.yawn_card.value_label.configure(
            text=str(stats.get('yawn_count', 0))
        )
        self.head_down_card.value_label.configure(
            text=str(stats.get('head_down_count', 0))
        )
        
        self.avg_ear_label.configure(text=f"{stats.get('avg_ear', 0):.3f}")
        self.avg_mar_label.configure(text=f"{stats.get('avg_mar', 0):.3f}")
        self.max_level_label.configure(text=str(stats.get('max_alert_level', 0)))
    
    def _update_history(self, alerts: List[Dict]):
        """Update history list"""
        # Clear existing items
        for widget in self.history_list.winfo_children():
            widget.destroy()
        
        if not alerts:
            StyledLabel(
                self.history_list,
                text="Không có dữ liệu",
                style="muted"
            ).pack(pady=20)
            return
        
        # Show last 20 alerts
        for alert in alerts[:20]:
            self._create_alert_item(alert)
    
    def _create_alert_item(self, alert: Dict):
        """Create an alert history item"""
        frame = StyledFrame(self.history_list, style="transparent")
        frame.pack(fill="x", pady=2)
        
        # Type icon
        type_icons = {
            'DROWSY': '😴',
            'YAWN': '🥱',
            'HEAD_DOWN': '⬇️',
            'DISTRACTED': '👀'
        }
        
        alert_type = alert.get('alert_type', 'UNKNOWN')
        icon = type_icons.get(alert_type, '⚠️')
        
        # Level color
        level_colors = {
            1: Colors.WARNING,
            2: Colors.DANGER,
            3: Colors.DANGER
        }
        level = alert.get('alert_level', 1)
        color = level_colors.get(level, Colors.WARNING)
        
        # Timestamp
        timestamp = alert.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            time_str = timestamp
        else:
            time_str = timestamp.strftime("%d/%m %H:%M:%S")
        
        # Create row
        StyledLabel(
            frame,
            text=f"{icon} {time_str}",
            style="normal",
            size=12
        ).pack(side="left")
        
        level_label = StyledLabel(
            frame,
            text=f"Lv.{level}",
            size=11
        )
        level_label.configure(text_color=color)
        level_label.pack(side="right")
    
    def _update_chart(self):
        """Update the weekly chart"""
        if not self.user_id:
            return
        
        # Get weekly stats
        weekly_stats = alert_model.get_weekly_statistics(self.user_id)
        
        # Clear canvas
        self.chart_canvas.delete("all")
        
        # Get canvas size
        self.chart_canvas.update()
        width = self.chart_canvas.winfo_width()
        height = self.chart_canvas.winfo_height()
        
        if width < 100 or height < 100:
            return
        
        # Draw bars
        padding = 40
        bar_width = (width - 2 * padding) / 7 - 10
        max_value = max([s.get('total_alerts', 0) for s in weekly_stats] + [1])
        
        for i, stats in enumerate(reversed(weekly_stats)):
            value = stats.get('total_alerts', 0)
            bar_height = (value / max_value) * (height - 2 * padding) if max_value > 0 else 0
            
            x = padding + i * (bar_width + 10)
            y = height - padding - bar_height
            
            # Draw bar
            color = Colors.PRIMARY if value > 0 else Colors.TEXT_MUTED
            self.chart_canvas.create_rectangle(
                x, y, x + bar_width, height - padding,
                fill=color, outline=""
            )
            
            # Draw value
            self.chart_canvas.create_text(
                x + bar_width / 2, y - 10,
                text=str(value),
                fill=Colors.TEXT_PRIMARY,
                font=("Arial", 10)
            )
            
            # Draw day label
            date = datetime.now() - timedelta(days=6 - i)
            day_label = date.strftime("%d/%m")
            self.chart_canvas.create_text(
                x + bar_width / 2, height - padding + 15,
                text=day_label,
                fill=Colors.TEXT_MUTED,
                font=("Arial", 9)
            )
    
    def _load_sessions(self):
        """Load driving sessions"""
        if not self.user_id:
            return
        
        # Clear existing
        for widget in self.sessions_list.winfo_children():
            widget.destroy()
        
        sessions = session_model.get_session_history(self.user_id, limit=10)
        
        if not sessions:
            StyledLabel(
                self.sessions_list,
                text="Chưa có phiên lái xe",
                style="muted"
            ).pack(pady=20)
            return
        
        for session in sessions:
            self._create_session_item(session)
    
    def _create_session_item(self, session: Dict):
        """Create a session history item"""
        frame = StyledFrame(self.sessions_list, style="transparent")
        frame.pack(fill="x", pady=3)
        
        start_time = session.get('start_time', datetime.now())
        if isinstance(start_time, str):
            time_str = start_time
        else:
            time_str = start_time.strftime("%d/%m %H:%M")
        
        duration = session.get('duration_minutes', 0)
        alerts = session.get('total_alerts', 0)
        status = session.get('status', 'UNKNOWN')
        
        status_icons = {
            'ACTIVE': '🟢',
            'COMPLETED': '✅',
            'INTERRUPTED': '⚠️'
        }
        
        StyledLabel(
            frame,
            text=f"{status_icons.get(status, '⚪')} {time_str}",
            style="normal",
            size=11
        ).pack(side="left")
        
        StyledLabel(
            frame,
            text=f"{duration}ph | {alerts} cảnh báo",
            style="muted",
            size=10
        ).pack(side="right")
    
    def _on_filter_change(self, value):
        """Handle filter change"""
        self._load_data()
    
    def _on_back_click(self):
        """Handle back button click"""
        if self.on_back:
            self.on_back()


if __name__ == "__main__":
    # Test dashboard view
    root = ctk.CTk()
    root.title("Dashboard Test")
    root.geometry("1200x700")
    
    user = {'id': 1, 'username': 'test_user'}
    view = DashboardView(root, user_data=user)
    view.pack(fill="both", expand=True)
    
    root.mainloop()
