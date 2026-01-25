"""
Script to add sunglasses_mode column to user_settings table
"""
from sqlalchemy import text
from src.database.connection import engine

try:
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'user_settings' 
            AND COLUMN_NAME = 'sunglasses_mode'
            AND TABLE_SCHEMA = DATABASE()
        """))
        
        exists = result.scalar()
        
        if exists == 0:
            # Add column if it doesn't exist
            conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN sunglasses_mode BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✅ Column 'sunglasses_mode' added successfully!")
        else:
            print("✅ Column 'sunglasses_mode' already exists!")
            
except Exception as e:
    print(f"❌ Error: {e}")
