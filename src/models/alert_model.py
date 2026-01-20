"""
============================================
🚨 Alert Model (Fixed & Optimized)
Driver Drowsiness Detection System
Alert history data operations
============================================
"""

from typing import Optional, Dict, List, Tuple, Union
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import DB Connection & Constants
from src.database.db_connection import execute_query
from src.utils.constants import AlertType, AlertLevel

class AlertModel:
    """
    Model class for alert-related database operations.
    Handles logging alerts and retrieving history.
    """
    
    def log_alert(self, user_id: int, alert_type: Union[AlertType, str], 
                  alert_level: Union[AlertLevel, int], ear_value: float = 0.0,
                  mar_value: float = 0.0, head_pitch: float = 0.0,
                  head_yaw: float = 0.0, duration: float = 0.0,
                  screenshot_path: str = None, perclos: float = 0.0,
                  session_id: Optional[int] = None, **kwargs) -> Optional[int]:
        """
        Ghi log cảnh báo mới vào database.
        Hàm này hỗ trợ nhận cả Enum hoặc giá trị nguyên thủy (str/int).
        """
        # 1. Chuẩn hóa dữ liệu đầu vào (Enum -> Value)
        # MySQL không hiểu Python Enum, phải chuyển về String/Int
        type_val = alert_type.value if hasattr(alert_type, 'value') else str(alert_type)
        level_val = int(alert_level) # AlertLevel là IntEnum nên ép kiểu int là an toàn
        
        # 2. Câu lệnh SQL
        query = """
            INSERT INTO alert_history 
            (user_id, alert_type, alert_level, ear_value, mar_value, 
             head_pitch, head_yaw, duration_seconds, screenshot_path, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        
        # 3. Tham số (lưu các trường chính; `perclos` được chấp nhận nhưng không
        #    được lưu vào bảng mặc định nếu schema không chứa cột tương ứng).
        params = (
            user_id,
            type_val,       # Ví dụ: 'DROWSY'
            level_val,      # Ví dụ: 3
            float(ear_value or 0),
            float(mar_value or 0),
            float(head_pitch or 0),
            float(head_yaw or 0),
            float(duration or 0),
            screenshot_path
        )
        
        # 4. Thực thi
        result_id = execute_query(query, params)
        return result_id # Trả về ID của dòng vừa insert

    def get_daily_statistics(self, user_id: int, date: datetime = None) -> Dict:
        """
        Lấy thống kê trong ngày.
        """
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        query = """
            SELECT 
                COUNT(*) as total_alerts,
                SUM(CASE WHEN alert_type = 'DROWSY' THEN 1 ELSE 0 END) as drowsy_count,
                SUM(CASE WHEN alert_type = 'YAWN' THEN 1 ELSE 0 END) as yawn_count,
                SUM(CASE WHEN alert_type = 'HEAD_DOWN' THEN 1 ELSE 0 END) as head_down_count,
                AVG(ear_value) as avg_ear,
                AVG(mar_value) as avg_mar,
                MAX(alert_level) as max_alert_level
            FROM alert_history
            WHERE user_id = %s AND timestamp BETWEEN %s AND %s
        """
        
        result = execute_query(query, (user_id, start, end), fetch=True)
        
        # Xử lý kết quả trả về (tránh None nếu không có dữ liệu)
        if result and result[0]:
            row = result[0]
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_alerts': row['total_alerts'] or 0,
                'drowsy_count': int(row['drowsy_count'] or 0),
                'yawn_count': int(row['yawn_count'] or 0),
                'head_down_count': int(row['head_down_count'] or 0),
                'avg_ear': round(float(row['avg_ear'] or 0), 3),
                'avg_mar': round(float(row['avg_mar'] or 0), 3),
                'max_alert_level': row['max_alert_level'] or 0
            }
        
        # Trả về mặc định nếu không có dữ liệu
        return {
            'date': date.strftime('%Y-%m-%d'), 'total_alerts': 0, 
            'drowsy_count': 0, 'yawn_count': 0, 'head_down_count': 0,
            'avg_ear': 0, 'avg_mar': 0, 'max_alert_level': 0
        }

    def get_recent_alerts(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Lấy danh sách cảnh báo gần đây (cho giao diện Dashboard)"""
        query = """
            SELECT alert_type, alert_level, timestamp, duration_seconds
            FROM alert_history
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return execute_query(query, (user_id, limit), fetch=True) or []

    def get_today_alerts(self, user_id: int) -> List[Dict]:
        """Lấy danh sách cảnh báo hôm nay"""
        query = """
            SELECT alert_type, alert_level, timestamp, duration_seconds
            FROM alert_history
            WHERE user_id = %s AND DATE(timestamp) = CURDATE()
            ORDER BY timestamp DESC
        """
        return execute_query(query, (user_id,), fetch=True) or []

    def get_alerts_by_date_range(self, user_id: int, start_date, end_date) -> List[Dict]:
        """Lấy danh sách cảnh báo trong khoảng thời gian"""
        query = """
            SELECT alert_type, alert_level, timestamp, duration_seconds
            FROM alert_history
            WHERE user_id = %s AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """
        return execute_query(query, (user_id, start_date, end_date), fetch=True) or []

    def get_alerts_by_user(self, user_id: int) -> List[Dict]:
        """Lấy tất cả cảnh báo của user"""
        query = """
            SELECT alert_type, alert_level, timestamp, duration_seconds
            FROM alert_history
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT 100
        """
        return execute_query(query, (user_id,), fetch=True) or []

    def get_weekly_statistics(self, user_id: int) -> List[Dict]:
        """Lấy dữ liệu biểu đồ 7 ngày"""
        stats = []
        today = datetime.now()
        for i in range(6, -1, -1): # Từ 6 ngày trước đến hôm nay
            date = today - timedelta(days=i)
            daily_stats = self.get_daily_statistics(user_id, date)
            stats.append(daily_stats)
        return stats


class DrivingSessionModel:
    """
    Model quản lý phiên lái xe (Start -> End chuyến đi).
    """
    
    def start_session(self, user_id: int) -> Optional[int]:
        """Bắt đầu phiên mới, đồng thời đóng các phiên cũ chưa đóng"""
        self.end_active_sessions(user_id)
        
        query = """
            INSERT INTO driving_sessions (user_id, start_time, status, total_alerts)
            VALUES (%s, NOW(), 'ACTIVE', 0)
        """
        return execute_query(query, (user_id,))
    
    def end_session(self, session_id: int) -> bool:
        """Kết thúc phiên hiện tại"""
        if not session_id: return False
        
        query = """
            UPDATE driving_sessions 
            SET end_time = NOW(), status = 'COMPLETED'
            WHERE id = %s
        """
        result = execute_query(query, (session_id,))
        return result is not None # execute_query trả về None nếu lỗi
    
    def end_active_sessions(self, user_id: int) -> None:
        """Dọn dẹp các session bị treo (do tắt máy đột ngột)"""
        query = """
            UPDATE driving_sessions 
            SET end_time = NOW(), status = 'INTERRUPTED'
            WHERE user_id = %s AND status = 'ACTIVE'
        """
        execute_query(query, (user_id,))
    
    def update_session_counts(self, session_id: int, alert_type: Union[AlertType, str]) -> bool:
        """
        Tăng biến đếm cảnh báo trong bảng sessions.
        Giúp truy vấn thống kê nhanh hơn mà không cần join bảng alert_history.
        """
        if not session_id: return False

        # Chuẩn hóa Enum
        type_str = alert_type.value if hasattr(alert_type, 'value') else str(alert_type)
        
        # Xác định cột cần tăng
        drowsy_inc = 1 if type_str == 'DROWSY' else 0
        yawn_inc = 1 if type_str == 'YAWN' else 0
        
        query = """
            UPDATE driving_sessions 
            SET total_alerts = total_alerts + 1,
                drowsy_count = drowsy_count + %s,
                yawn_count = yawn_count + %s
            WHERE id = %s
        """
        
        result = execute_query(query, (drowsy_inc, yawn_inc, session_id))
        return result is not None
    
    def get_session_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Lấy lịch sử các chuyến đi"""
        query = """
            SELECT id, start_time, end_time, status, total_alerts,
                   TIMESTAMPDIFF(MINUTE, start_time, IFNULL(end_time, NOW())) as duration_minutes
            FROM driving_sessions
            WHERE user_id = %s
            ORDER BY start_time DESC
            LIMIT %s
        """
        return execute_query(query, (user_id, limit), fetch=True) or []


# Tạo Singleton Instance để các module khác import dùng luôn
alert_model = AlertModel()
session_model = DrivingSessionModel()