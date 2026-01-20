
import sys
import os
import time

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.audio_manager import audio_manager

def test_tts():
    print("Testing TTS System...")
    
    if not audio_manager.tts_available:
        print("❌ TTS is NOT available on this system.")
        return

    print("Speaking: 'System initialized'")
    audio_manager.speak("System initialized")
    time.sleep(2)
    
    print("Speaking: 'You are drowsy'")
    audio_manager.speak("You are drowsy")
    time.sleep(2)
    
    print("✅ TTS Test Completed")

if __name__ == "__main__":
    test_tts()
