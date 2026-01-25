
import sys
import os
sys.path.append(os.getcwd())

from src.database.connection import SessionLocal
# Import ALL models to ensure relationships are registered
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession
from src.models.user_settings_model import UserSettings
from src.models.user_model import User
from src.config.database import DATABASE_URL
import time

def test_insert():
    print(f"🔌 Connecting to: {DATABASE_URL.split('@')[-1]}") # Show host only
    
    db = SessionLocal()
    try:
        # Create a unique username based on timestamp to avoid unique constraint errors on repeated runs
        test_username = f"cloud_test_{int(time.time())}"
        
        print(f"📝 Attempting to insert User: {test_username}")
        
        u = User(username=test_username, password="123") # Model uses 'password', not 'password_hash'
        db.add(u)
        db.commit()
        db.refresh(u)
        
        print(f"✅ Insert Railway MySQL OK")
        print(f"🆔 New User ID: {u.id}")
        print(f"👤 Username: {u.username}")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_insert()
