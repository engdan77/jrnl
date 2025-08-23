import datetime
import json
import re
import logging
from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jrnl.journals import Entry, Journal  # for type checking only

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TASK_ID_PHRASE = "@task:"


class TaskStatus(StrEnum):
    todo = auto()
    ongoing = auto()
    completed = auto()


def has_task_status(entry: "Entry") -> bool:
    for status in TaskStatus:
        if f"@{status.value}" in entry.text:
            return True
    return False


def has_task_id(entry: "Entry") -> bool:
    for token in entry.text.split():
        if token.startswith(TASK_ID_PHRASE):
            return True
    else:
        return False


def get_task_id(entry: "Entry") -> int | float | None:
    for token in entry.text.split():
        if token.startswith(TASK_ID_PHRASE):
            return float(token.split(":")[1].strip("."))
    else:
        return None


def get_next_taskid(journal: "Journal"):
    ids = set()
    for entry in journal.entries:
        task_id = get_task_id(entry)
        if task_id:
            ids.add(task_id)
    return int(max(ids)) + 1.0 if ids else 1.0


def get_next_sub_taskid(journal: "Journal", task_id: int | float) -> float | None:
    ids = set()
    for entry in journal.entries:
        if TASK_ID_PHRASE in entry.text:
            for token in entry.text.split():
                if token.startswith(TASK_ID_PHRASE):
                    ids.add(float(token.split(":")[1].strip(".")))
    for id_ in sorted(ids, reverse=True):
        if int(id_) == int(task_id):
            new_id = id_ + 0.1
            if str(new_id).count("9") > 2:
                new_id = round(new_id, 1)  # Workaround for weird floating point errors
            return new_id
    else:
        return None


def get_entries_by_keyword(journal: "Journal", keyword: str) -> list["Entry"]:
    entries = []
    for entry in journal.entries:
        if keyword in entry.text:
            entries.append(entry)
    return entries


def remove_task_status(entry: "Entry") -> "Entry":
    for status in TaskStatus:
        entry.title = re.sub(
            rf"@{status.value}(:\d+-\d+-\d+)?", "", entry.title.strip()
        )
        try:
            entry.tags.remove(f"{status.value}")
        except ValueError:
            pass
    return entry


def remove_task_id(entry: "Entry") -> "Entry":
    entry.title = re.sub(rf"{TASK_ID_PHRASE}(\d+\.\d+)?", "", entry.title).strip()
    return entry


def set_task_id(task_id: int | float, entry: "Entry"):
    entry = remove_task_id(entry)
    entry.title = f"{entry.title} {TASK_ID_PHRASE}{task_id}"
    entry.tags.append("@task")
    return entry


def set_task_status(entry: "Entry", status: TaskStatus):
    now = datetime.date.today()
    entry = remove_task_status(entry)
    entry.title = f"{entry.title} @{status.value}:{now:%Y-%m-%d}"
    entry.tags.append(f"@{status.value}")
    return entry


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


def get_duration(entry: "Entry") -> datetime.timedelta:
    if duration := re.match(r".*?@duration:(\w+).*", entry.title):
        g = duration.group(1)
        return string_to_timedelta(g)
    else:
        return datetime.timedelta()


def remove_duration(entry: "Entry") -> "Entry":
    entry.title = re.sub(r"@duration:\w+", "", entry.title)
    return entry


def add_duration(entry: "Entry", duration: datetime.timedelta):
    current_duration = get_duration(entry)
    new_duration = current_duration + duration
    duration_string = timedelta_to_string(new_duration)
    remove_duration(entry)
    entry.title = f"{entry.title} @duration:{duration_string}"
    return entry


def apply_initial_task_properties(entry: "Entry", journal: "Journal") -> "Entry":
    task_id = get_task_id(entry)
    if not task_id:
        next_task_id = get_next_taskid(journal)
        set_task_id(next_task_id, entry)
    elif task_id % 1 == 0:
        # Ensures if title contains e.g. @id:2.0 that it'd add a sub-task 2.1
        next_sub_task_id = get_next_sub_taskid(journal, task_id)
        if next_sub_task_id:
            set_task_id(next_sub_task_id, entry)
        else:
            set_task_id(task_id + 0.1, entry)

    if not has_task_status(entry):
        entry = set_task_status(entry, status=TaskStatus.completed)
    return entry


def get_journal(journal_name: str = "default") -> tuple["Journal", str]:
    # Delay these imports to avoid circular-import during module import.
    from jrnl import install
    from jrnl.config import scope_config
    from jrnl.journals import Journal
    config = install.load_or_install_jrnl("")
    config = scope_config(config, journal_name)
    journal_file = config["journal"]
    journal = Journal()
    journal.open(journal_file)
    return journal, journal_file


def add_task_to_journal(raw: str, journal_name: str = "default"):
    """Main function to add a task to the journal."""
    journal, journal_file = get_journal()
    new_entry = journal.new_entry(raw, append=False)
    new_entry = apply_initial_task_properties(new_entry, journal=journal)
    journal.entries.append(new_entry)
    journal.write(journal_file)


def add_duration_to_task(task_id: float, duration: str):
    """Add duration to a task."""
    journal, journal_file = get_journal()
    assert isinstance(task_id, float), 'Task ID must be a float to be specific'
    entries = get_entries_by_keyword(journal, f"{TASK_ID_PHRASE}{task_id}")
    for entry in entries:
        entry = add_duration(entry, string_to_timedelta(duration))
        journal.entries.append(entry)
    journal.write(journal_file)


def set_status_to_task(task_id: float, status: TaskStatus):
    """Set status of a task."""
    journal, journal_file = get_journal()
    assert isinstance(task_id, float), 'Task ID must be a float to be specific'
    entries = get_entries_by_keyword(journal, f"{TASK_ID_PHRASE}{task_id}")
    for entry in entries:
        entry = set_task_status(entry, status)
        journal.entries.append(entry)
    journal.write(journal_file)


def search_journal(keywords: list[str]) -> dict | list[dict]:
    from jrnl.plugins import json_exporter
    journal, journal_file = get_journal()
    journal.filter(contains=keywords)
    json_result = json_exporter.JSONExporter().export(journal)
    return json.loads(json_result)


def get_all_tasks():
    from jrnl.plugins import json_exporter
    journal, journal_file = get_journal()
    json_result = json_exporter.JSONExporter().export(journal)
    return json.loads(json_result)


def example_tasks():
    # add_task_to_journal("My super duper task")
    # logger.info("Example tasks added")
    journal, journal_file = get_journal()
    entries = search_journal(["task:2"])
    ...



if __name__ == "__main__":
    example_tasks()