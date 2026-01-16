"""
============================================
📝 Logger Utility
Driver Drowsiness Detection System
Centralized logging configuration
============================================
"""

import logging
import os
from datetime import datetime
from typing import Optional
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config


class Logger:
    """
    Centralized logger class with file and console output.
    """
    
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self) -> None:
        """Initialize the logger with handlers"""
        
        # Create logs directory if not exists
        if not os.path.exists(config.LOGS_DIR):
            os.makedirs(config.LOGS_DIR)
        
        # Create logger
        self._logger = logging.getLogger('DrowsinessDetection')
        self._logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
        
        # Prevent duplicate handlers
        if self._logger.handlers:
            return
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler (daily rotating)
        log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
        log_filepath = os.path.join(config.LOGS_DIR, log_filename)
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        # Show debug logs on console when in DEBUG mode
        console_handler.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
        
        self._logger.info("=" * 50)
        self._logger.info("Logger initialized")
        self._logger.info(f"Log file: {log_filepath}")
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        if self._logger:
            self._logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message"""
        if self._logger:
            self._logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        if self._logger:
            self._logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message"""
        if self._logger:
            self._logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message"""
        if self._logger:
            self._logger.critical(message)
    
    def exception(self, message: str) -> None:
        """Log exception with traceback"""
        if self._logger:
            self._logger.exception(message)
    
    def log_alert(self, alert_type: str, level: int, ear: float = None, 
                  mar: float = None, pitch: float = None, perclos: float = None) -> None:
        """
        Log drowsiness alert with details.
        
        Args:
            alert_type: Type of alert (DROWSY, YAWN, HEAD_DOWN)
            level: Alert level (1, 2, 3)
            ear: Eye Aspect Ratio value
            mar: Mouth Aspect Ratio value
            pitch: Head pitch angle
        """
        details = f"Type={alert_type}, Level={level}"
        if ear is not None:
            details += f", EAR={ear:.3f}"
        if mar is not None:
            details += f", MAR={mar:.3f}"
        if pitch is not None:
            details += f", Pitch={pitch:.1f}°"
        if perclos is not None:
            details += f", PERCLOS={perclos:.3f}"
        
        self._logger.warning(f"🚨 ALERT: {details}")
    
    def log_session_start(self, user_id: int) -> None:
        """Log monitoring session start"""
        self._logger.info(f"📹 Monitoring session started - User ID: {user_id}")
    
    def log_session_end(self, user_id: int, duration: float, alerts: int) -> None:
        """Log monitoring session end"""
        self._logger.info(
            f"📹 Monitoring session ended - User ID: {user_id}, "
            f"Duration: {duration:.1f}s, Total Alerts: {alerts}"
        )
    
    def log_login(self, username: str, success: bool) -> None:
        """Log login attempt"""
        status = "SUCCESS" if success else "FAILED"
        self._logger.info(f"🔐 Login {status} - Username: {username}")
    
    def log_performance(self, fps: float, processing_time: float) -> None:
        """Log performance metrics"""
        self._logger.debug(f"📊 Performance - FPS: {fps:.1f}, Processing: {processing_time:.1f}ms")


# Create singleton instance
logger = Logger()


# Convenience functions
def get_logger() -> Logger:
    """Get logger instance"""
    return logger


def debug(message: str) -> None:
    logger.debug(message)


def info(message: str) -> None:
    logger.info(message)


def warning(message: str) -> None:
    logger.warning(message)


def error(message: str) -> None:
    logger.error(message)


def critical(message: str) -> None:
    logger.critical(message)


if __name__ == "__main__":
    # Test logger
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    logger.log_alert("DROWSY", 2, ear=0.22, mar=0.45, pitch=15.5)
