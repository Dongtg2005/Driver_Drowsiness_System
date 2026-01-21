"""
============================================
🗣️ Head Pose Estimation Module
Driver Drowsiness Detection System
Estimate head orientation (pitch, yaw, roll)
============================================
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config, mp_config
from src.utils.math_helpers import rotation_matrix_to_euler_angles, moving_average
from src.ai_core.face_mesh import FaceLandmarks


class HeadPoseEstimator:
    """
    Estimate head pose (pitch, yaw, roll) from facial landmarks.
    Uses solvePnP algorithm with 6 key facial points.
    """
    
    def __init__(self, smoothing_window: int = 5):
        """
        Initialize head pose estimator.
        
        Args:
            smoothing_window: Window size for moving average smoothing
        """
        self.smoothing_window = smoothing_window
        
        # History for smoothing
        self._pitch_history: List[float] = []
        self._yaw_history: List[float] = []
        self._roll_history: List[float] = []
        
        # Current values
        self._current_pitch: float = 0.0
        self._current_yaw: float = 0.0
        self._current_roll: float = 0.0
        
        # 3D model points for head pose estimation
        # Standard Generic Face Model (centered at Nose Tip)
        # Coordinate System matches OpenCV Camera: X-Right, Y-Down, Z-Forward
        self._model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, 330.0, -65.0),         # Chin (Below nose = +Y)
            (-225.0, -170.0, -135.0),    # Left Eye Corner (Camera Left = -X, Above Nose = -Y)
            (225.0, -170.0, -135.0),     # Right Eye Corner (Camera Right = +X, Above Nose = -Y)
            (-150.0, 150.0, -125.0),     # Left Mouth Corner (Camera Left = -X, Below Nose = +Y)
            (150.0, 150.0, -125.0)       # Right Mouth Corner (Camera Right = +X, Below Nose = +Y)
        ], dtype=np.float64)
        
        # Camera matrix (will be updated based on image size)
        self._camera_matrix: Optional[np.ndarray] = None
        self._dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion
    
    def _get_camera_matrix(self, image_width: int, image_height: int) -> np.ndarray:
        """
        Get camera intrinsic matrix.
        
        Args:
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            3x3 camera matrix
        """
        focal_length = image_width
        center = (image_width / 2, image_height / 2)
        
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        return camera_matrix
    
    def estimate(self, face: FaceLandmarks) -> Tuple[float, float, float]:
        """
        Estimate head pose from facial landmarks.
        
        Args:
            face: FaceLandmarks object
            
        Returns:
            Tuple of (pitch, yaw, roll) in degrees
            - Pitch: Up/Down (positive = looking up)
            - Yaw: Left/Right (positive = looking right)
            - Roll: Tilt (positive = tilting right)
        """
        # Get 2D image points
        # MediaPipe Landmarks:
        # NOSE_TIP (1)
        # CHIN (152)
        # LEFT_EYE_OUTER (263) -> Subject's Left, so CAMERA RIGHT (X+)
        # RIGHT_EYE_OUTER (33) -> Subject's Right, so CAMERA LEFT (X-)
        # LEFT_MOUTH (61) -> Subject's Right Corner (Wait, MP 61 is Right Corner?), No, MP convention:
        # 61 is Subject Right (Camera Left). 291 is Subject Left (Camera Right).
        
        # Mapping to 3D Model:
        # 0: Nose (0, 0) -> MP 1
        # 1: Chin (0, 330) -> MP 152
        # 2: Model Left (-225, -170) -> Camera Left -> Subject Right Eye (MP 33)
        # 3: Model Right (225, -170) -> Camera Right -> Subject Left Eye (MP 263)
        # 4: Model Mouse Left (-150, 150) -> Camera Left -> Subject Right Mouth (MP 61)
        # 5: Model Mouse Right (150, 150) -> Camera Right -> Subject Left Mouth (MP 291)
        
        image_points = np.array([
            face.pixel_landmarks[mp_config.NOSE_TIP],      # Nose
            face.pixel_landmarks[mp_config.CHIN],          # Chin
            face.pixel_landmarks[mp_config.RIGHT_EYE_OUTER], # Model Left (Camera Left) matches Subj Right Eye
            face.pixel_landmarks[mp_config.LEFT_EYE_OUTER],  # Model Right (Camera Right) matches Subj Left Eye
            face.pixel_landmarks[mp_config.LEFT_MOUTH],      # Model Mouth Left (Camera Left) matches Subj Right Mouth (61)
            face.pixel_landmarks[mp_config.RIGHT_MOUTH]      # Model Mouth Right (Camera Right) matches Subj Left Mouth (291)
        ], dtype=np.float64)
        
        # Get camera matrix
        camera_matrix = self._get_camera_matrix(face.image_width, face.image_height)
        
        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self._model_points,
            image_points,
            camera_matrix,
            self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return self._current_pitch, self._current_yaw, self._current_roll
        
        # Convert rotation vector to rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Convert rotation matrix to Euler angles
        pitch, yaw, roll = rotation_matrix_to_euler_angles(rotation_matrix)
        
        # Add to history and smooth
        self._pitch_history.append(pitch)
        self._yaw_history.append(yaw)
        self._roll_history.append(roll)
        
        # Keep history limited
        for history in [self._pitch_history, self._yaw_history, self._roll_history]:
            if len(history) > self.smoothing_window:
                history.pop(0)
        
        # Smooth values
        self._current_pitch = sum(self._pitch_history) / len(self._pitch_history) if self._pitch_history else pitch
        self._current_yaw = sum(self._yaw_history) / len(self._yaw_history) if self._yaw_history else yaw
        self._current_roll = sum(self._roll_history) / len(self._roll_history) if self._roll_history else roll
        
        return self._current_pitch, self._current_yaw, self._current_roll
    
    def is_head_down(self, pitch: float = None, threshold: float = None) -> bool:
        """
        Check if head is tilted down (drowsy).
        
        Args:
            pitch: Pitch angle (uses current if None)
            threshold: Custom threshold (uses config if None)
            
        Returns:
            True if head is down
        """
        if pitch is None:
            pitch = self._current_pitch
        if threshold is None:
            threshold = config.HEAD_PITCH_THRESHOLD
        
        # Negative pitch means head down
        return pitch < -threshold
    
    def is_looking_away(self, yaw: float = None, threshold: float = None) -> bool:
        """
        Check if driver is looking away (distracted).
        
        Args:
            yaw: Yaw angle (uses current if None)
            threshold: Custom threshold (uses config if None)
            
        Returns:
            True if looking away
        """
        if yaw is None:
            yaw = self._current_yaw
        if threshold is None:
            threshold = config.HEAD_YAW_THRESHOLD
        
        return abs(yaw) > threshold
    
    def get_pose_status(self) -> dict:
        """
        Get current pose status.
        
        Returns:
            Dictionary with pose information
        """
        return {
            'pitch': self._current_pitch,
            'yaw': self._current_yaw,
            'roll': self._current_roll,
            'head_down': self.is_head_down(),
            'looking_away': self.is_looking_away()
        }
    
    def get_direction_text(self) -> str:
        """
        Get human-readable direction text.
        
        Returns:
            Direction description string
        """
        pitch = self._current_pitch
        yaw = self._current_yaw
        
        vertical = ""
        if pitch < -20:
            vertical = "Looking Down"
        elif pitch > 20:
            vertical = "Looking Up"
        else:
            vertical = "Forward"
        
        horizontal = ""
        if yaw < -20:
            horizontal = "Left"
        elif yaw > 20:
            horizontal = "Right"
        else:
            horizontal = ""
        
        if horizontal:
            return f"{vertical} {horizontal}"
        return vertical
    
    def draw_pose_axes(self, image: np.ndarray, face: FaceLandmarks, 
                       axis_length: int = 100) -> np.ndarray:
        """
        Draw 3D axes on the face to visualize head pose.
        
        Args:
            image: Input image
            face: FaceLandmarks object
            axis_length: Length of axes in pixels
            
        Returns:
            Image with axes drawn
        """
        # Get nose tip as origin
        nose_tip = face.pixel_landmarks[mp_config.NOSE_TIP]
        
        # Get camera matrix
        camera_matrix = self._get_camera_matrix(face.image_width, face.image_height)
        
        # Get 2D image points
        image_points = np.array([
            face.pixel_landmarks[mp_config.NOSE_TIP],
            face.pixel_landmarks[mp_config.CHIN],
            face.pixel_landmarks[mp_config.LEFT_EYE_OUTER],
            face.pixel_landmarks[mp_config.RIGHT_EYE_OUTER],
            face.pixel_landmarks[mp_config.LEFT_MOUTH],
            face.pixel_landmarks[mp_config.RIGHT_MOUTH]
        ], dtype=np.float64)
        
        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self._model_points,
            image_points,
            camera_matrix,
            self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return image
        
        # Define axis points in 3D
        axis_points = np.array([
            [0, 0, 0],                    # Origin
            [axis_length, 0, 0],          # X axis (red)
            [0, axis_length, 0],          # Y axis (green)
            [0, 0, axis_length]           # Z axis (blue)
        ], dtype=np.float64)
        
        # Project 3D points to 2D
        projected_points, _ = cv2.projectPoints(
            axis_points,
            rotation_vector,
            translation_vector,
            camera_matrix,
            self._dist_coeffs
        )
        
        origin = tuple(map(int, projected_points[0].ravel()))
        x_end = tuple(map(int, projected_points[1].ravel()))
        y_end = tuple(map(int, projected_points[2].ravel()))
        z_end = tuple(map(int, projected_points[3].ravel()))
        
        # Draw axes
        cv2.line(image, origin, x_end, (0, 0, 255), 3)  # X - Red
        cv2.line(image, origin, y_end, (0, 255, 0), 3)  # Y - Green
        cv2.line(image, origin, z_end, (255, 0, 0), 3)  # Z - Blue
        
        return image
    
    def reset(self) -> None:
        """Reset history and current values"""
        self._pitch_history.clear()
        self._yaw_history.clear()
        self._roll_history.clear()
        self._current_pitch = 0.0
        self._current_yaw = 0.0
        self._current_roll = 0.0


# Create default instance
head_pose_estimator = HeadPoseEstimator()


def get_head_pose_estimator() -> HeadPoseEstimator:
    """Get head pose estimator instance"""
    return head_pose_estimator


if __name__ == "__main__":
    print("Head Pose Estimator Test")
    print(f"Pitch Threshold: {config.HEAD_PITCH_THRESHOLD}°")
    print(f"Yaw Threshold: {config.HEAD_YAW_THRESHOLD}°")
    
    estimator = HeadPoseEstimator()
    
    # Simulate some pose values
    test_pitches = [0, -10, -20, -35, -40, -30, -15, 0, 10]
    
    for pitch in test_pitches:
        estimator._pitch_history.append(pitch)
        smoothed = sum(estimator._pitch_history) / len(estimator._pitch_history)
        head_down = smoothed < -config.HEAD_PITCH_THRESHOLD
        print(f"Pitch: {pitch}°, Smoothed: {smoothed:.1f}°, Head Down: {head_down}")
