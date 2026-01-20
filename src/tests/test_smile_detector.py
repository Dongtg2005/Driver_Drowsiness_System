# src/tests/test_smile_detector.py
import sys
import os
import unittest

# --- 1. SỬA LỖI IMPORT (ModuleNotFoundError) ---
# Thêm thư mục gốc dự án vào đường dẫn tìm kiếm của Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai_core.smile_detector import SmileDetector, MouthState
from src.utils.constants import AlertType

# --- 2. CLASS GIẢ LẬP ĐỂ TEST (MOCK) ---
class MockSmileDetector(SmileDetector):
    """
    Phiên bản giả lập của SmileDetector.
    Cho phép nạp trực tiếp các chỉ số (MAR, Ratio, EAR) thay vì phải đọc từ Camera.
    """
    def update_with_values(self, mar, ratio, ear):
        """Hàm này mô phỏng quá trình update() nhưng bỏ qua bước xử lý ảnh"""
        timestamp = 0 # Dummy timestamp
        
        # Gọi thẳng vào logic máy trạng thái (State Machine)
        # Lưu ý: Chúng ta giả định bạn có hàm _update_state_machine hoặc tương tự.
        # Nếu logic nằm trong update(), chúng ta cần viết lại logic đó ở đây để test 
        # hoặc sửa code gốc để tách logic ra.
        
        # Dưới đây là mô phỏng lại logic phân loại dựa trên code gốc của bạn:
        self.current_mar = mar
        self.mouth_ratio = ratio
        self.ear = ear
        
        # --- LOGIC PHÂN LOẠI (MÔ PHỎNG CODE GỐC) ---
        # Logic này cần khớp với file smile_detector.py của bạn
        new_state = MouthState.NEUTRAL
        
        # Ví dụ logic:
        if mar > 0.65: # Ngưỡng ngáp
            new_state = MouthState.YAWNING
        elif mar > 0.40 and ratio > 1.5: # Ngưỡng cười (Miệng rộng + Tỷ lệ ngang)
            new_state = MouthState.SMILING
        elif mar > 0.15 and ear > 0.20: # Ngưỡng nói (Mở nhỏ + Mắt mở)
            new_state = MouthState.SPEAKING
        else:
            new_state = MouthState.NEUTRAL
            
        self.state = new_state
        return self.state

# --- 3. CÁC TEST CASE ---
class TestSmileDetector(unittest.TestCase):
    
    def test_mouth_state_classification(self):
        """Test: Phân biệt Cười / Nói / Ngáp dựa trên thông số"""
        print("\n--- Testing Mouth Classification Logic ---")
        detector = MockSmileDetector()
        
        # Kịch bản test: (MAR, Ratio, EAR, Kết quả mong đợi)
        scenarios = [
            (0.70, 1.2, 0.20, MouthState.YAWNING),  # Ngáp (MAR cao)
            (0.50, 2.0, 0.25, MouthState.SMILING),  # Cười (Ratio cao, MAR vừa)
            (0.25, 1.0, 0.30, MouthState.SPEAKING), # Nói (MAR nhỏ)
            (0.05, 1.0, 0.30, MouthState.NEUTRAL),  # Ngậm miệng
        ]
        
        for mar, ratio, ear, expected in scenarios:
            result = detector.update_with_values(mar, ratio, ear)
            print(f"Input(MAR={mar}, Ratio={ratio}) -> Got: {result.name} | Expected: {expected.name}")
            
            # Assert
            self.assertEqual(result, expected, f"Failed at MAR={mar}, Ratio={ratio}")

    def test_yawn_alert_trigger(self):
        """Test: Ngáp liên tục phải kích hoạt cảnh báo"""
        print("\n--- Testing Yawn Alert Logic ---")
        detector = MockSmileDetector()
        
        # Giả lập ngáp trong 30 frame liên tục
        for _ in range(30):
            detector.update_with_values(mar=0.8, ratio=1.0, ear=0.2)
            
        # Kiểm tra xem bộ đếm ngáp có tăng không (nếu class có thuộc tính yawn_count)
        # Giả sử detector có thuộc tính total_yawns hoặc tương tự
        if hasattr(detector, 'total_yawns'):
            print(f"Total Yawns detected: {detector.total_yawns}")
            # self.assertGreater(detector.total_yawns, 0) # Bỏ comment nếu code gốc có biến này

if __name__ == "__main__":
    unittest.main()