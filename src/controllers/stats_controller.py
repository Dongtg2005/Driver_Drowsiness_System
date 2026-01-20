"""
======================================================
📊 Statistics Controller (SQLAlchemy Version)
Driver Drowsiness Detection System
Handles fetching statistics and history from the database.
======================================================
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.database.connection import SessionLocal
from src.models.user_model import User
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession

def get_alerts_by_date_range(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> List[AlertHistory]:
    """Fetches alerts for a user within a date range."""
    return db.query(AlertHistory).filter(
        AlertHistory.user_id == user_id,
        AlertHistory.timestamp.between(start_date, end_date)
    ).order_by(AlertHistory.timestamp.desc()).all()

def get_all_alerts(db: Session, user_id: int) -> List[AlertHistory]:
    """Fetches all alerts for a user."""
    return db.query(AlertHistory).filter(AlertHistory.user_id == user_id).order_by(AlertHistory.timestamp.desc()).all()

def get_aggregated_stats(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> Dict:
    """Calculates aggregated statistics for a user over a period."""

    # Define case statements for counting specific alert types
    drowsy_case = case((AlertHistory.alert_type == 'DROWSY', 1), else_=0)
    yawn_case = case((AlertHistory.alert_type == 'YAWN', 1), else_=0)
    head_down_case = case((AlertHistory.alert_type == 'HEAD_DOWN', 1), else_=0)

    # Query the database
    stats = db.query(
        func.count(AlertHistory.id).label('total_alerts'),
        func.sum(drowsy_case).label('drowsy_count'),
        func.sum(yawn_case).label('yawn_count'),
        func.sum(head_down_case).label('head_down_count'),
        func.avg(AlertHistory.ear_value).label('avg_ear'),
        func.avg(AlertHistory.mar_value).label('avg_mar'),
        func.max(AlertHistory.alert_level).label('max_alert_level')
    ).filter(
        AlertHistory.user_id == user_id,
        AlertHistory.timestamp.between(start_date, end_date)
    ).first()

    # Convert the result (which is a SQLAlchemy Row object) to a dictionary
    if stats and stats.total_alerts is not None:
        return {
            'total_alerts': stats.total_alerts or 0,
            'drowsy_count': int(stats.drowsy_count or 0),
            'yawn_count': int(stats.yawn_count or 0),
            'head_down_count': int(stats.head_down_count or 0),
            'avg_ear': float(stats.avg_ear or 0),
            'avg_mar': float(stats.avg_mar or 0),
            'max_alert_level': int(stats.max_alert_level or 0)
        }

    # Return a default dictionary if no stats are found
    return {
        'total_alerts': 0, 'drowsy_count': 0, 'yawn_count': 0,
        'head_down_count': 0, 'avg_ear': 0, 'avg_mar': 0, 'max_alert_level': 0
    }

def get_weekly_statistics(db: Session, user_id: int) -> List[Dict]:
    """
    Fetches daily alert counts for the last 7 days.
    Returns a list of dictionaries, e.g., [{'date': '2023-10-27', 'total_alerts': 5}, ...]
    """
    results = []
    today = datetime.now().date()
    for i in range(7):
        day = today - timedelta(days=i)
        start_of_day = datetime.combine(day, datetime.min.time())
        end_of_day = datetime.combine(day, datetime.max.time())

        count = db.query(func.count(AlertHistory.id)).filter(
            AlertHistory.user_id == user_id,
            AlertHistory.timestamp.between(start_of_day, end_of_day)
        ).scalar()

        results.append({'date': day, 'total_alerts': count or 0})

    return results

def get_session_history(db: Session, user_id: int, limit: int = 10) -> List[DrivingSession]:
    """Fetches recent driving sessions for a user."""
    return db.query(DrivingSession).filter(
        DrivingSession.user_id == user_id
    ).order_by(DrivingSession.start_time.desc()).limit(limit).all()
