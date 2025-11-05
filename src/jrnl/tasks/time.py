import datetime
import re
from dateparser import parse


def string_to_timedelta(s: str) -> datetime.timedelta:
    g = s.strip()
    days = int(d.group(1)) if (d := re.match(r".*?(\d+)d.*", g)) else 0
    hours = int(h.group(1)) if (h := re.match(r".*?(\d+)h.*", g)) else 0
    mins = int(m.group(1)) if (m := re.match(r".*?(\d+)m.*", g)) else 0
    return datetime.timedelta(days=int(days), hours=int(hours), minutes=int(mins))


def timedelta_to_string(td: datetime.timedelta, enforce_hours: bool=False) -> str:
    output_string = ""
    days = td.days
    hours = td.seconds // 3600
    mins = (td.seconds // 60) % 60
    if enforce_hours:
        hours = round(hours + (mins // 60) + (days * 24), 1)
        return f"{hours}h"
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
        last_monday = parse(from_date, settings={'PREFER_DATES_FROM': 'past'}).isoformat()
        coming_friday = date_today if weekday_today == 'friday' else parse(to_date, settings={'PREFER_DATES_FROM': 'future'}).isoformat()
        return last_monday, coming_friday
    elif (from_date.lower(), to_date.lower()) == ('last monday', 'last friday'):
        last_monday, last_friday = previous_week_monday_friday()
        return last_monday, last_friday
    elif from_date.lower() == 'this month':
        return f'{datetime.date.today():%Y-%m-01}', parse(to_date).strftime("%Y-%m-%d")
    elif from_date.lower() == 'last month':
        last_day_last_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return f'{first_day_last_month:%Y-%m-%d}', f'{last_day_last_month:%Y-%m-%d}'
    else:
        return parse(from_date).strftime("%Y-%m-%d"), parse(to_date).strftime("%Y-%m-%d")


def previous_week_monday_friday(reference: datetime.date | None = None) -> tuple[str, str]:
    """
    Return the (Monday, Friday) dates for the week immediately preceding the week of `reference`.
    If `reference` is None, use today's date.

    Weeks are considered Monday (0) to Sunday (6).
    """
    ref = reference or datetime.date.today()
    current_week_monday = ref - datetime.timedelta(days=ref.weekday())  # Monday of the current week
    prev_week_monday = current_week_monday - datetime.timedelta(days=7)
    prev_week_friday = prev_week_monday + datetime.timedelta(days=4)
    return prev_week_monday.isoformat(), prev_week_friday.isoformat()
