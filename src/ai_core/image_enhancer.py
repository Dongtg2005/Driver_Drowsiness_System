"""
Image enhancement utilities for low-light / night mode.
"""
import cv2
import numpy as np

def enhance_image(frame: np.ndarray) -> np.ndarray:
    """Apply YUV histogram equalization to brighten low-light frames."""
    try:
        img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        return cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    except Exception:
        return frame
