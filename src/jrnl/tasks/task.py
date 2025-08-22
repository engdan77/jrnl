import datetime
import re
from pathlib import Path

from pygments.lexers import j

from jrnl.journals import Entry
from ..journals.Journal import Journal
import logging
from enum import StrEnum, auto

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TASK_ID_PHRASE = "@task:"


class TaskStatus(StrEnum):
    todo = auto()
    ongoing = auto()
    completed = auto()


def has_task_status(entry: Entry) -> bool:
    for status in TaskStatus:
        if f'@{status.value}' in entry.text:
            return True
    return False


def has_task_id(entry: Entry) -> bool:
    for token in entry.text.split():
        if token.startswith(TASK_ID_PHRASE):
            return True
    else:
        return False


def get_task_id(entry: Entry) -> int | float | None:
    for token in entry.text.split():
        if token.startswith(TASK_ID_PHRASE):
            return float(token.split(":")[1].strip('.'))
    else:
        return None


def get_next_taskid(journal: Journal):
    ids = set()
    for entry in journal.entries:
        task_id = get_task_id(entry)
        if task_id:
            ids.add(task_id)
    return int(max(ids)) + 1.0 if ids else 1.0


def get_next_sub_taskid(journal: Journal, task_id: int | float) -> float | None:
    ids = set()
    for entry in journal.entries:
        if TASK_ID_PHRASE in entry.text:
            for token in entry.text.split():
                if token.startswith(TASK_ID_PHRASE):
                    ids.add(float(token.split(":")[1].strip('.')))
    for id_ in sorted(ids, reverse=True):
        if int(id_) == int(task_id):
            return id_ + 0.1
    else:
        return None


def get_entries_by_keyword(journal: Journal, keyword: str) -> list[Entry]:
    entries = []
    for entry in journal.entries:
        if keyword in entry.text:
            entries.append(entry)
    return entries


def remove_task_status(entry: Entry) -> Entry:
    for status in TaskStatus:
        entry.title = re.sub(rf'@{status.value}(:\d+-\d+-\d+)?', '', entry.title.strip())
        try:
            entry.tags.remove(f'@{status.value}')
        except ValueError:
            pass
    return entry


def set_task_id(task_id: int | float, entry: Entry):
    entry.title = f'{entry.title} @{TASK_ID_PHRASE}{task_id}'
    entry.tags.append(f'@task')
    return entry


def set_task_status(task_id: int | float, status: TaskStatus, journal: Journal):
    now = datetime.date.today()
    for entry in journal.entries:
        if f'{TASK_ID_PHRASE}{task_id}' in entry.text:
            entry = remove_task_status(entry)
            entry.title = f'{entry.title} @{status.value}:{now:%Y-%m-%d}'
            entry.tags.append(f'@{status.value}')


def string_to_timedelta(s: str) -> datetime.timedelta:
    g = s.strip()
    days = int(d.group(1)) if (d := re.match(r'(\d+)d', g)) else 0
    hours = int(h.group(1)) if (h := re.match(r'(\d+)h', g)) else 0
    mins = int(m.group(1)) if (m := re.match(r'(\d+)m', g)) else 0
    return datetime.timedelta(days=int(days), hours=int(hours), minutes=int(mins))


def timedelta_to_string(td: datetime.timedelta) -> str:
    output_string = ''
    days = td.days
    hours = td.seconds // 3600
    mins = (td.seconds // 60) % 60
    if days:
        output_string += f'{days}d'
    if hours:
        output_string += f'{hours}h'
    if mins:
        output_string += f'{mins}m'
    return output_string.strip()


def get_duration(entry: Entry) -> datetime.timedelta:
    if duration := re.match(r'.*?@duration:(\w+).*', entry.title):
        g = duration.group(1)
        return string_to_timedelta(g)
    else:
        return datetime.timedelta()


def remove_duration(entry: Entry) -> Entry:
    entry.title = re.sub(r'@duration:\w+', '', entry.title)
    return entry


def add_duration(entry: Entry, duration: datetime.timedelta):
    current_duration = get_duration(entry)
    new_duration = current_duration + duration
    duration_string = timedelta_to_string(new_duration)
    remove_duration(entry)
    entry.title = f'{entry.title} @duration:{duration_string}'
    return entry


def apply_initial_task_properties(entry: Entry, journal: Journal) -> Entry:
    if not has_task_id(entry):
        next_task_id = get_next_taskid(journal)
        set_task_id(next_task_id, entry)
    if not has_task_status(entry):
        set_task_status()
    return entry


def example_tasks():
    j = Journal()
    j.open(Path('~/.local/share/jrnl/journal.txt').expanduser().as_posix())
    next_task_id = get_next_taskid(j)
    logger.info(f"Next task id: {next_task_id}")
    ...
    next_sub_task_id = get_next_sub_taskid(j, 9)
    logger.info(f"Next sub task id: {next_sub_task_id}")
    found_entries = get_entries_by_keyword(journal=j, keyword='@task:9.')
    logger.info(f"Found entries: {found_entries}")
    set_task_status(task_id=9, status=TaskStatus.completed, journal=j)
    e = found_entries[0]
    ee = add_duration(e, datetime.timedelta(days=2, hours=3))
    j.write()
    ...


if __name__ == "__main__":
    example_tasks()
