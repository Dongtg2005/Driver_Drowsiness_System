"""
============================================
👁️ Face Mesh Module
Driver Drowsiness Detection System
MediaPipe Tasks API (0.10.30+)
============================================
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, NamedTuple
import sys
import os
import urllib.request

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import mp_config

# Import MediaPipe Tasks
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError as e:
    MEDIAPIPE_AVAILABLE = False
    print(f"❌ MediaPipe not installed! {e}")


class FaceLandmarks(NamedTuple):
    """Container for face landmark data"""
    landmarks: List[Tuple[float, float, float]]  # (x, y, z) normalized
    pixel_landmarks: List[Tuple[int, int]]        # (x, y) pixel coordinates
    image_width: int
    image_height: int


class FaceMeshDetector:
    """
    MediaPipe Face Mesh detector wrapper using Tasks API.
    Detects 478 facial landmarks in real-time.
    """
    
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
    
    def __init__(self, 
                 max_faces: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """
        Initialize Face Mesh detector.
        """
        self.max_faces = max_faces
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        
        self._face_landmarker = None
        self._legacy_mode = False
        self._face_mesh_legacy = None
        self._initialize_detector()
    
    def _download_model(self) -> bool:
        """Download the face landmarker model if not exists"""
        if os.path.exists(self.MODEL_PATH):
            return True
        
        print("⏳ Downloading Face Landmarker model...")
        try:
            urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
            print("✅ Model downloaded successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
            return False
    
    def _initialize_detector(self) -> None:
        """Initialize MediaPipe Face Landmarker"""
        if not MEDIAPIPE_AVAILABLE:
            print("❌ Cannot initialize Face Mesh - MediaPipe not available")
            return
        
        # Download model if needed
        if not self._download_model():
            return
        
        try:
            # Try to import and use with proper error handling for Python 3.14
            base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
            
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=self.max_faces,
                min_face_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False
            )
            
            self._face_landmarker = vision.FaceLandmarker.create_from_options(options)
            print("✅ Face Landmarker initialized (Tasks API)")
            
        except (OSError, AttributeError, Exception) as e:
            error_msg = str(e).lower()
            # Handle ctypes/dll issues with 'free' function or other compatibility problems
            if "free" in error_msg or "ctypes" in error_msg or "dll" in error_msg or "libmediapipe" in error_msg:
                print(f"⚠️ MediaPipe Tasks API has compatibility issues: {e}")
                print("⚠️ Falling back to legacy MediaPipe solutions API...")
                self._try_legacy_mediapipe()
            else:
                print(f"⚠️ Error with Tasks API: {e}")
                print("⚠️ Attempting fallback to legacy API...")
                self._try_legacy_mediapipe()
    
    def _try_legacy_mediapipe(self) -> None:
        """Try to use legacy MediaPipe solutions API as fallback"""
        try:
            # Try legacy solutions API (may work on some Python versions)
            self._legacy_mode = True
            self._face_mesh_legacy = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=self.max_faces,
                refine_landmarks=True,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self._face_landmarker = True  # Mark as available
            print("✅ Face Mesh initialized (Legacy Solutions API)")
        except Exception as e:
            print(f"❌ Legacy API also failed: {e}")
            self._face_landmarker = None
            self._legacy_mode = False
    
    def detect(self, image: np.ndarray) -> Optional[List[FaceLandmarks]]:
        """
        Detect faces and landmarks in an image.
        
        Args:
            image: BGR image from OpenCV
            
        Returns:
            List of FaceLandmarks objects, or None if no faces detected
        """
        if self._face_landmarker is None:
            return None
        
        # Check if using legacy mode
        if hasattr(self, '_legacy_mode') and self._legacy_mode:
            return self._detect_legacy(image)
        
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            
            # Detect face landmarks
            result = self._face_landmarker.detect(mp_image)
            
            if not result.face_landmarks:
                return None
            
            h, w = image.shape[:2]
            face_landmarks_list = []
            
            for face_landmarks in result.face_landmarks:
                # Extract normalized landmarks
                landmarks = []
                pixel_landmarks = []
                
                for lm in face_landmarks:
                    landmarks.append((lm.x, lm.y, lm.z))
                    pixel_landmarks.append((int(lm.x * w), int(lm.y * h)))
                
                face_landmarks_list.append(FaceLandmarks(
                    landmarks=landmarks,
                    pixel_landmarks=pixel_landmarks,
                    image_width=w,
                    image_height=h
                ))
            
            return face_landmarks_list
            
        except Exception as e:
            print(f"❌ Error detecting faces: {e}")
            return None
    
    def _detect_legacy(self, image: np.ndarray) -> Optional[List[FaceLandmarks]]:
        """Detect faces using legacy MediaPipe solutions API"""
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process image
            results = self._face_mesh_legacy.process(rgb_image)
            
            if not results.multi_face_landmarks:
                return None
            
            h, w = image.shape[:2]
            face_landmarks_list = []
            
            for face_landmarks in results.multi_face_landmarks:
                # Extract landmarks
                landmarks = []
                pixel_landmarks = []
                
                for lm in face_landmarks.landmark:
                    landmarks.append((lm.x, lm.y, lm.z))
                    pixel_landmarks.append((int(lm.x * w), int(lm.y * h)))
                
                face_landmarks_list.append(FaceLandmarks(
                    landmarks=landmarks,
                    pixel_landmarks=pixel_landmarks,
                    image_width=w,
                    image_height=h
                ))
            
            return face_landmarks_list
            
        except Exception as e:
            print(f"❌ Error in legacy detection: {e}")
            return None
    
    def get_eye_landmarks(self, face_landmarks: FaceLandmarks) -> dict:
        """
        Get eye landmarks from face landmarks.
        
        Returns dict with 'left_eye' and 'right_eye' pixel coordinates.
        """
        # MediaPipe Face Mesh indices for eyes
        LEFT_EYE = [362, 385, 387, 263, 373, 380]   # P1-P6
        RIGHT_EYE = [33, 160, 158, 133, 153, 144]   # P1-P6
        
        left_eye = [face_landmarks.pixel_landmarks[i] for i in LEFT_EYE]
        right_eye = [face_landmarks.pixel_landmarks[i] for i in RIGHT_EYE]
        
        return {
            'left_eye': left_eye,
            'right_eye': right_eye
        }
    
    def get_mouth_landmarks(self, face_landmarks: FaceLandmarks) -> list:
        """
        Get mouth landmarks from face landmarks.
        
        Returns list of 8 mouth landmark pixel coordinates.
        """
        # Mouth indices: outer corners, upper/lower lip
        MOUTH = [61, 291, 0, 17, 13, 14, 78, 308]
        
        return [face_landmarks.pixel_landmarks[i] for i in MOUTH]
    
    def get_head_pose_landmarks(self, face_landmarks: FaceLandmarks) -> list:
        """
        Get 6 landmarks for head pose estimation.
        
        Returns list of (x, y) pixel coordinates for:
        nose tip, chin, left eye corner, right eye corner, 
        left mouth corner, right mouth corner
        """
        # 6-point model indices
        POSE_INDICES = [1, 152, 33, 263, 61, 291]
        
        return [face_landmarks.pixel_landmarks[i] for i in POSE_INDICES]
    
    def close(self) -> None:
        """Release resources"""
        if self._face_landmarker:
            self._face_landmarker.close()
            self._face_landmarker = None


# Singleton instance
_detector_instance: Optional[FaceMeshDetector] = None

def get_face_detector() -> FaceMeshDetector:
    """Get singleton Face Mesh detector"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = FaceMeshDetector()
    return _detector_instance
