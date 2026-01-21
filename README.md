# 🚗 Driver Drowsiness Detection System

Hệ thống phát hiện lái xe ngủ gật sử dụng Computer Vision và AI.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-blue.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)
![Alembic](https://img.shields.io/badge/Alembic-1.13-blue.svg)

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

> Khuyến nghị dùng **Python 3.9 – 3.11** để tương thích tốt với `mediapipe`.

### 0. Kiểm tra Python & pip

**Windows (khuyến nghị PowerShell):**
```powershell
python --version
python -m pip --version
```


### 1. Clone repository
```bash
git clone https://github.com/yourusername/driver-drowsiness-system.git Driver_Drowsiness_System
cd Driver_Drowsiness_System
```

### 2. Tạo môi trường ảo (venv)

**Windows (PowerShell):**
```powershell
# Tạo venv
python -m venv venv

# Nâng cấp pip / setuptools / wheel
python -m pip install --upgrade pip setuptools wheel

# Nếu bị chặn chạy script: chỉ bật tạm trong phiên hiện tại
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Kích hoạt venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```bat
python -m venv venv
python -m pip install --upgrade pip setuptools wheel
venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv venv
python3 -m pip install --upgrade pip setuptools wheel
source venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Tạo file cấu hình .env
Tạo file `.env` trong thư mục gốc với nội dung:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=drowsiness_db
DB_USER=root
DB_PASSWORD=
```

### 5. Cấu hình Database MySQL

Hệ thống sử dụng **Alembic** để quản lý và cập nhật cấu trúc database một cách tự động.

#### Bước 1: Tạo Database Rỗng
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS drowsiness_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### Bước 2: Áp dụng Cấu trúc (Migration)
```bash
# Đảm bảo venv đã active
python -m alembic upgrade head
```

> **Windows lưu ý:** nếu dùng Workbench, hãy chọn đúng file `database.sql` trong thư mục dự án.

### 6. Chạy ứng dụng
```bash
python main.py
```

### 7. Thoát môi trường ảo
```bash
deactivate
```

### 7. Đăng nhập test
```
Username: admin
Password: admin123
```

---

## 🔧 Troubleshooting

### Lỗi MediaPipe trên Python 3.13+
```bash
pip uninstall mediapipe
pip install mediapipe==0.10.9
```

### Lỗi MySQL Access Denied
- Kiểm tra lại password trong file `.env`
- Đảm bảo MySQL Server đang chạy
- Thử kết nối thủ công: `mysql -u root -p`

### Lỗi bcrypt
```bash
pip install bcrypt --force-reinstall
```

### Reset mật khẩu admin
```bash
python reset_password.py
```

### Lỗi Camera không mở được
- Kiểm tra webcam đã kết nối chưa
- Đóng các ứng dụng khác đang dùng camera
- Thử đổi camera index trong Settings

---

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
Driver_Drowsiness_System/
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
