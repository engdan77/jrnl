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


def normalize_date(from_date: str, to_date: str) -> tuple[str, str]:
    """Normalize a date string to YYYY-MM-DD format, and ensure to cover complete week for e.g, Monday to Friday."""
    weekday_today = datetime.date.today().strftime('%A').lower()
    date_today = datetime.date.today().isoformat()
    if (from_date.lower(), to_date.lower()) == ('monday', 'friday'):
        if weekday_today == 'monday':
            last_monday = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            last_friday = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
            return last_monday, last_friday
        last_monday = parse(from_date, settings={'PREFER_DATES_FROM': 'past'})
        coming_friday = date_today if weekday_today == 'friday' else parse(to_date, settings={'PREFER_DATES_FROM': 'future'}).isoformat()
        return last_monday, coming_friday
    else:
        return parse(from_date).strftime("%Y-%m-%d"), parse(to_date).strftime("%Y-%m-%d")