"""Script to reset admin password"""
import sys
sys.path.insert(0, '.')

import bcrypt
import mysql.connector

# Generate new hash
password = 'admin123'
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

print(f"New hash: {hashed}")

# Update database
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='123456',
    database='drowsiness_db'
)

cursor = conn.cursor()
cursor.execute("UPDATE users SET password = %s WHERE username = 'admin'", (hashed,))
conn.commit()

print(f"Updated {cursor.rowcount} row(s)")

# Verify
cursor.execute("SELECT password FROM users WHERE username = 'admin'")
result = cursor.fetchone()
stored_hash = result[0]

print(f"Stored hash: {stored_hash}")
print(f"Verify: {bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))}")

cursor.close()
conn.close()
