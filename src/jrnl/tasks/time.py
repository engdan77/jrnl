import datetime
import re
from dateparser import parse


def string_to_timedelta(s: str) -> datetime.timedelta:
    g = s.strip()
    days = int(d.group(1)) if (d := re.match(r".*?(\d+)d.*", g)) else 0
    hours = int(h.group(1)) if (h := re.match(r".*?(\d+)h.*", g)) else 0
    mins = int(m.group(1)) if (m := re.match(r".*?(\d+)m.*", g)) else 0
    return datetime.timedelta(days=int(days), hours=int(hours), minutes=int(mins))


def timedelta_to_string(td: datetime.timedelta) -> str:
    output_string = ""
    days = td.days
    hours = td.seconds // 3600
    mins = (td.seconds // 60) % 60
    if days:
        output_string += f"{days}d"
    if hours:
        output_string += f"{hours}h"
    if mins:
        output_string += f"{mins}m"
    return output_string.strip()


def timedelta_to_hours(td: datetime.timedelta) -> float:
    return td.total_seconds() / 3600


def normalize_date(from_date: str, to_date: str) -> str:
    """Normalize a date string to YYYY-MM-DD format, and ensure to cover complete week for e.g, Monday to Friday."""
    weekday_today = datetime.date.today().strftime('%A')
    if (from_date.lower(), to_date.lower()) == ('monday', 'friday'):
        return weekday_today
    match weekday_today:
        case 'Monday':
            from_date = parse(from_date, settings={'PREFER_DATES_FROM': 'past'})
    return parse(from_date).strftime("%Y-%m-%d")