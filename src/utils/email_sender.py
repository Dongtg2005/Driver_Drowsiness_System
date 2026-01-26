"""
============================================
📧 Email Sender Utility
Driver Drowsiness Detection System
============================================
"""
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import config
from src.utils.logger import logger

class EmailSender:
    """
    Lớp tiện ích để gửi email cảnh báo bất đồng bộ.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EmailSender, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.last_sent_time = 0
        self.cooldown = config.EMAIL_COOLDOWN
        
    def send_alert_email(self, alert_level: str, details: str = "", recipient: str = None):
        """
        Gửi email cảnh báo (Chạy trên luồng riêng để không chặn chương trình chính).
        """
        # Kiểm tra cooldown
        current_time = time.time()
        if current_time - self.last_sent_time < self.cooldown:
            logger.info("⏳ Email notification skipped due to cooldown.")
            return

        # Xác định người nhận (Ưu tiên tham số truyền vào > config)
        target_email = recipient if recipient else config.RECIPIENT_EMAIL

        # Kiểm tra cấu hình
        if not config.SMTP_SERVER or not config.SENDER_EMAIL or not target_email:
            logger.warning("⚠️ Email configuration/recipient missing. Cannot send alert.")
            return

        # Cập nhật cooldown NGAY LẬP TỨC để chặn các call tiếp theo (tránh race condition)
        self.last_sent_time = current_time

        # Tạo luồng gửi mail
        thread = threading.Thread(
            target=self._send_async,
            args=(alert_level, details, current_time, target_email),
            daemon=True
        )
        thread.start()

    def _send_async(self, alert_level: str, details: str, timestamp: float, recipient: str):
        try:
            msg = MIMEMultipart()
            msg['From'] = config.SENDER_EMAIL
            msg['To'] = recipient
            msg['Subject'] = f"🚨 CẢNH BÁO KHẨN CẤP: {alert_level} - Driver Drowsiness System"

            body = f"""
            <h3>HỆ THỐNG CẢNH BÁO TÀI XẾ BUỒN NGỦ</h3>
            <p><strong>Cấp độ cảnh báo:</strong> <span style="color:red;">{alert_level}</span></p>
            <p><strong>Thời gian:</strong> {time.ctime(timestamp)}</p>
            <p><strong>Chi tiết:</strong> {details}</p>
            <hr>
            <p>Đây là tin nhắn tự động. Vui lòng kiểm tra tình trạng tài xế ngay lập tức.</p>
            """
            
            msg.attach(MIMEText(body, 'html'))

            # Kết nối và gửi
            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
            server.starttls()
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
            text = msg.as_string()
            server.sendmail(config.SENDER_EMAIL, recipient, text)
            server.quit()
            
            logger.info(f"✅ Email alert sent to {recipient}")
            self.last_sent_time = timestamp # Cập nhật cooldown sau khi gửi thành công
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")

# Global Instance
email_sender = EmailSender()
