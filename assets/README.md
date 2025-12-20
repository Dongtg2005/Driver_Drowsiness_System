# Assets Directory

This directory contains audio files for the alert system.

## Required Audio Files

Place the following audio files in this directory:

1. **alert_level1.wav** - Warning beep (short beep sound)
2. **alert_level2.wav** - Alert sound (medium intensity)
3. **alert_level3.wav** - Critical alarm (loud alarm sound)

## Audio Specifications

- Format: WAV (recommended) or MP3
- Sample Rate: 44100 Hz
- Duration:
  - Level 1: 0.5 - 1 second
  - Level 2: 1 - 2 seconds
  - Level 3: 2 - 3 seconds (can loop)

## Free Sound Resources

You can download free sound effects from:
- [Freesound.org](https://freesound.org/)
- [Mixkit](https://mixkit.co/free-sound-effects/)
- [Zapsplat](https://www.zapsplat.com/)

## Alternative

If audio files are not present, the system will generate simple beeps using pygame.

## Example File Names

```
assets/
├── alert_level1.wav   # Warning beep
├── alert_level2.wav   # Alert sound
├── alert_level3.wav   # Critical alarm
├── icon.ico           # Application icon (optional)
└── README.md          # This file
```
