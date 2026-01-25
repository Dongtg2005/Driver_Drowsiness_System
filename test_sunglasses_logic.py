
import sys
import os
sys.path.append(os.getcwd())

from src.ai_core.drowsiness_fusion import DrowsinessFusion
from config import config

def test_logic():
    print("🧪 INITIALIZING LOGIC TEST SIMULATION...")
    print("========================================")
    
    # Init Fusion Engine
    fusion = DrowsinessFusion()
    
    # Define Scenarios
    scenarios = [
        {
            "name": "RESOURCE 1: KHÔNG ĐEO KÍNH (Chuẩn)",
            "sunglasses": False,
            "ear": 0.15, # Mắt nhắm
            "pitch": -5.0, # Đầu thẳng
            "desc": "Mắt nhắm, đầu thẳng. Score phải tăng nhanh (Weight 1.0)."
        },
        {
            "name": "RESOURCE 2: ĐEO KÍNH + ĐẦU THẲNG (False Positive Check)",
            "sunglasses": True,
            "ear": 0.15, # Mắt nhắm (hoặc do kính đen)
            "pitch": -5.0, # Đầu thẳng
            "desc": "Mắt nhắm nhưng có kính. Score phải tăng CHẬM (Weight 0.5)."
        },
        {
            "name": "RESOURCE 3: ĐEO KÍNH + GẬT ĐẦU (True Positive/Fallback)",
            "sunglasses": True,
            "ear": 0.15, 
            "pitch": -25.0, # Cúi đầu (> 20 độ)
            "desc": "Mắt nhắm + Cúi đầu. Score phải tăng RẤT NHANH (Weight 0.5 + Head Weight)."
        }
    ]
    
    for scen in scenarios:
        print(f"\n▶ {scen['name']}")
        print(f"   Context: {scen['desc']}")
        
        # Reset score
        fusion.score = 0
        fusion.head_tracker.is_distracted = False # Reset state
        
        # Simulate 30 frames (1 second)
        print("   Running simulation for 30 frames...")
        initial_score = fusion.score
        
        for i in range(30):
            # Cần simulate yaw để head tracker không bị lỗi logic (cho yaw=0 an toàn)
            fusion.update(
                ear=scen['ear'],
                mar=0.0,
                is_yawning=False,
                pitch=scen['pitch'],
                yaw=0.0,
                is_smiling=False,
                manual_sunglasses_mode=scen['sunglasses']
            )
            
        final_score = fusion.score
        print(f"   🏁 Score sau 1s: {final_score}")
        
        # Validation Logic
        if scen['name'].startswith("RESOURCE 1"):
            # Normal: ~30 frames * 1 weight = ~30
            if final_score >= 25: print("   ✅ PASSED: Hệ thống phản ứng nhanh.")
            else: print("   ❌ FAILED: Phản ứng quá chậm.")
            
        elif scen['name'].startswith("RESOURCE 2"):
            # Sunglasses: ~30 frames * 0.5 weight = ~15
            # Phải thấp hơn Resource 1 đáng kể
            if final_score < 20: print("   ✅ PASSED: Hệ thống đã GIẢM độ nhạy (tránh báo ảo).")
            else: print("   ❌ FAILED: Hệ thống vẫn báo động quá nhanh (Chưa giảm weight).")
            
        elif scen['name'].startswith("RESOURCE 3"):
            # Fallback: ~15 (eye) + ~60 (head distraction delay 2s? No wait logic distraction needs 2s to trigger)
            # HeadPoseTracker needs 2s (60 frames) to trigger 'is_distracted'.
            # Test chạy 30 frames thì HeadTracker chưa trigger 'is_distracted' (True), 
            # NHƯNG logic 'nod_detected' (Minima) hoặc logic Manual Boost trong update có thể chạy.
            
            # Kiểm tra xem logic Force Distraction có hoạt động không?
            # Trong code cũ: "Nếu Sunglasses và Distracted -> Weight gấp đôi"
            # Nhưng Distracted cần 2s mới active.
            
            # Ta test Nodding Detector trigger? Or simple Pitch contribution?
            # Pitch < -15 -> NodDetector might trigger if pattern matches.
            pass

    print("\n========================================")
    print("ℹ️  Lưu ý: RESOURCE 3 cần test dài hơn (>2s) để kích hoạt Head Distraction.")

if __name__ == "__main__":
    test_logic()
