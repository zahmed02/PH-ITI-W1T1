# backend/date_parser.py
from datetime import datetime, timedelta
import re

# Urdu to English translation mappings
URDU_TO_ENGLISH = {
    'aaj': 'today',
    'aj': 'today',
    'kal': 'tomorrow',
    'parso': 'day after tomorrow',
    'is hafte': 'this week',
    'is haftay': 'this week',
    'aglay hafte': 'next week',
    'aglay haftay': 'next week',
    'konse din': '',  # will be handled separately
    'konsay din': '',
}

# Urdu day names (Romanized)
URDU_DAY_MAP = {
    'itwar': 'sunday',
    'peer': 'monday',
    'mangal': 'tuesday',
    'budh': 'wednesday',
    'jumerat': 'thursday',
    'juma': 'friday',
    'hafte': 'saturday',
    'hfta': 'saturday',
}

def translate_urdu_date(expr: str) -> str:
    """Translate common Urdu date phrases to English."""
    expr_lower = expr.lower().strip()
    # Replace full phrases
    for urdu, eng in URDU_TO_ENGLISH.items():
        if urdu in expr_lower:
            expr_lower = expr_lower.replace(urdu, eng)
    # Replace day names if they appear (e.g., "mangal ko" -> "tuesday")
    for urdu, eng in URDU_DAY_MAP.items():
        if urdu in expr_lower:
            expr_lower = expr_lower.replace(urdu, eng)
    return expr_lower

def parse_date_expression(expr: str) -> datetime | None:
    """
    Convert natural language date expressions like 'today', 'tomorrow',
    'this Friday', 'next Monday' into a datetime object.
    Also supports Urdu/Romanized Urdu: 'kal', 'parso', 'aaj', 'is hafte', etc.
    Returns None if parsing fails.
    """
    if not expr:
        return None

    # Translate Urdu to English
    expr = translate_urdu_date(expr)

    # Handle "this week" and "next week" – we'll return today for simplicity
    if "this week" in expr:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if "next week" in expr:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)

    expr = expr.lower().strip()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Direct date in YYYY-MM-DD
    try:
        return datetime.strptime(expr, "%Y-%m-%d")
    except ValueError:
        pass

    # "today"
    if expr == "today":
        return today

    # "tomorrow"
    if expr == "tomorrow":
        return today + timedelta(days=1)

    # "day after tomorrow"
    if expr == "day after tomorrow":
        return today + timedelta(days=2)

    # "yesterday"
    if expr == "yesterday":
        return today - timedelta(days=1)

    # Weekday mapping: Monday=0, Sunday=6
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }

    # "this Friday", "next Monday"
    parts = expr.split()
    if len(parts) == 2 and parts[1] in weekdays:
        modifier, day_name = parts[0], parts[1]
        target_weekday = weekdays[day_name]
        current_weekday = today.weekday()  # Monday=0

        if modifier == "this":
            days_until = (target_weekday - current_weekday) % 7
            if days_until == 0:
                return today
            return today + timedelta(days=days_until)
        elif modifier == "next":
            days_until = (target_weekday - current_weekday) % 7
            if days_until == 0:
                days_until = 7
            return today + timedelta(days=days_until)

    # Single weekday like "friday"
    if expr in weekdays:
        target = weekdays[expr]
        current = today.weekday()
        days_until = (target - current) % 7
        if days_until == 0:
            return today
        return today + timedelta(days=days_until)

    return None

def parse_time_expression(expr: str) -> tuple[int, int] | None:
    """
    Convert time expressions like 'morning', 'afternoon', 'evening',
    or specific hour like '10am', '10 AM', '10:00 AM', '10:00am' into (start_hour, end_hour).
    Returns None if not recognized.
    """
    if not expr:
        return None
    # Normalize: lowercase, remove extra spaces
    expr = expr.lower().strip()
    # Remove spaces around colon and am/pm
    expr = re.sub(r'\s+', '', expr)

    # Match patterns like 10am, 10pm, 10:00am, 10:00pm
    match = re.match(r"(\d{1,2})(:(\d{2}))?(am|pm)", expr)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(3)) if match.group(3) else 0
        ampm = match.group(4)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        # Assume a 1-hour slot starting at the given minute
        end_hour = hour + 1
        if end_hour > 24:
            end_hour = 24
        return (hour, end_hour)

    # Time ranges
    if expr in ["morning"]:
        return (9, 12)
    if expr in ["afternoon"]:
        return (12, 17)
    if expr in ["evening"]:
        return (17, 20)

    return None