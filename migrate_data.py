
import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.database import DATABASE_URL as RAILWAY_URL
from config import config
from src.models.user_model import User
from src.models.user_settings_model import UserSettings
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession

def migrate():
    print("🚀 Starting Data Migration: Local MySQL -> Railway MySQL")
    
    # 1. Setup Railway Connection (Destination)
    if not RAILWAY_URL or "localhost" in RAILWAY_URL:
        print("❌ Error: DATABASE_URL in .env seems to be local or missing. Please ensure .env has the Railway URL.")
        return

    print(f"☁️  Destination (Railway): {RAILWAY_URL.split('@')[-1]}")
    railway_engine = create_engine(RAILWAY_URL, pool_pre_ping=True)
    RailwaySession = sessionmaker(bind=railway_engine)
    railway_db = RailwaySession()
    
    # 2. Setup Local Connection (Source)
    # We construct this manually to force local connection regardless of .env DATABASE_URL
    local_url = f"mysql+mysqlconnector://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    print(f"🏠 Source (Local): {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    
    try:
        local_engine = create_engine(local_url)
        LocalSession = sessionmaker(bind=local_engine)
        local_db = LocalSession()
    except Exception as e:
        print(f"❌ Error connecting to Local DB: {e}")
        if "Access denied" in str(e):
             print("\n⚠️  HINT: Password sai hoặc User không đúng.")
             print("   Hãy kiểm tra lại file 'config.py' hoặc '.env' để điền đúng pass Local DB của bạn.")
             print("   (Mặc định trong code đang là '12345')")
        return

    try:
        # 3. Migrate Users
        local_users = local_db.query(User).all()
        print(f"\n📦 Found {len(local_users)} users in Local DB.")
        
        migrated_count = 0
        for u in local_users:
            # Check if user exists in Railway
            exists = railway_db.query(User).filter_by(username=u.username).first()
            if not exists:
                print(f"   -> Migrating user: {u.username}")
                new_user = User(
                    username=u.username,
                    password=u.password,
                    full_name=u.full_name,
                    email=u.email,
                    phone=u.phone,
                    avatar=u.avatar,
                    is_active=u.is_active,
                    created_at=u.created_at
                )
                railway_db.add(new_user)
                railway_db.flush() # Flush to generate ID if needed for relationships, though we might rely on auto-inc
                
                # Migrate Settings for this user
                if u.settings:
                    print(f"      + Migrating settings for {u.username}")
                    new_settings = UserSettings(
                        user_id=new_user.id,
                        ear_threshold=u.settings.ear_threshold,
                        mar_threshold=u.settings.mar_threshold,
                        head_threshold=u.settings.head_threshold,
                        alert_volume=u.settings.alert_volume,
                        sensitivity_level=u.settings.sensitivity_level,
                        enable_sound=u.settings.enable_sound,
                        enable_vibration=u.settings.enable_vibration,
                        sunglasses_mode=u.settings.sunglasses_mode
                    )
                    # Handle relationship assignment if needed, or just add object
                    new_user.settings = new_settings 
                    
                migrated_count += 1
            else:
                print(f"   - User {u.username} already exists on Railway. Syncing Data...")
                # Even if user exists, we might need to sync their sessions/alerts if ID matches, 
                # but linking ID across databases is tricky if auto-inc differs.
                # Simplest strategy: Find the railway user object to link new records to.
                new_user = exists

            # 4. Migrate Driving Sessions (Bulk Mode)
            print(f"     > Checking sessions for {u.username}...")
            local_sessions = local_db.query(DrivingSession).filter_by(user_id=u.id).all()
            
            # Pre-fetch existing sessions for this user on Railway to minimize queries
            # We use start_time as unique identifier
            existing_sessions = railway_db.query(DrivingSession.start_time).filter_by(user_id=new_user.id).all()
            existing_session_times = {s[0] for s in existing_sessions}
            
            new_sessions_batch = []
            for s in local_sessions:
                if s.start_time not in existing_session_times:
                    new_sessions_batch.append(DrivingSession(
                        user_id=new_user.id,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        total_alerts=s.total_alerts,
                        drowsy_count=s.drowsy_count,
                        yawn_count=s.yawn_count,
                        status=s.status,
                        notes=s.notes
                    ))
            
            if new_sessions_batch:
                print(f"       + Bulk inserting {len(new_sessions_batch)} sessions...")
                railway_db.bulk_save_objects(new_sessions_batch)
                railway_db.commit() # Commit sessions first in case other things depend on them
            
            # 5. Migrate Alert History (Bulk Mode)
            print(f"     > Checking alerts for {u.username}...")
            local_alerts = local_db.query(AlertHistory).filter_by(user_id=u.id).all()
            
            # Pre-fetch existing alerts
            # We use timestamp as unique identifier
            existing_alerts = railway_db.query(AlertHistory.timestamp).filter_by(user_id=new_user.id).all()
            existing_alert_times = {a[0] for a in existing_alerts}
            
            new_alerts_batch = []
            for A in local_alerts:
                if A.timestamp not in existing_alert_times:
                    new_alerts_batch.append(AlertHistory(
                        user_id=new_user.id,
                        alert_type=A.alert_type, # Convert to string if it's enum, but here model should hande it or it's already string in DB
                        alert_level=A.alert_level,
                        ear_value=A.ear_value,
                        mar_value=A.mar_value,
                        head_pitch=A.head_pitch,
                        head_yaw=A.head_yaw,
                        duration_seconds=A.duration_seconds,
                        screenshot_path=A.screenshot_path,
                        timestamp=A.timestamp
                    ))
            
            if new_alerts_batch:
                print(f"       + Bulk inserting {len(new_alerts_batch)} alerts...")
                railway_db.bulk_save_objects(new_alerts_batch)
                railway_db.commit()

        print(f"✅ Migration Completed! Processed {len(local_users)} users.")

    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        railway_db.rollback()
    finally:
        local_db.close()
        railway_db.close()

if __name__ == "__main__":
    migrate()
