import mysql.connector
import os
from dotenv import load_dotenv

# Load config
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "drowsiness_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def check_data_raw():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        if conn.is_connected():
            print("="*50)
            print("🔍 KIỂM TRA DỮ LIỆU TỪ DB (RAW SQL)")
            print("="*50)
            
            cursor = conn.cursor(dictionary=True)
            
            # Check Session
            cursor.execute("SELECT * FROM driving_sessions ORDER BY id DESC LIMIT 1")
            session = cursor.fetchone()
            if session:
                print(f"\n🚗 PHIÊN LÁI XE GẦN NHẤT (ID: {session['id']})")
                print(f"   - User ID: {session['user_id']}")
                print(f"   - Bắt đầu: {session['start_time']}")
                print(f"   - Kết thúc: {session['end_time']}")
                print(f"   - Alert Count: {session['total_alerts']} (Drowsy: {session['drowsy_count']})")
            else:
                print("\n🚗 Không tìm thấy phiên nào.")
                
            # Check Alerts
            print("\n🚨 5 CẢNH BÁO GẦN NHẤT:")
            cursor.execute("SELECT * FROM alert_history ORDER BY id DESC LIMIT 5")
            alerts = cursor.fetchall()
            if alerts:
                for alert in alerts:
                    print(f"   - [ID: {alert['id']}] Time: {alert['timestamp']} | Level: {alert['alert_level']}")
                    print(f"     Type: {alert['alert_type']}")
                    print(f"     Metrics: EAR={alert['ear_value']:.2f}, Pitch={alert['head_pitch']:.1f}")
            else:
                print("   (Chưa có dữ liệu)")
                
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    check_data_raw()
