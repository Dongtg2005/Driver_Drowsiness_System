# 🚗 Driver Drowsiness Detection System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.2+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**Hệ thống phát hiện tài xế ngủ gật (Driver Drowsiness Detection System)** là một ứng dụng Desktop mạnh mẽ được xây dựng bằng Python, sử dụng các thuật toán Thị giác máy tính (Computer Vision) tiên tiến để giám sát trạng thái của người lái xe trong thời gian thực. Hệ thống giúp ngăn chặn tai nạn giao thông bằng cách phát hiện các dấu hiệu mệt mỏi như nhắm mắt, ngáp và gục đầu, sau đó đưa ra cảnh báo tức thì.

---

## 📋 Mục Lục

- [Giới thiệu](#-giới-thiệu)
- [Tính năng chính](#-tính-năng)
- [Công nghệ sử dụng](#-công-nghệ)
- [Cài đặt & Hướng dẫn chạy](#-cài-đặt)
- [Kiến trúc Hệ thống](#-kiến-trúc)
- [Nguyên lý hoạt động](#-nguyên-lý)
- [Các chỉ số kỹ thuật](#-chỉ-số)
- [Sơ đồ CSDL](#-cơ-sở-dữ-liệu)
- [Đóng góp](#-đóng-góp)

---

## ✨ Tính năng

### 1. 👁️ Giám sát Thời gian thực (Real-time Monitoring)
*   **Phát hiện Nhắm mắt (Drowsiness):** Sử dụng chỉ số EAR (Eye Aspect Ratio) để đo độ mở của mắt. Phát hiện nhanh chóng các tình huống nhắm mắt lâu (> 0.7s) hoặc chớp mắt chậm.
*   **Phát hiện Ngáp (Yawning):** Sử dụng chỉ số MAR (Mouth Aspect Ratio) để đo độ mở miệng, phân biệt giữa nói chuyện và ngáp mệt mỏi.
*   **Phát hiện Gục đầu (Head Nodding):** Ước lượng tư thế đầu 3D (Head Pose Estimation) để phát hiện hành vi cúi gục đầu do buồn ngủ hoặc quay mặt mất tập trung.

### 2. 🚨 Hệ thống Cảnh báo Đa cấp độ (Multi-level Alert)
Hệ thống phản ứng thông minh dựa trên mức độ nghiêm trọng:
*   **Level 1 (Warning):** Nhắc nhở nhẹ nhàng (âm thanh "Beep") khi có dấu hiệu chớm buồn ngủ.
*   **Level 2 (Alarm):** Báo động lớn khi phát hiện ngủ gật rõ ràng.
*   **Level 3 (Critical):** Còi hú khẩn cấp (Siren) và cảnh báo bằng giọng nói (Text-to-Speech) khi tình trạng nguy hiểm kéo dài.

### 3. 🎯 Cá nhân hóa (Calibration)
*   Tính năng **Hiệu chuẩn (Calibration)** thông minh trong 5 giây đầu tiên.
*   Hệ thống học đặc điểm khuôn mặt của từng tài xế để thiết lập ngưỡng (Threshold) riêng, giúp giảm thiểu báo động giả đối với người có mắt nhỏ hoặc đeo kính.

### 4. 📊 Báo cáo & Thống kê
*   **Dashboard trực quan:** Biểu đồ thống kê tần suất buồn ngủ theo ngày/tuần.
*   **Lịch sử chi tiết:** Xem lại toàn bộ sự kiện vi phạm kèm thời gian và loại cảnh báo.

### 5. 🔐 Quản lý Người dùng
*   Đăng ký/Đăng nhập bảo mật (Mã hóa mật khẩu bằng `BCrypt`).
*   Lưu trữ cài đặt riêng cho từng người dùng.

---

## 🛠️ Công nghệ

*   **Ngôn ngữ:** Python 3.9+
*   **Vision AI:**
    *   **MediaPipe Face Mesh:** Trích xuất 468 điểm mốc khuôn mặt 3D tốc độ cao (chạy tốt trên CPU).
    *   **OpenCV:** Xử lý hình ảnh và video stream.
*   **Giao diện (GUI):** **CustomTkinter** (Hiện đại, hỗ trợ Dark Mode).
*   **Database:**
    *   **MySQL:** Lưu trữ dữ liệu bền vững.
    *   **SQLAlchemy (ORM):** Tương tác DB an toàn.
    *   **Alembic:** Quản lý phiên bản Database (Migrations).
*   **Âm thanh:** Pygame (Alerts) & pyttsx3 (Text-to-Speech).

---

## 🚀 Cài đặt

### Yêu cầu tiên quyết
*   Python 3.9 đến 3.11 (MediaPipe hoạt động ổn định nhất trên các phiên bản này).
*   MySQL Server đã được cài đặt và đang chạy.

### Bước 1: Clone Repository
```bash
git clone https://github.com/your-repo/driver-drowsiness.git
cd Driver_Drowsiness_System
```

### Bước 2: Tạo môi trường ảo (Khuyến nghị)
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình Môi trường
Tạo file `.env` tại thư mục gốc và điền thông tin MySQL của bạn:
```ini
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=drowsiness_db
```

### Bước 5: Khởi tạo Database
Sử dụng Alembic để tạo bảng tự động:
```bash
# Tạo DB nếu chưa có
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS drowsiness_db;"

# Chạy migration
alembic upgrade head
```

### Bước 6: Chạy ứng dụng
```bash
python main.py
```

---

## 🏗️ Kiến trúc Hệ thống

Dự án áp dụng mô hình **MVC (Model-View-Controller)** chuyên nghiệp:

```
Driver_Drowsiness_System/
├── src/
│   ├── ai_core/            # Xử lý thị giác máy tính & AI (Face Mesh, Fusion)
│   ├── controllers/        # Logic điều khiển & Đa luồng (MonitorController)
│   ├── models/             # Định nghĩa dữ liệu (User, Alert)
│   ├── views/              # Giao diện người dùng (GUI)
│   ├── database/           # Kết nối CSDL
│   └── utils/              # Tiện ích (Logger, Audio, Toast)
├── assets/                 # Tài nguyên (Âm thanh, Hình ảnh)
├── migrations/             # Alembic versions
├── config.py               # File cấu hình trung tâm
└── main.py                 # Điểm khởi chạy chương trình
```

---

## 🧮 Nguyên lý Hoạt động & Chỉ số

### 1. Eye Aspect Ratio (EAR)
Đo độ mở của mắt.
$$EAR = \frac{||p_2 - p_6|| + ||p_3 - p_5||}{2 \times ||p_1 - p_4||}$$
*   **Logic:** Nếu `EAR < Threshold` (ví dụ 0.25) liên tục trong `N` frames $\rightarrow$ Cảnh báo Buồn ngủ.

### 2. Mouth Aspect Ratio (MAR)
Đo độ mở của miệng để phát hiện ngáp.
$$MAR = \frac{||p_{top} - p_{bottom}||}{||p_{left} - p_{right}||}$$
*   **Logic:** Nếu `MAR > Threshold` (ví dụ 0.70) $\rightarrow$ Cảnh báo Ngáp.

### 3. Sensor Fusion (Hợp nhất Cảm biến)
Thuật toán ưu việt kết hợp cả 3 chỉ số:
`Alert Level = Function(EAR, MAR, Head_Pitch, Head_Yaw, History)`
Giúp giảm đáng kể tỷ lệ báo động giả so với các hệ thống chỉ dùng EAR đơn thuần.

---

## 🔍 Troubleshooting (Sửa lỗi thường gặp)

**Q: Lỗi `ModuleNotFoundError: No module named 'mediapipe'`?**
A: Đảm bảo bạn đang dùng Python < 3.12. Chạy `python --version` để kiểm tra.

**Q: Camera không mở được?**
A: Kiểm tra xem có ứng dụng nào khác (Zoom, Teams) đang chiếm camera không. Thử thay đổi `CAMERA_INDEX` trong `config.py`.

**Q: Database lỗi kết nối?**
A: Kiểm tra service MySQL đã bật chưa và thông tin trong file `.env` đã chính xác chưa.

---

## 👥 Tác giả

Dự án được thực hiện bởi [Tên Bạn/Nhóm].
Nếu có câu hỏi hoặc đóng góp, vui lòng tạo Issue hoặc Pull Request.

**License:** MIT
