
import sys
import os
sys.path.append(os.getcwd())

from src.database.connection import SessionLocal
from src.database.db_connection import execute_query
from sqlalchemy import inspect, text

def check_schema():
    print("Checking 'user_settings' schema...")
    try:
        # Method 1: Raw SQL Describe
        rows = execute_query("DESCRIBE user_settings", fetch=True)
        if rows:
            print("Columns in user_settings:")
            found = False
            for row in rows:
                # Mysql connector returns tuple or dict depending on config, usually tuple for raw
                # Field, Type, Null, Key, Default, Extra
                col_name = row['Field'] if isinstance(row, dict) else row[0]
                print(f" - {col_name}")
                if col_name == 'sunglasses_mode':
                    found = True
            
            if found:
                print("✅ Column 'sunglasses_mode' EXISTS.")
            else:
                print("❌ Column 'sunglasses_mode' IS MISSING!")
                # Attempt to fix
                print("Attempting to add column...")
                execute_query("ALTER TABLE user_settings ADD COLUMN sunglasses_mode BOOLEAN DEFAULT FALSE")
                print("✅ Column added successfully.")
        else:
            print("Could not fetch schema.")

    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
