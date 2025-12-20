# 🚗 Driver Drowsiness Detection System

Hệ thống phát hiện lái xe ngủ gật sử dụng Computer Vision và AI.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-blue.svg)

## 📋 Mục Lục

- [Tính năng](#-tính-năng)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#-cấu-hình)
- [Sử dụng](#-sử-dụng)
- [Kiến trúc](#-kiến-trúc)
- [API Documentation](#-api-documentation)

## ✨ Tính năng

### 🔐 Quản lý tài khoản
- Đăng ký/Đăng nhập
- Cập nhật thông tin cá nhân
- Mật khẩu được mã hóa bcrypt

### 👁️ Giám sát thời gian thực
- Phát hiện **mắt nhắm** (EAR - Eye Aspect Ratio)
- Phát hiện **ngáp** (MAR - Mouth Aspect Ratio)
- Phát hiện **gục đầu** (Head Pose Estimation)
- Hiển thị thông số realtime trên màn hình

### 🚨 Hệ thống cảnh báo 3 cấp độ
| Cấp độ | Điều kiện | Âm thanh |
|--------|-----------|----------|
| 1 | Nhắm mắt 2-3 giây | Beep nhẹ |
| 2 | Nhắm mắt 3-5 giây | Alarm |
| 3 | Nhắm mắt >5 giây | Siren khẩn cấp |

### 📊 Báo cáo & Thống kê
- Lịch sử cảnh báo theo ngày/tuần/tháng
- Biểu đồ trực quan
- Export báo cáo

## 💻 Yêu cầu hệ thống

- **OS**: Windows 10/11, macOS, Linux
- **Python**: 3.9+
- **RAM**: 4GB+ (khuyến nghị 8GB)
- **CPU**: Intel Core i5+ hoặc tương đương
- **Camera**: Webcam hoặc Camera hồng ngoại
- **MySQL**: 8.0+

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone https://github.com/yourusername/driver-drowsiness-system.git
cd driver-drowsiness-system
```

### 2. Tạo môi trường ảo
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình Database

#### Tạo database MySQL:
```bash
mysql -u root -p < database.sql
```

#### Hoặc chạy trong MySQL Workbench:
```sql
SOURCE /path/to/database.sql;
```

### 5. Cấu hình môi trường
```bash
# Copy file .env.example thành .env
cp .env.example .env

# Chỉnh sửa thông tin database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=drowsiness_db
DB_USER=root
DB_PASSWORD=your_password
```

### 6. Chạy ứng dụng
```bash
python main.py
```

## ⚙️ Cấu hình

### Ngưỡng phát hiện (config.py)

```python
# Ngưỡng nhắm mắt
EAR_THRESHOLD = 0.25

# Ngưỡng ngáp  
MAR_THRESHOLD = 0.7

# Ngưỡng cúi đầu (độ)
HEAD_PITCH_THRESHOLD = 30
```

### Tùy chỉnh cảnh báo

```python
# Số frame liên tiếp để kích hoạt
EAR_CONSEC_FRAMES = 20  # ~0.67 giây ở 30 FPS

# Âm lượng (0.0 - 1.0)
ALERT_VOLUME = 0.8
```

## 📖 Sử dụng

### Đăng nhập
1. Mở ứng dụng
2. Nhập username/password
3. Nhấn "Đăng nhập"

### Bắt đầu giám sát
1. Nhấn nút "Start Monitoring"
2. Camera sẽ tự động bật
3. Hệ thống bắt đầu phân tích

### Xem báo cáo
1. Chọn tab "Dashboard"
2. Chọn khoảng thời gian
3. Xem thống kê chi tiết

## 🏗️ Kiến trúc

```
driver-drowsiness-system/
├── main.py                 # Entry point
├── config.py               # Cấu hình
├── src/
│   ├── database/           # Database connection
│   ├── models/             # Data models
│   ├── views/              # GUI (Tkinter)
│   ├── controllers/        # Business logic
│   ├── ai_core/            # AI algorithms
│   └── utils/              # Utilities
├── assets/
│   ├── sounds/             # Alert sounds
│   └── images/             # Icons, logos
└── tests/                  # Unit tests
```

### Mô hình MVC

```
┌─────────────────────────────────────────────────────────────┐
│                          VIEW                                │
│  (login_view, camera_view, dashboard_view, settings_view)   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       CONTROLLER                             │
│  (auth_controller, monitor_controller, settings_controller) │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         MODEL                                │
│          (user_model, alert_model, db_connection)           │
└─────────────────────────────────────────────────────────────┘
```

## 🧮 Thuật toán

### EAR (Eye Aspect Ratio)

$$EAR = \frac{||p_2 - p_6|| + ||p_3 - p_5||}{2 \times ||p_1 - p_4||}$$

- Mắt mở: EAR ≈ 0.30 - 0.35
- Mắt nhắm: EAR < 0.25

### MAR (Mouth Aspect Ratio)

$$MAR = \frac{||p_{top} - p_{bottom}||}{||p_{left} - p_{right}||}$$

- Bình thường: MAR < 0.5
- Ngáp: MAR > 0.7

## 🧪 Testing

```bash
# Chạy tất cả tests
pytest tests/

# Chạy với coverage
pytest --cov=src tests/
```

## 📝 License

MIT License - xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## 👥 Đóng góp

1. Fork repo
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Liên hệ

- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

---

⭐ Nếu dự án hữu ích, hãy cho một star nhé!
