"""
============================================
🧮 Math Helpers (Final Version)
Driver Drowsiness Detection System
Mathematical utility functions
============================================
"""

import numpy as np
from typing import List, Tuple, Union

def euclidean_distance(point1, point2):
    """Tính khoảng cách Euclid giữa 2 điểm (2D hoặc 3D)"""
    # Chuyển đổi sang numpy array để tính toán an toàn
    p1 = np.array(point1)
    p2 = np.array(point2)
    return np.linalg.norm(p1 - p2)

def euclidean_distance_2d(x1, y1, x2, y2):
    """Tính khoảng cách 2D giữa các tọa độ rời rạc"""
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def euclidean_distance_3d(x1, y1, z1, x2, y2, z2):
    """Tính khoảng cách 3D giữa các tọa độ rời rạc"""
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def calculate_ear(eye_points):
    """
    Tính chỉ số EAR (Eye Aspect Ratio)
    eye_points: List 6 điểm mốc của mắt [(x,y), ...]
    """
    if len(eye_points) != 6:
        return 0.0

    # Các điểm mốc (Landmarks)
    p1, p2, p3, p4, p5, p6 = eye_points

    # Khoảng cách chiều dọc (Vertical)
    # ||p2 - p6||
    A = euclidean_distance(p2, p6)
    # ||p3 - p5||
    B = euclidean_distance(p3, p5)

    # Khoảng cách chiều ngang (Horizontal)
    # ||p1 - p4||
    C = euclidean_distance(p1, p4)

    if C == 0:
        return 0.0

    # Công thức EAR
    ear = (A + B) / (2.0 * C)
    return ear

def calculate_mar(mouth_points):
    """
    Tính chỉ số MAR (Mouth Aspect Ratio)
    mouth_points: Dictionary hoặc List các điểm mốc miệng
    """
    # Nếu đầu vào là dict (như trong constants cũ)
    if isinstance(mouth_points, dict):
        top = mouth_points.get('top')
        bottom = mouth_points.get('bottom')
        left = mouth_points.get('left')
        right = mouth_points.get('right')
        
        if not all([top, bottom, left, right]):
            return 0.0
            
        vertical = euclidean_distance(top, bottom)
        horizontal = euclidean_distance(left, right)
        
    # Nếu đầu vào là List điểm từ MediaPipe (List 4 điểm chủ chốt)
    elif isinstance(mouth_points, (list, tuple)) and len(mouth_points) >= 4:
        # Giả sử thứ tự: [top, bottom, left, right] hoặc các điểm cụ thể
        # Ở đây ta dùng logic tổng quát: Tìm điểm cao nhất/thấp nhất/trái nhất/phải nhất
        pts = np.array(mouth_points)
        top = pts[np.argmin(pts[:, 1])]
        bottom = pts[np.argmax(pts[:, 1])]
        left = pts[np.argmin(pts[:, 0])]
        right = pts[np.argmax(pts[:, 0])]
        
        vertical = euclidean_distance(top, bottom)
        horizontal = euclidean_distance(left, right)
    else:
        return 0.0

    if horizontal == 0: 
        return 0.0

    mar = vertical / horizontal
    return mar

def calculate_angle(point_a, point_b, point_c):
    """Tính góc giữa 3 điểm (Góc tại điểm B)"""
    a = np.array(point_a)
    b = np.array(point_b)
    c = np.array(point_c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return np.degrees(angle)

def normalize_vector(vector):
    """Chuẩn hóa vector về độ dài 1"""
    norm = np.linalg.norm(vector)
    if norm == 0: 
        return vector
    return vector / norm

def rotation_matrix_to_euler_angles(R):
    """Chuyển đổi ma trận xoay sang góc Euler (Pitch, Yaw, Roll)"""
    sy = np.sqrt(R[0, 0] * R[0, 0] +  R[1, 0] * R[1, 0])
    singular = sy < 1e-6

    if not singular:
        x = np.arctan2(R[2, 1], R[2, 2])
        y = np.arctan2(-R[2, 0], sy)
        z = np.arctan2(R[1, 0], R[0, 0])
    else:
        x = np.arctan2(-R[1, 2], R[1, 1])
        y = np.arctan2(-R[2, 0], sy)
        z = 0

    return np.degrees(np.array([x, y, z]))

def moving_average(new_value, history, window_size=5):
    """Tính trung bình động"""
    if not isinstance(history, list):
        history = []
    
    history.append(new_value)
    if len(history) > window_size:
        history.pop(0)
    
    return sum(history) / len(history)

def clamp(value, min_val, max_val):
    """Giới hạn giá trị"""
    return max(min_val, min(value, max_val))

def map_range(value, in_min, in_max, out_min, out_max):
    """Ánh xạ giá trị"""
    return (value - in_min) * (out_max - out_min) / (in_max - in_min + 1e-6) + out_min

def get_centroid(points):
    """Tính tâm của tập hợp điểm"""
    if not points: return (0, 0)
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return (sum(x) / len(points), sum(y) / len(points))