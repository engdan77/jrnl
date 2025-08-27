import datetime
import json
import re
import logging
from typing import TYPE_CHECKING, Union, Final

from jrnl.tasks.protocols import Columns, TaskStatus

if TYPE_CHECKING:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TASK_ID_PHRASE: Final = "@task:"
DURATION_PHRASE: Final = "@spent:"


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


def has_duration(entry: "Entry") -> bool:
    return bool(re.match(fr".*?{DURATION_PHRASE}(\w+).*", entry.text))


def get_task_id(entry: Union["Entry", str, dict]) -> int | float | None:
    try:
        title = entry.text if not isinstance(entry, str) else entry
    except AttributeError:
        title = entry['title']
    for token in title.split():
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


def get_task_status(entry: "Entry") -> TaskStatus | None:
    title = entry['title'] if isinstance(entry, dict) else entry.title
    for status in TaskStatus:
        if f"@{status.value}" in title:
            return status
    else:
        return None


def remove_task_id(entry: "Entry") -> "Entry":
    entry.title = re.sub(rf"{TASK_ID_PHRASE}(\d+\.\d+)?", "", entry.title).strip()
    return entry


def set_task_id(task_id: int | float, entry: "Entry"):
    entry = remove_task_id(entry)
    entry.title = f"{entry.title} {TASK_ID_PHRASE}{task_id}"
    entry.tags.append("@task")
    return entry


def set_task_status(entry: "Entry", status: TaskStatus) -> "Entry":
    now = datetime.date.today()
    entry = remove_task_status(entry)
    entry.title = f"{entry.title} @{status.value}:{now:%Y-%m-%d}"
    entry.tags.append(f"@{status.value}")
    return entry


def update_task_by_gui_columns(columns: Columns):
    """Update a task by the GUI columns."""
    t = columns.to_dict()
    new_title = t['title']
    task_id = float(t['id'])
    new_status = TaskStatus(t['status'].lower())
    duration = string_to_timedelta(t['duration'])

    journal, journal_file = get_journal()
    assert isinstance(task_id, float), 'Task ID must be a float to be specific'
    entries = get_entries_by_keyword(journal, f"{TASK_ID_PHRASE}{task_id}")
    if not entries:
        new_entry = journal.new_entry(new_title, append=False)
        new_entry = apply_initial_task_properties(new_entry, journal=journal, override_task_id=task_id)
        set_task_status(new_entry, new_status)
        journal.entries.append(new_entry)
        logger.info(f"Added new task: {new_entry.title}")
    for entry in entries:
        if entry.title != new_title:
            entry.title = t['title']
        current_status = get_task_status(entry)
        if new_status != current_status:
            entry = set_task_status(entry, new_status)  # To avoid wrecking the current date
        if duration:
            entry = replace_duration(entry, duration)
        logger.info(f"Updated task: {entry.title}")
    journal.write(journal_file)


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


def get_duration(entry: Union["Entry", dict]) -> datetime.timedelta:
    title = entry['title'] if isinstance(entry, dict) else entry.title
    if duration := re.match(fr".*?{DURATION_PHRASE}(\w+).*", title):
        g = duration.group(1)
        return string_to_timedelta(g)
    else:
        return datetime.timedelta()


def remove_duration(entry: "Entry") -> "Entry":
    entry.title = re.sub(fr"{DURATION_PHRASE}\w+", "", entry.title)
    return entry


def add_duration(entry: "Entry", duration: datetime.timedelta) -> "Entry":
    current_duration = get_duration(entry)
    new_duration = current_duration + duration
    duration_string = timedelta_to_string(new_duration)
    remove_duration(entry)
    entry.title = f"{entry.title} {DURATION_PHRASE}{duration_string}"
    return entry


def replace_duration(entry: "Entry", duration: datetime.timedelta) -> "Entry":
    duration_string = timedelta_to_string(duration)
    remove_duration(entry)
    entry.title = f"{entry.title} {DURATION_PHRASE}{duration_string}"
    return entry


def apply_initial_task_properties(entry: "Entry", journal: "Journal", override_task_id: float | None = None) -> "Entry":
    if override_task_id:
        set_task_id(override_task_id, entry)
    else:
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

    if not has_task_status(entry) and has_duration(entry):
        entry = set_task_status(entry, status=TaskStatus.completed)
    elif not has_task_status(entry) and not has_duration(entry):
        entry = set_task_status(entry, status=TaskStatus.todo)

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


def get_journal_file_path(journal_name: str = "default") -> str:
    journal, journal_file = get_journal(journal_name)
    return journal_file


def search_journal(keywords: list[str]) -> dict | list[dict]:
    from jrnl.plugins import json_exporter
    journal, journal_file = get_journal()
    journal.filter(contains=keywords, strict=True)
    json_result = json_exporter.JSONExporter().export(journal)
    return json.loads(json_result)


def get_all_tasks_as_dict():
    from jrnl.plugins import json_exporter
    journal, journal_file = get_journal()
    json_result = json_exporter.JSONExporter().export(journal)
    return json.loads(json_result)


def get_all_tasks() -> list:
    all_tasks = get_all_tasks_as_dict()
    return sorted(all_tasks['entries'], key=lambda x: (x['date'], x['time']))


def get_task_by_id(task_id: float) -> "Entry":
    journal, journal_file = get_journal()
    entries = get_entries_by_keyword(journal, f"{TASK_ID_PHRASE}{task_id}")
    return entries[0]


def get_tasks_by_id(task_id: float):
    """Return all (associated) tasks with the given major task ID."""
    output_tasks = []
    all_tasks = get_all_tasks_as_dict()
    for task in all_tasks['entries']:
        if int(get_task_id(task)) == int(task_id):
            output_tasks.append(task)
    return output_tasks


def example_tasks():
    # add_task_to_journal("My super duper task")
    # logger.info("Example tasks added")
    journal, journal_file = get_journal()
    entries = search_journal(["task:2"])
    ...



if __name__ == "__main__":
    example_tasks()