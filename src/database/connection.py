import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Tải các biến môi trường từ file .env ở thư mục gốc của dự án
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Kiểm tra xem các biến môi trường cần thiết đã được đặt chưa
if not DB_NAME:
    raise ValueError("DB_NAME is not set in the environment variables.")

# Tạo chuỗi kết nối theo chuẩn của SQLAlchemy
# Format: mysql+<driver>://<user>:<password>@<host>:<port>/<dbname>
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Tạo engine - đây là điểm kết nối trung tâm đến database.
# echo=True sẽ in ra các câu lệnh SQL mà SQLAlchemy thực thi, hữu ích cho việc debug.
# Bạn có thể đặt echo=False khi triển khai sản phẩm.
engine = create_engine(DATABASE_URL, echo=True)

# Tạo một lớp Session đã được cấu hình.
# Lớp này sẽ được dùng để tạo các phiên (session) giao tiếp với database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo một lớp Base mà tất cả các lớp Model sẽ kế thừa.
# SQLAlchemy sử dụng lớp này để "đăng ký" các model và ánh xạ chúng tới các bảng trong database.
Base = declarative_base()

def get_db():
    """
    Hàm helper để tạo và đóng session database một cách an toàn.
    Sử dụng với `with` statement để đảm bảo session luôn được đóng.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
