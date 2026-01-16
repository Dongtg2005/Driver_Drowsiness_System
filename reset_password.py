"""Script to reset admin password safely.

This script uses the project's `config` and database helper to update the
admin password. It also uses the same hashing routine from `UserModel` to
ensure compatibility.
"""
import sys
sys.path.insert(0, '.')

from config import config
from src.models.user_model import UserModel
from src.database.db_connection import execute_query

def reset_admin_password(new_password: str = 'admin123') -> None:
    # Hash using the project's UserModel method
    hashed = UserModel.hash_password(new_password)

    print(f"Updating admin password (hashed): {hashed}")

    # Update using execute_query helper
    update_q = "UPDATE users SET password = %s WHERE username = 'admin'"
    res = execute_query(update_q, (hashed,))

    print(f"Update result: {res}")

    # Verify
    select_q = "SELECT password FROM users WHERE username = %s"
    rows = execute_query(select_q, ('admin',), fetch=True)
    if not rows:
        print("Admin user not found or DB error.")
        return

    stored_hash = rows[0].get('password')
    print(f"Stored hash: {stored_hash}")
    ok = UserModel.verify_password(new_password, stored_hash)
    print(f"Verify: {ok}")


if __name__ == '__main__':
    # You can change the password here or pass via environment in future
    reset_admin_password('admin123')
