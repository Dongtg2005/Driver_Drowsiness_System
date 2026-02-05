"""
============================================
🔊 Audio Manager (Windows Native & TTS)
Driver Drowsiness Detection System
Uses winsound for Windows compatibility
Uses pyttsx3 for Text-to-Speech
============================================
"""

import os
import sys
import threading
import time
from typing import Optional
import pyttsx3
from gtts import gTTS
import tempfile
try:
    from playsound import playsound
    G_TTS_AVAILABLE = True
except ImportError:
    G_TTS_AVAILABLE = False
    print("⚠️ playsound not installed. Online TTS disabled.")

# Use winsound for Windows (built-in, no install needed)
try:
    import winsound
    AUDIO_AVAILABLE = True
except ImportError:
    import platform
    if platform.system() == "Windows":
        AUDIO_AVAILABLE = False
        print("⚠️ winsound not available. Audio alerts will be disabled.")
    else:
        AUDIO_AVAILABLE = False # Linux/Mac support needs other libs

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
        self.use_online_tts = False # Default to offline
        
        # [NEW] TTS Queue to prevent voice overlap
        from collections import deque
        self._tts_queue = deque()
        self._tts_queue_lock = threading.Lock()
        self._tts_worker_active = False
        
        # TTS Engine
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            
            # Auto-detect Vietnamese voice
            image_voices = self.tts_engine.getProperty('voices')
            vi_voice_id = None
            for voice in image_voices:
                # Common IDs for Vietnamese: 'vi', 'vietnam', 'an' (Microsoft An)
                if 'vietnam' in voice.name.lower() or 'vi_vn' in voice.id.lower():
                    vi_voice_id = voice.id
                    break
            
            if vi_voice_id:
                self.tts_engine.setProperty('voice', vi_voice_id)
                self.language = "vi"
                print(f"🎤 Default TTS Voice set to: {vi_voice_id}")
            else:
                 # Local Vietnamese voice NOT found. Switch to Online TTS (gTTS)
                 print("⚠️ No local Vietnamese voice found. Switching to Google TTS (Online).")
                 self.use_online_tts = True
                 self.language = "vi"
            
            self.tts_available = True
        except Exception as e:
            print(f"⚠️ TTS Init Error: {e}")
            self.tts_available = False
        
        print("✅ Audio system initialized (Windows native + TTS)")

    # ... (rest of class)

    
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
    
    def speak(self, text: str) -> None:
        """Speak text using TTS engine (Queue-based to prevent overlap) - supports Offline & Online"""
        if not self._enabled or not self.tts_available:
            return
        
        # [NEW] Queue the text instead of spawning multiple threads
        with self._tts_queue_lock:
            self._tts_queue.append(text)
        
        # Start worker if not already running
        if not self._tts_worker_active:
            self._tts_worker_active = True
            threading.Thread(target=self._tts_worker, daemon=True).start()
    
    def _tts_worker(self) -> None:
        """Background worker to process TTS queue sequentially"""
        while True:
            text = None
            with self._tts_queue_lock:
                if self._tts_queue:
                    text = self._tts_queue.popleft()
                else:
                    self._tts_worker_active = False
                    break
            
            if text:
                self._speak_internal(text)
    
    def _speak_internal(self, text: str) -> None:
        """Internal method to speak text (called by worker thread)"""
        if not self._enabled or not self.tts_available:
            return
            
        def _speak_online():
            if not G_TTS_AVAILABLE:
                print("⚠️ gTTS requested but not available.")
                return
            try:
                # Generate MP3 using Google TTS
                tts = gTTS(text=text, lang='vi')
                with tempfile.NamedTemporaryFile(delete=True) as fp:
                    temp_filename = fp.name + ".mp3"
                
                tts.save(temp_filename)
                # Play audio
                playsound(temp_filename)
                # Cleanup
                try:
                    os.remove(temp_filename)
                except: pass
            except Exception as e:
                print(f"Online TTS Error: {e}")

        # Capture the voice ID detected in __init__
        target_voice_id = None
        try:
             target_voice_id = self.tts_engine.getProperty('voice')
        except: pass

        def _speak_offline():
            try:
                # Re-initialize engine in thread to avoid COM errors
                engine = pyttsx3.init()
                
                # Apply the detected Vietnamese voice if available
                if target_voice_id:
                     engine.setProperty('voice', target_voice_id)
                
                # Slow down slightly for clarity
                engine.setProperty('rate', 140) 
                
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"Offline TTS Error: {e}")

        # Select Strategy
        if self.use_online_tts and G_TTS_AVAILABLE:
             _speak_online()
        else:
             _speak_offline()

    def stop(self) -> None:
        """Stop all sounds"""
        self._stop_flag = True
        self._is_playing = False
        if self.tts_available:
            try:
                self.tts_engine.stop()
            except: pass
    
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 - 1.0) - Note: winsound doesn't support volume control"""
        self._volume = max(0.0, min(1.0, volume))
        if self.tts_available:
            try:
                self.tts_engine.setProperty('volume', self._volume)
            except: pass
    
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

