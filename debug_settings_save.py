
import sys
import os
sys.path.append(os.getcwd())

# Import models FIRST to ensure SQLAlchemy registry is populated and relationships work
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession
from src.models.user_settings_model import UserSettings
from src.models.user_model import user_model, User

# Then import controllers that use these models
from src.controllers.settings_controller import settings_controller

def test_settings_persistence():
    user_id = 1
    print(f"Testing settings persistence for User {user_id}...")
    
    # 1. Initialize Settings Controller
    settings_controller.set_user(user_id)
    initial_settings = settings_controller.get_settings()
    print(f"Initial Settings: sunglasses_mode = {initial_settings.get('sunglasses_mode')}")
    
    # 2. Toggle Mode
    new_mode = not initial_settings.get('sunglasses_mode', False)
    print(f"Attempting to set sunglasses_mode = {new_mode}...")
    
    success, msg = settings_controller.update_settings(sunglasses_mode=new_mode)
    if success:
        print(f"✅ Update reported success: {msg}")
    else:
        print(f"❌ Update failed: {msg}")
        return

    # 3. Read back via SettingsController
    updated_settings = settings_controller.get_settings()
    print(f"SettingsController read back: sunglasses_mode = {updated_settings.get('sunglasses_mode')}")
    
    if updated_settings.get('sunglasses_mode') != new_mode:
        print("❌ FAIL: SettingsController did not return updated value!")
    else:
        print("✅ PASS: SettingsController returned updated value.")

    # 4. Read back via UserRepository (Simulating MonitorController)
    repo_settings = user_model.get_user_settings(user_id)
    print(f"UserRepository read back: sunglasses_mode = {repo_settings.get('sunglasses_mode')}")
    
    if repo_settings.get('sunglasses_mode') != new_mode:
        print("❌ FAIL: UserRepository (Monitor) did not see the change!")
    else:
        print("✅ PASS: UserRepository (Monitor) saw the change.")

if __name__ == "__main__":
    test_settings_persistence()
