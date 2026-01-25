
import sys
import os
sys.path.append(os.getcwd())

from src.database.connection import engine, Base
from src.config.database import DATABASE_URL

# Import all models to ensure they are registered with Base.metadata
# Crucial for create_all to work correctly
from src.models.user_model import User
from src.models.user_settings_model import UserSettings
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession

def init_db():
    print(f"🔄 Initializing Database...")
    print(f"📍 Target: {DATABASE_URL.split('@')[-1]}")  # Hide credentials, show host
    
    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully via SQLAlchemy!")
        print("   - users")
        print("   - user_settings")
        print("   - alert_history")
        print("   - driving_sessions")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    init_db()
