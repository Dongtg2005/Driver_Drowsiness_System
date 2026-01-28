
import threading
import time
import sys
import os
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.local_db import get_pending_alerts, mark_alerts_synced, mark_alerts_failed
from src.models.alert_model import alert_model # Phase 1: Use direct MySQL

from src.utils.logger import logger

# Cấu hình Sync
SYNC_INTERVAL = 10  # Chu kỳ sync (giây)
BATCH_SIZE = 10     # Số lượng record mỗi lần sync

class SyncService:
    """
    Service chạy ngầm để đồng bộ dữ liệu từ Local SQLite -> Cloud (MySQL/API).
    Đảm bảo Camera không bao giờ bị lag do mạng.
    """
    
    def __init__(self):
        self._is_running = False
        self._thread = None

    def start(self):
        """Khởi động sync thread"""
        if self._is_running: return
        self._is_running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True, name="SyncThread")
        self._thread.start()
        logger.info("✅ Sync Service started (Background)")

    def stop(self):
        self._is_running = False

    def _sync_loop(self):
        """Vòng lặp chính"""
        from src.database.db_connection import get_db

        while self._is_running:
            try:
                # [NEW] Network Heartbeat & Auto Reconnect
                # Check này sẽ tự động reconnect DB nếu mạng vừa có lại
                get_db().check_network_status()

                # 1. Lấy dữ liệu pending từ SQLite
                alerts = get_pending_alerts(limit=BATCH_SIZE)
                
                if not alerts:
                    # Không có gì để sync, ngủ lâu chút
                    time.sleep(SYNC_INTERVAL)
                    continue
                
                start_time = time.time()
                logger.info(f"[SYNC][SQLite] Found {len(alerts)} pending records")
                
                synced_ids = []
                failed_count = 0
                
                for alert in alerts:
                    try:
                        success = self._push_to_cloud(alert)
                        if success:
                            synced_ids.append(alert['id'])
                        else:
                            mark_alerts_failed([alert['id']], "Push returned False")
                            failed_count += 1
                            logger.warning(f"[SYNC][Cloud] ⚠️ Push failed for ID {alert['id']}")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"[SYNC][Cloud] ❌ Push Exception for ID {alert['id']}: {e}")
                        mark_alerts_failed([alert['id']], str(e))
                
                # 2. Cập nhật trạng thái SQLite (chỉ những cái thành công)
                if synced_ids:
                    mark_alerts_synced(synced_ids)
                    logger.info(f"[SYNC][Cloud] ✅ Batch push success: {len(synced_ids)} records")

                # Log tổng hợp cuối cùng
                total = len(alerts)
                success_count = len(synced_ids)
                duration_ms = int((time.time() - start_time) * 1000)
                
                summary_msg = f"[SYNC][SUMMARY] total={total} success={success_count} failed={failed_count} duration={duration_ms}ms"
                
                if failed_count > 0:
                    logger.warning(summary_msg)
                else:
                    logger.info(summary_msg)
                    
            except Exception as e:
                # Bắt lỗi toàn cục của vòng lặp để thread không bao giờ chết
                logger.error(f"[SYNC][FATAL] Loop Error: {e}")
                time.sleep(5) # Ngủ thêm nếu gặp lỗi lạ
            
            # Nghỉ ngơi giữa các lần sync
            time.sleep(SYNC_INTERVAL)

    def _push_to_cloud(self, alert: Dict[str, Any]) -> bool:
        """
        Chiến lược gửi dữ liệu (Forward-Compatible).
        Hiện tại: Gửi trực tiếp vào MySQL Server (Remote).
        Tương lai: Gọi API (POST /alerts).
        """
        try:
            # [PRAGMATIC FIX] Skip Guest/Offline User records (Identity Reconciliation Strategy)
            # Dữ liệu của User -1 chỉ tồn tại Local, không đẩy lên Cloud để tránh lỗi FK
            if alert.get('user_id', 0) < 0:
                # logger.debug(f"[SYNC] Skipping Guest record ID {alert['id']} (User -1)")
                return True # Return True to mark as 'synced' (processed) locally
            
            # [PHASE 1] Direct MySQL Connection (Railway)
            # Hàm này thực hiện INSERT vào MySQL Server
            # Lưu ý timestamp: alert['timestamp'] là chuỗi từ SQLite, MySQL sẽ tự convert
            
            # Cần convert alert_type string -> Enum nếu model yêu cầu, 
            # nhưng alert_model.log_alert của chúng ta đã xử lý str rồi.
            
            # [REGRESSION FIX] Dùng sync_to_cloud để ghi thẳng lên Cloud
            # Không dùng log_alert vì log_alert giờ chỉ ghi Local (gây loop).
            
            return alert_model.sync_to_cloud(
                user_id=alert['user_id'],
                alert_type=alert['alert_type'],
                alert_level=alert['alert_level'],
                ear_value=alert['ear'],
                mar_value=alert['mar'],
                head_pitch=alert['pitch'],
                head_yaw=alert['yaw'],
                duration=alert['duration'],
                perclos=alert['perclos'],
                timestamp=alert.get('timestamp') # Quan trọng: Giữ nguyên thời gian gốc
            )
            
            # [PHASE 3] API Call
            # response = requests.post(API_URL, json=alert)
            # return response.status_code == 200
            
        except Exception as e:
            # Mạng lỗi, server down -> Return False để lần sau sync lại
            # print(f"Push failed: {e}") 
            return False

# Singleton
sync_service = SyncService()
