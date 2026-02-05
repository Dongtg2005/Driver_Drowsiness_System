"""
Image enhancement utilities for low-light / night mode.
"""
import cv2
import numpy as np

def enhance_image(frame: np.ndarray) -> np.ndarray:
    """
    Smart Enhance: Only apply equalization if image is dark.
    Reduces lag in well-lit environments.
    """
    try:
        # 1. Quick brightness check (HSV Value channel)
        # Convert a small thumbnail to check brightness fast
        small = cv2.resize(frame, (64, 48))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2]
        avg_brightness = np.mean(v)
        
        # Threshold: < 100 is somewhat dark, < 60 is very dark
        if avg_brightness > 100:
            return frame # Đủ sáng, không cần xử lý thêm -> Mượt
            
        # 2. Enhance if Dark
        img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        return cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    except Exception:
        return frame
