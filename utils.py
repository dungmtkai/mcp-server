# utils.py
# Utility functions for the haircut scheduler
from datetime import datetime, timedelta

def generate_time_slots(start_time_str: str, end_time_str: str, interval_minutes: int) -> list[str]:
    """Generate available time slots between start and end times with specified interval."""
    start_time = datetime.strptime(start_time_str, "%H:%M")
    end_time = datetime.strptime(end_time_str, "%H:%M")
    slots = []
    current_time = start_time
    while current_time + timedelta(minutes=interval_minutes) <= end_time:
        slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=interval_minutes)
    return slots

def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate squared Euclidean distance between two points (no square root for efficiency)."""
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return dlat ** 2 + dlon ** 2