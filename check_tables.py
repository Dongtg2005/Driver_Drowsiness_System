
import sys
import os
sys.path.append(os.getcwd())

from src.database.db_connection import execute_query
from src.config.database import DATABASE_URL

def check_tables():
    print(f"🔌 Checking tables on: {DATABASE_URL.split('@')[-1]}")
    
    # Standard SQL to list tables
    tables = execute_query("SHOW TABLES", fetch=True)
    
    print("\n📊 Existing Tables:")
    if tables:
        found_tables = []
        for t in tables:
            # Result is usually [{'Tables_in_railway': 'users'}]
            table_name = list(t.values())[0]
            print(f" - {table_name}")
            found_tables.append(table_name)
            
        required = {'users', 'user_settings', 'alert_history', 'driving_sessions'}
        missing = required - set(found_tables)
        
        if not missing:
            print("\n✅ All required tables are present!")
        else:
            print(f"\n❌ Missing tables: {missing}")
    else:
        print("❌ No tables found! Database is empty.")

if __name__ == "__main__":
    check_tables()
