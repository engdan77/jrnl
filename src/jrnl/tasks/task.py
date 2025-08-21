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


def get_next_taskid(journal: Journal):
    ids = set()
    for entry in journal.entries:
        if TASK_ID_PHRASE in entry.text:
            for token in entry.text.split():
                if token.startswith(TASK_ID_PHRASE):
                    ids.add(float(token.split(":")[1].strip('.')))
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
        entry.title = re.sub(rf'@{status.value}:\d+-\d+-\d+', '', entry.title.strip())
        try:
            entry.tags.remove(f'@{status.value}')
        except ValueError:
            pass
    return entry


def set_task_status(task_id: int | float, status: TaskStatus, journal: Journal):
    now = datetime.date.today()
    for entry in journal.entries:
        if f'{TASK_ID_PHRASE}{task_id}' in entry.text:
            entry = remove_task_status(entry)
            entry.title = f'{entry.title} @{status.value}:{now:%Y-%m-%d}'
            entry.tags.append(f'@{status.value}')


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
    ...


if __name__ == "__main__":
    example_tasks()
