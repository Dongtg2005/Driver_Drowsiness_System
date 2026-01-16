"""
============================================
🔊 Audio Manager (Windows Native)
Driver Drowsiness Detection System
Uses winsound for Windows compatibility
============================================
"""

import os
import sys
import threading
import time
from typing import Optional

# Use winsound for Windows (built-in, no install needed)
try:
    import winsound
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ winsound not available. Audio alerts will be disabled.")


class AudioManager:
    """
    Manages audio playback for alert sounds using Windows native winsound.
    Uses Singleton pattern.
    """
    
    _instance: Optional['AudioManager'] = None
    
    def __new__(cls) -> 'AudioManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._is_playing = False
        self._volume = 1.0
        self._enabled = True
        self._stop_flag = False
        self._current_thread: Optional[threading.Thread] = None
        
        print("✅ Audio system initialized (Windows native)")
    
    def play_alert(self, level: int, loop: bool = False) -> None:
        """
        Play alert sound based on level.
        Level 1: Short beep
        Level 2: Medium beep 
        Level 3: Long alarm beep
        """
        if not self._enabled or not AUDIO_AVAILABLE:
            return
        
        self._stop_flag = False
        
        # Start in separate thread to not block
        self._current_thread = threading.Thread(
            target=self._play_beep_thread, 
            args=(level, loop), 
            daemon=True
        )
        self._current_thread.start()
    
    def _play_beep_thread(self, level: int, loop: bool) -> None:
        """Thread function to play beep sounds"""
        try:
            self._is_playing = True
            
            # Define beep patterns for each level
            # (frequency_hz, duration_ms)
            beep_patterns = {
                1: [(800, 200)],                          # Warning: short beep
                2: [(1000, 300), (1000, 300)],            # Alert: two beeps
                3: [(1200, 400), (800, 200), (1200, 400)] # Critical: alarm pattern
            }
            
            pattern = beep_patterns.get(level, [(800, 200)])
            
            while not self._stop_flag:
                for freq, duration in pattern:
                    if self._stop_flag:
                        break
                    winsound.Beep(freq, duration)
                    time.sleep(0.05)  # Small gap between beeps
                
                if not loop:
                    break
                    
                time.sleep(0.5)  # Gap between loop iterations
            
            self._is_playing = False
            
        except Exception as e:
            print(f"❌ Error playing sound: {e}")
            self._is_playing = False
    
    def play_beep(self) -> None:
        """Play a simple test beep"""
        if AUDIO_AVAILABLE:
            threading.Thread(
                target=lambda: winsound.Beep(1000, 200),
                daemon=True
            ).start()

    def play_alarm(self, loop: bool = False) -> None:
        """Play medium-level alarm (mapped to level 2)."""
        self.play_alert(2, loop=loop)

    def play_siren(self, loop: bool = True) -> None:
        """Play critical siren (mapped to level 3). Default is looping."""
        self.play_alert(3, loop=loop)
    
    def stop(self) -> None:
        """Stop all sounds"""
        self._stop_flag = True
        self._is_playing = False
    
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 - 1.0) - Note: winsound doesn't support volume control"""
        self._volume = max(0.0, min(1.0, volume))
    
    def enable(self) -> None:
        """Enable audio"""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable audio"""
        self._enabled = False
        self.stop()
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        return self._is_playing
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop()


# Create singleton instance
audio_manager = AudioManager()


def get_audio_manager() -> AudioManager:
    return audio_manager


def play_alert(level: int, loop: bool = False) -> None:
    audio_manager.play_alert(level, loop)


def stop_alert() -> None:
    audio_manager.stop()


def set_volume(volume: float) -> None:
    audio_manager.set_volume(volume)
