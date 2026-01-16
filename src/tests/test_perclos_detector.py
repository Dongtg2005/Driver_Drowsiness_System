import unittest
import sys
import os

# Thêm đường dẫn để Python tìm thấy module src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import module cần test
from src.ai_core.perclos_detector import PerclosDetector 

class TestPerclosDetector(unittest.TestCase): # <--- BẮT BUỘC: Phải kế thừa unittest.TestCase
    
    def setUp(self):
        """Chạy trước mỗi bài test"""
        # Khởi tạo detector với history ngắn để dễ test
        self.detector = PerclosDetector(history_seconds=5, fps=30, threshold=0.25)

    def test_initialization(self): # <--- BẮT BUỘC: Tên hàm phải bắt đầu bằng 'test_'
        """Kiểm tra khởi tạo object"""
        self.assertIsNotNone(self.detector)
        self.assertEqual(self.detector.threshold, 0.25)

    def test_eyes_open_logic(self): # <--- BẮT BUỘC: Tên hàm phải bắt đầu bằng 'test_'
        """Test trường hợp mắt mở (EAR cao) -> Không buồn ngủ"""
        # Giả lập 100 frame mắt mở (EAR = 0.30 > 0.25)
        for _ in range(150):
            level = self.detector.update(ear_value=0.30)
        
        # PERCLOS phải bằng 0 (vì không nhắm mắt tí nào)
        current_perclos = self.detector.get_perclos_level()
        self.assertEqual(current_perclos, 0.0)

    def test_eyes_closed_logic(self): # <--- BẮT BUỘC: Tên hàm phải bắt đầu bằng 'test_'
        """Test trường hợp mắt nhắm (EAR thấp) -> Buồn ngủ"""
        # Giả lập 200 frame mắt nhắm (EAR = 0.15 < 0.25)
        for _ in range(200):
            self.detector.update(ear_value=0.15)
            
        current_perclos = self.detector.get_perclos_level()
        # Vì nhắm mắt liên tục, PERCLOS phải tiệm cận 1.0 (100%)
        self.assertGreater(current_perclos, 0.8)

    def test_small_eyes_real_scenario(self): # <--- Thêm hàm này
        """
        Mô phỏng đôi mắt thực tế của bạn (EAR khoảng 0.20 - 0.22).
        Nếu test này FAIL, nghĩa là ngưỡng 0.25 đang quá cao so với bạn.
        """
        print("\n--- Đang chạy thử nghiệm với Mắt Nhỏ (EAR=0.21) ---")
        
        # Giả lập 150 frame mắt bạn đang mở bình thường 
        # (nhưng vì mắt nhỏ hoặc camera xa nên EAR chỉ đạt 0.21)
        for _ in range(150):
            # Nếu ngưỡng cài đặt là 0.25, thì 0.21 sẽ bị tính là NHẮM
            self.detector.update(ear_value=0.21) 
        
        current_perclos = self.detector.get_perclos_level()
        print(f"Kết quả PERCLOS đo được: {current_perclos}")
        
        # Mong muốn: PERCLOS phải bằng 0.0 (Tỉnh táo)
        # Nếu ngưỡng sai, nó sẽ ra > 0.8 (Ngủ gật)
        self.assertLess(current_perclos, 0.1, "LỖI: Hệ thống báo ngủ gật dù đang mở mắt (0.21)!")
if __name__ == '__main__':
    unittest.main()