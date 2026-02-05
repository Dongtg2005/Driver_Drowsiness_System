
import cv2
import threading
import time
from typing import Optional, Tuple

class ThreadedCamera:
    """
    A threaded camera wrapper to improve FPS.
    Continuously reads frames in a separate thread so the main loop never waits for I/O.
    """
    def __init__(self, src=0, api_preference=None, width=640, height=480, fps=30):
        self.src = src
        self.width = width
        self.height = height
        self.target_fps = fps
        
        if api_preference is not None:
            self.cap = cv2.VideoCapture(self.src, api_preference)
        else:
            self.cap = cv2.VideoCapture(self.src)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()
        self.last_frame_time = 0.0

    def start(self):
        if self.started:
            return self
        self.started = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()
        return self

    def update(self):
        while self.started:
            if not self.cap.isOpened():
                break
                
            grabbed, frame = self.cap.read()
            with self.read_lock:
                if grabbed:
                    self.grabbed = grabbed
                    self.frame = frame
                else:
                    self.grabbed = False
            
            # Simple sleep to avoid hogging CPU if camera is slow
            time.sleep(0.005) 

    def read(self) -> Tuple[bool, Optional[object]]:
        with self.read_lock:
            if self.frame is None:
                return False, None
            return self.grabbed, self.frame.copy()

    def stop(self):
        self.started = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        if self.cap:
             self.cap.release()

    def isOpened(self):
        return self.cap.isOpened()
    
    def set(self, propId, value):
        self.cap.set(propId, value)
    
    def release(self):
        self.stop()
