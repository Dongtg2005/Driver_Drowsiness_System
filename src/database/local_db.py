
import sqlite3
import os
import threading
from typing import Dict, Any, Optional

# Đường dẫn file DB nằm trong thư mục gốc hoặc thư mục data
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "local_alerts.db")

_local_connection = None
_lock = threading.Lock()

def get_local_db():
    """
    Tạo hoặc lấy kết nối SQLite (Threadify bằng check_same_thread=False)
    Sử dụng chế độ WAL để tối ưu ghi song song.
    """
    global _local_connection
    with _lock:
        if _local_connection is None:
            _local_connection = sqlite3.connect(DB_PATH, check_same_thread=False)
            # Bật chế độ WAL (Write-Ahead Logging) để ghi không block đọc
            _local_connection.execute("PRAGMA journal_mode=WAL;")
            _local_connection.execute("PRAGMA synchronous = NORMAL;")
            _initialize_db(_local_connection)
    return _local_connection

def _initialize_db(conn):
    """Khởi tạo bảng nếu chưa có"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id INTEGER,
                alert_type TEXT,
                alert_level INTEGER,
                score INTEGER,
                ear REAL,
                mar REAL,
                pitch REAL,
                yaw REAL,
                perclos REAL,
                duration REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'PENDING',
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                last_retry_at DATETIME
            );
        """)
        # Index cho sync_status để query nhanh
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON alerts(sync_status);")
        
        # [MIGRATION] Thêm cột nếu chưa có (cho DB cũ)
        try:
            cursor.execute("ALTER TABLE alerts ADD COLUMN retry_count INTEGER DEFAULT 0;")
        except: pass
        try:
            cursor.execute("ALTER TABLE alerts ADD COLUMN last_error TEXT;")
        except: pass
        try:
            cursor.execute("ALTER TABLE alerts ADD COLUMN last_retry_at DATETIME;")
        except: pass
        
        conn.commit()
    except Exception as e:
        print(f"❌ Init Local DB Error: {e}")

def log_alert_local(alert_data: Dict[str, Any]) -> bool:
    """
    Ghi log vào SQLite. Hàm này chạy cực nhanh (<1ms).
    """
    try:
        local_id = insert_alert(
            user_id=alert_data.get('user_id'),
            alert_type=alert_data.get('alert_type'),
            alert_level=alert_data.get('alert_level', 0),
            ear_value=float(alert_data.get('ear', 0)),
            mar_value=float(alert_data.get('mar', 0)),
            head_pitch=float(alert_data.get('pitch', 0)),
            head_yaw=float(alert_data.get('yaw', 0)),
            duration=float(alert_data.get('duration', 0)),
            perclos=float(alert_data.get('perclos', 0))
        )
        return local_id is not None
    except Exception as e:
        print(f"❌ Local Log Error: {e}")
        return False

def insert_alert(user_id, alert_type, alert_level, ear_value, mar_value, head_pitch, head_yaw, duration, perclos, timestamp=None) -> Optional[int]:
    """
    Helper function to insert alert with explicit arguments.
    Returns the new row ID.
    timestamp: Optional datetime object. If None, uses datetime.now() (Local Time).
    """
    try:
        from datetime import datetime
        conn = get_local_db()
        cursor = conn.cursor()
        
        # Determine timestamp (Local Time)
        ts_to_store = timestamp if timestamp else datetime.now()
        
        # Handle Enum or string
        type_val = alert_type.value if hasattr(alert_type, 'value') else str(alert_type)
        
        cursor.execute("""
            INSERT INTO alerts (
                user_id, alert_type, alert_level, 
                ear, mar, pitch, yaw, perclos, duration, 
                sync_status, retry_count, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, ?)
        """, (
            user_id, type_val, int(alert_level or 0),
            float(ear_value or 0), float(mar_value or 0), 
            float(head_pitch or 0), float(head_yaw or 0), 
            float(perclos or 0), float(duration or 0),
            ts_to_store
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"❌ Local Insert Error: {e}")
        return None

def get_pending_alerts(limit: int = 20, max_retries: int = 5):
    """
    Lấy danh sách các alert cần sync.
    Bao gồm:
    1. Trạng thái PENDING
    2. Trạng thái FAILED nhưng chưa vượt quá max_retries
    """
    try:
        conn = get_local_db()
        # Row factory để truy cập theo tên cột
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM alerts 
            WHERE sync_status = 'PENDING' 
               OR (sync_status = 'FAILED' AND retry_count < ?)
            ORDER BY timestamp ASC 
            LIMIT ?
        """, (max_retries, limit))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"❌ Get Pending Error: {e}")
        return []

def mark_alerts_synced(alert_ids: list):
    """Đánh dấu đã đồng bộ thành công"""
    if not alert_ids: return
    try:
        conn = get_local_db()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(alert_ids))
        cursor.execute(f"""
            UPDATE alerts SET sync_status = 'SYNCED' 
            WHERE id IN ({placeholders})
        """, alert_ids)
        conn.commit()
    except Exception as e:
        print(f"❌ Mark Synced Error: {e}")

def mark_alerts_failed(alert_ids: list, error_msg: str = "Unknown"):
    """
    Đánh dấu thất bại để retry sau.
    Tăng retry_count lên 1.
    Cập nhật last_retry_at hiện tại.
    """
    if not alert_ids: return
    try:
        conn = get_local_db()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(alert_ids))
        cursor.execute(f"""
            UPDATE alerts 
            SET sync_status = 'FAILED', 
                retry_count = retry_count + 1,
                last_error = ?,
                last_retry_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, [error_msg] + alert_ids)
        conn.commit()
    except Exception as e:
        print(f"❌ Mark Failed Error: {e}")

def migrate_guest_alerts(real_user_id: int) -> int:
    """
    [AUTO-MIGRATE] Chuyển đổi dữ liệu từ Guest (-1) sang User thật.
    Reset sync_status='PENDING' để SyncService đẩy lại lên Cloud.
    """
    try:
        conn = get_local_db()
        cursor = conn.cursor()
        
        # Chỉ migrate những dòng chưa được gán user thật (user_id < 0)
        cursor.execute("""
            UPDATE alerts 
            SET user_id = ?, 
                sync_status = 'PENDING', 
                retry_count = 0 
            WHERE user_id < 0
        """, (real_user_id,))
        
        affected = cursor.rowcount
        conn.commit()
        
        if affected > 0:
            print(f"🧠 [MIGRATE] Transferred {affected} offline alerts to User ID {real_user_id}")
            
        return affected
    except Exception as e:
        print(f"❌ Migration Error: {e}")
        return 0
