import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from src.config.database import DATABASE_URL

# Tạo engine - đây là điểm kết nối trung tâm đến database.
# pool_pre_ping=True: Kiểm tra kết nối trước khi dùng (tránh lỗi 'MySQL server has gone away')
# pool_recycle=1800: Tái tạo kết nối mỗi 30 phút (chuẩn production cho web/cloud)
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Tắt echo log để giảm nhiễu trên cloud console
    pool_pre_ping=True,
    pool_recycle=1800
)

# Tạo một lớp Session đã được cấu hình.
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
