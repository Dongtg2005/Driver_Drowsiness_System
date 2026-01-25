
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Determine Environment
# Default to 'local' if not set
db_env = os.getenv("DATABASE_ENV", "local").lower()

# Railway automatically provides DATABASE_URL
_db_url = os.getenv("DATABASE_URL")

if db_env == "railway":
    if not _db_url:
        raise ValueError("❌ CRITICAL: DATABASE_ENV is set to 'railway' but DATABASE_URL is missing!")
    
    print("☁️  Running in RAILWAY mode. Local DB is logically locked.")
    
    if _db_url.startswith("mysql://"):
       DATABASE_URL = _db_url.replace("mysql://", "mysql+mysqlconnector://")
    else:
       DATABASE_URL = _db_url

else:
    # Local Mode fallback
    print("🏠 Running in LOCAL mode.")
    if _db_url:
        print("⚠️  Warning: DATABASE_URL found but DATABASE_ENV is not 'railway'. Using Cloud DB anyway.")
        if _db_url.startswith("mysql://"):
            DATABASE_URL = _db_url.replace("mysql://", "mysql+mysqlconnector://")
        else:
            DATABASE_URL = _db_url
    else:
        # Fallback to Local Configuration (Source of Truth: config.py)
        try:
            from config import config
            DB_HOST = config.DB_HOST
            DB_PORT = config.DB_PORT
            DB_NAME = config.DB_NAME
            DB_USER = config.DB_USER
            DB_PASSWORD = config.DB_PASSWORD
            
            # Ensure we use valid values
            DB_PORT = str(DB_PORT) if DB_PORT else "3306"
            DB_PASSWORD = DB_PASSWORD if DB_PASSWORD is not None else ""
            
            DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        except ImportError:
            # Emergency fallback if config.py cannot be imported
            DATABASE_URL = "mysql+mysqlconnector://root:12345@localhost:3306/drowsiness_db"

print(f"🔌 Database Configuration Loaded: {'Railway Cloud' if _db_url else 'Localhost'}")
