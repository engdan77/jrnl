import csv
import datetime
import functools
import io
import itertools
import json
import operator
import re

from loguru import logger
from collections import defaultdict, Counter
from typing import TYPE_CHECKING, Union, Final, Iterable, Generator, Any, Annotated
from tabulate import tabulate

import dateparser

from jrnl.tasks.journal import get_journal
from jrnl.tasks.llm import make_task_bullets_simpler, MODEL
from jrnl.tasks.protocols import Columns, TaskStatus, TaskEntryDict, TasksSummary, TaskOutputFormat, DaySummaryDict, \
    Period
from jrnl.tasks.time import string_to_timedelta, timedelta_to_string, timedelta_to_hours, normalize_date

if TYPE_CHECKING:
    pass

TASK_ID_PHRASE: Final = "@task:"
DURATION_PHRASE: Final = "@spent:"

NON_BILLABLE_PROJECT_SUFFIXES = (
    'non-billable',
    'nonbillable',
    'no-billable',
    'nobillable',
    'no-bill',
    'not-billable',
    'notbillable',

)


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


def has_parent_task(task_id: float) -> bool:
    return not task_id % 1 == 0.0


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

def get_task_date(entry: "Entry", status: TaskStatus) -> str | None:
    title = entry['title'] if isinstance(entry, dict) else entry.title
    if not f"@{status.value}" in title:
        return None
    if d := re.search(rf'@{status.value}:(\d+-\d+-\d+)', title):
        return d.group(1)
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
    task_id_to_be_updated = float(t['id'])
    new_status = TaskStatus(t['status'].lower())
    duration = string_to_timedelta(t['duration'])

    journal, journal_file = get_journal()
    assert isinstance(task_id_to_be_updated, float), 'Task ID must be a float to be specific'
    found_entries = get_entries_by_keyword(journal, f"{TASK_ID_PHRASE}{task_id_to_be_updated}")
    delete = columns.deleted.value
    if delete:
        for e in found_entries:
            journal.entries.remove(e)
            logger.info(f"Deleting task: {new_title}")
    else:
        if not found_entries:
            new_entry = journal.new_entry(new_title, append=False)
            new_entry = apply_initial_task_properties(new_entry, journal=journal, override_task_id=task_id_to_be_updated)
            set_task_status(new_entry, new_status)
            journal.entries.append(new_entry)
            logger.info(f"Added new task: {new_entry.title}")
        for entry in found_entries:
            if entry.title != new_title:
                updated_title = apply_non_billable(t['title'])
                entry.title = updated_title
            current_status = get_task_status(entry)
            if new_status != current_status:
                entry = set_task_status(entry, new_status)  # To avoid wrecking the current date
            if duration:
                entry = replace_duration(entry, duration)
            logger.info(f"Updated task: {entry.title}")
    journal.write(journal_file)


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


def apply_non_billable(input_text: str) -> str:
    return re.sub(r'(.+?@\S+)([_-]no[^\b]{,3}bill\w*)(.*)', r'\1-nonbillable\3', input_text)


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


def add_task_to_journal(raw: str, journal_name: str = "default"):
    """Main function to add a task to the journal."""
    journal, journal_file = get_journal()
    raw = apply_non_billable(raw)
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
    journal.filter(contains=keywords, strict=True)
    # TODO: Ensure search by id of task works
    json_result = json_exporter.JSONExporter().export(journal)
    return json.loads(json_result)


def get_all_tasks_as_dict():
    from jrnl.plugins import json_exporter
    journal, journal_file = get_journal()
    json_result = json_exporter.JSONExporter().export(journal)
    d = json.loads(json_result)
    return d


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


def remove_redundant_tags(tags: list[str]) -> list[str]:
    """
    Removes redundant and unwanted tags from the given list of tags.

    This function eliminates duplicate tags by converting the list
    into a set and then applies a filter to remove tags that start
    with specific prefixes like task phrases, duration phrases, or
    task statuses. The final set of tags is returned as a list.
    """
    output_tags = list(set(tags))
    output_tags = [_ for _ in output_tags if not any(_.startswith(p.strip(':')) for p in (TASK_ID_PHRASE, DURATION_PHRASE, *(f'@{t.value}' for t in TaskStatus)))]
    ...
    return output_tags


def clean_task_title_by_str(title: str) -> str:
    t = re.sub(rf"{TASK_ID_PHRASE}(\d+\.\d+)?", "", title).strip()
    t = re.sub(fr"{DURATION_PHRASE}\w+", "", t)
    for status in TaskStatus:
        t = re.sub(
            rf"@{status.value}(:\d+-\d+-\d+)?", "", t.strip()
        )
    return t.strip()


def remove_all_tags(input_text: str) -> str:
    return re.sub(r'\s@[^\s\b]+', '', input_text)


def get_tasks_by_date(date_string: str, task_statuses: Iterable[TaskStatus] = (TaskStatus.completed,)) -> list[TaskEntryDict]:
    """
    Return all (associated) tasks with the given date.
    Also ensure that redundant tags are removed.
    """
    date = f'{dateparser.parse(date_string).date():%Y-%m-%d}'
    output_tasks = []
    all_tasks = get_all_tasks_as_dict()
    for task in all_tasks['entries']:
        task_status = get_task_status(task)
        if task_status not in task_statuses:
            continue
        if date in task['date'] or any(f'@{t.value}:{date}' in task['title'] for t in task_statuses):
            if task['date'] is not date:
                task_id = get_task_id(task)
                logger.debug(f"Task {task_id} has date {task['date']} but completed other date, updating to {date}")
                task['date'] = date
            task['tags'] = remove_redundant_tags(task['tags'])
            output_tasks.append(task)
    return output_tasks


def get_tasks_by_status(status: TaskStatus) -> list[TaskEntryDict]:
    """Return all (associated) tasks with the given status."""
    output_tasks = []
    all_tasks = get_all_tasks_as_dict()
    for task in all_tasks['entries']:
        if get_task_status(task) == status:
            task['tags'] = remove_redundant_tags(task['tags'])
            output_tasks.append(task)
    return output_tasks


def get_tasks_grouped_by_tags(tasks: list[TaskEntryDict]) -> dict[tuple[str], list[TaskEntryDict]]:
    tags_grouped_tasks = defaultdict(list)
    for task in tasks:
        tags_tuple = tuple(sorted(task['tags']))
        tags_grouped_tasks[tags_tuple].append(task)
    return tags_grouped_tasks


def concat_title_body(title: str, body: str, extra: str) -> str:
    output_lines = [f"- {title}".strip()]
    if body:
        output_lines.append(f"    - {body}".strip())
    if extra:
        linked_task_title = clean_task_title_by_str(extra)
        output_lines.append(f"    - Continuation of the task \"{linked_task_title}\"".strip())
    return "\n".join(output_lines)


def get_title_of_parent_task(task_id: float) -> str:
    if not has_parent_task(task_id):
        return ""
    parent_task_id = float(int(task_id))
    parent_task = get_task_by_id(parent_task_id)
    return parent_task['title'] if isinstance(parent_task, dict) else parent_task.title


def get_day_summary_by_tasks(input_tasks: list[TaskEntryDict]) -> list[TasksSummary]:
    summary_per_tags: list[TasksSummary] = []
    tasks_grouped_by_tags = get_tasks_grouped_by_tags(input_tasks)
    for tags, tasks in tasks_grouped_by_tags.items():
        date = tasks[0]['date']
        text_summary_list: list = []
        task_ids: list[float] = []
        starred_list: list[bool] = []
        total_time = datetime.timedelta()
        for task in sorted(tasks, key=lambda x: x['starred']):
            # TODO: ensure starred comes first
            task_id = get_task_id(task)
            task_ids.append(task_id)
            starred_list.append(task['starred'])
            task_duration = get_duration(task)
            total_time += task_duration
            task_title = clean_task_title_by_str(task['title'])  # Remove task ID and status from title
            task_body = task['body']
            parent_task_title = get_title_of_parent_task(task_id)
            task_text = concat_title_body(task_title, task_body, extra=parent_task_title)
            text_summary_list.append(task_text)
        day_summary = TasksSummary(
            date=date,
            text_summary='\n'.join(text_summary_list),
            task_ids=task_ids,
            starred=any(starred_list),
            total_time=total_time,
            tags=tags,
        )
        summary_per_tags.append(day_summary)
    return summary_per_tags


# Python
def calc_total_duration(summaries: list[TasksSummary]) -> datetime.timedelta:
    tot = functools.reduce(operator.add, [s.total_time for s in summaries], datetime.timedelta())
    return tot


def adjust_time(s: list[TasksSummary], steps_minutes: int = 15) -> list[TasksSummary]:
    td = datetime.timedelta
    for item in s:
        current_time = item.total_time.total_seconds()
        new_time = current_time + (60 * steps_minutes)
        item.total_time = td(seconds=int(new_time))
    return s


def normalize_time_summaries(
    summary_per_tags: list[TasksSummary],
    extra_non_project_duration: datetime.timedelta = datetime.timedelta(hours=1),
    working_hours_per_day: datetime.timedelta = datetime.timedelta(hours=8),
) -> list[TasksSummary]:
    """Align the timespan of each summary to the longest one."""
    assert len(summary_per_tags) > 0, "No tasks found, nothing to normalize."
    current_date = summary_per_tags[0].date

    non_project = TasksSummary(
        date=current_date,
        text_summary='- Non-project task',
        task_ids=[],
        starred=False,
        total_time=extra_non_project_duration,
        tags=('@non-project',),
    )

    current_sum_durations = calc_total_duration(summary_per_tags)
    least_hours_required = working_hours_per_day - extra_non_project_duration

    # Adds a non-project task if the total time of all tasks is less than working hours per day, adding little extra non-project time. Or adding to a current non-project task if such exists.
    if least_hours_required <= current_sum_durations < working_hours_per_day:
        logger.info("Total time of all tasks is less than working hours per day, adding little extra non-project time.")
        non_project.total_time = working_hours_per_day - current_sum_durations
        if found_non_project := [s for s in summary_per_tags if '@non-project' in s.tags]:
            found_non_project[0].total_time += non_project.total_time
        else:
            summary_per_tags.append(non_project)
        return summary_per_tags
    elif current_sum_durations < least_hours_required:
        summary_per_tags = increase_times(summary_per_tags, least_hours_required)
        if found_non_project := [s for s in summary_per_tags if '@non-project' in s.tags]:
            found_non_project[0].total_time += non_project.total_time
        else:
            summary_per_tags.append(non_project)
        logger.info(f"New total time: {calc_total_duration(summary_per_tags)}")
        return summary_per_tags
    elif current_sum_durations > working_hours_per_day:
        summary_per_tags = decrease_times(summary_per_tags, working_hours_per_day)
        logger.info(f"New total time: {calc_total_duration(summary_per_tags)}")
        return summary_per_tags
    return summary_per_tags


def increase_times(summaries: list[TasksSummary], least_hours_required: datetime.timedelta) -> list[TasksSummary]:
    logger.info("Adjusting time a notch to align into reasonable margins evenly")
    org_duration = calc_total_duration(summaries)
    if not org_duration:
        logger.warning('No tasks found, nothing to adjust.')
        raise SystemExit(1)
    while calc_total_duration(summaries) < least_hours_required:
        summaries = adjust_time(summaries, steps_minutes=15)
    c = calc_total_duration(summaries)
    minor_leftover = least_hours_required - c
    summaries[-1].total_time += minor_leftover
    c = calc_total_duration(summaries)
    logger.info(f"Adjusted time from {org_duration} to {c} = {1 - org_duration.total_seconds() / c.total_seconds():.1%}")
    return summaries


def decrease_times(summaries: list[TasksSummary], working_hours_per_day: datetime.timedelta) -> list[TasksSummary]:
    logger.info("Adjusting time a notch to align into reasonable margins evenly")
    org_duration = calc_total_duration(summaries)
    while calc_total_duration(summaries) > working_hours_per_day:
        summaries = adjust_time(summaries, steps_minutes=-15)
    c = calc_total_duration(summaries)
    minor_leftover = working_hours_per_day - c
    summaries[-1].total_time += minor_leftover
    c = calc_total_duration(summaries)
    logger.info(f"Adjusted time from {org_duration} to {c} = {1 - org_duration.total_seconds() / c.total_seconds():.1%}")
    return summaries


def day_summary_to_dict(day_summaries: list[TasksSummary]) -> list[dict]:
    output_list: list[dict] = []
    for d in day_summaries:
        output_list.append(
            {
                "date": d.date,
                "text_summary": d.text_summary,
                "task_ids": d.task_ids,
                "starred": d.starred,
                "total_time": timedelta_to_string(d.total_time),
                "tags": d.tags,
            }
        )
    return output_list


def convert_iterable_to_strings(input_data: list[dict] | list[TaskEntryDict], fields=('task_ids', 'tags')) -> list[dict]:
    output_list: list[dict] = []
    for item in input_data:
        new_item = dict(item)
        for f in fields:
            if f in new_item and isinstance(new_item[f], (list, tuple, set)):
                new_item[f] = ', '.join(str(_) for _ in new_item[f])
        output_list.append(new_item)
    return output_list


def day_summary_to_json(day_summaries: list[TasksSummary]) -> str:
    output_list = day_summary_to_dict(day_summaries)
    return json.dumps(output_list, indent=4)


def day_summary_to_tsv(day_summaries: list[TasksSummary]) -> str:
    rows = day_summary_to_dict(day_summaries)
    rows_with_converted_fields = convert_iterable_to_strings(rows)
    output_csv = io.StringIO()
    writer = csv.DictWriter(output_csv, fieldnames=rows_with_converted_fields[0].keys(), delimiter='\t')
    writer.writeheader()
    writer.writerows(rows_with_converted_fields)
    return output_csv.getvalue()


def tasks_to_tsv(tasks: list[TaskEntryDict]) -> str:
    rows_with_converted_fields = convert_iterable_to_strings(tasks)
    output_csv = io.StringIO()
    writer = csv.DictWriter(output_csv, fieldnames=rows_with_converted_fields[0].keys(), delimiter='\t')
    writer.writeheader()
    writer.writerows(rows_with_converted_fields)
    return output_csv.getvalue()


def make_tasks_text_simpler(summaries: list[TasksSummary], model: str = MODEL) -> list[TasksSummary]:
    for idx, summary in enumerate(summaries):
        logger.info(f"Making summary {idx + 1}/{len(summaries)} simpler")
        text = remove_all_tags(summary.text_summary)
        summary.text_summary = make_task_bullets_simpler(text, duration=summary.total_time, model=model)
    return summaries


def get_date_range(from_date: str, to_date: str) -> Generator[str]:
    normalized_from, normalized_to = normalize_date(from_date, to_date)
    from_date_dt = dateparser.parse(normalized_from)
    to_date_dt = dateparser.parse(normalized_to)
    for n in range(int((to_date_dt - from_date_dt).days) + 1):
        yield f'{from_date_dt + datetime.timedelta(days=n):%Y-%m-%d}'


def is_string_part_of_tags(search_string: str, tags: Iterable[str]) -> bool:
    if tags == []:
        tags = ['unknown']  # To ensure one can include by CLI by --include-only-tag unknown
    if search_string in tags:
        return True
    for tag in tags:
        if search_string in tag:
            return True
    if ','.join(sorted(search_string.split(','))) == ','.join(sorted(tags)):
        return True
    return False


def day_summary_to_bar_chart_data(day_summaries: list[DaySummaryDict]) -> tuple[Annotated[list, 'x_axis'], Annotated[list[list], 'series'], Annotated[list, 'labels']]:
    summary = defaultdict(dict)
    for s in day_summaries:
        tag = tuple(s['tags'])
        summary[s['date']][tag] = string_to_timedelta(s['total_time'])
    x_axis = list(sorted(summary.keys()))
    labels = sorted(list(set(itertools.chain.from_iterable([day.keys() for day in summary.values()]))))
    series = []
    for tag in labels:
        day_series = []
        for day in x_axis:
            day_series.append(timedelta_to_hours(summary[day].get(tag, datetime.timedelta())))
        series.append(day_series)
    labels = [f','.join(l).replace('@', '') for l in labels]
    return x_axis, series, labels


def day_summary_per_tags(day_summaries: list [DaySummaryDict]) -> Counter:
    c = Counter()
    for s in day_summaries:
        tags = ','.join(sorted(s['tags'])).replace('@', '') or 'unknown'
        c[tags] += round(string_to_timedelta(s['total_time']).total_seconds() / 3600, 1)
    return c


def truncate_tasks_by_tags_and_period(daily_tasks: list[TasksSummary], by_period: Period = Period.month) -> list[TasksSummary]:
    output_tasks: list[TasksSummary] = []
    monthly_tasks: dict[tuple[str, tuple], list[TasksSummary]] = defaultdict(list)
    for task in daily_tasks:
        dt = datetime.datetime.strptime(task.date, '%Y-%m-%d')
        tags = tuple(sorted(set(task.tags)))
        dt_period = None
        if by_period == Period.month:
            dt_period = dt.strftime('%Y-%m')
        elif by_period == Period.year:
            dt_period = dt.strftime('%Y')
        assert by_period is not None, "Unsupported period"
        monthly_tasks[(dt_period, tags)].append(task)
    tot_time = datetime.timedelta()
    for (dt_period, tags), tasks_ in monthly_tasks.items():
        monthly_duration = calc_total_duration(tasks_)
        tot_time += monthly_duration
        all_texts = '\n'.join(t.text_summary for t in tasks_)
        starred = any(t.starred for t in tasks_)
        task_ids = list(itertools.chain.from_iterable([t.task_ids for t in tasks_]))
        tags = list(set(itertools.chain.from_iterable(t.tags for t in tasks_)))
        output_tasks.append(
            TasksSummary(
                date=dt_period,
                text_summary=all_texts,
                task_ids=task_ids,
                starred=starred,
                total_time=monthly_duration,
                tags=tags,
            )
        )
    return output_tasks


def truncate_tasks(tasks: list[TasksSummary], by: Period) -> list[TasksSummary]:
    """Truncate the task summary by period."""
    assert by is not Period.day, "Cannot truncate by day, use `sum_up_by_date` instead."
    output_tasks: list[TasksSummary] = []
    match by:
        case Period.month:
            output_tasks = truncate_tasks_by_tags_and_period(tasks)
        case _:
            raise ValueError(f"Unsupported period: {by}")
    return output_tasks


def get_summed_up_tasks(date_string: str,
                        to_date_string: str | None = None,
                        output_format: TaskOutputFormat = TaskOutputFormat.json,
                        simplify_texts: bool = False,
                        by_period: Period = Period.day,
                        model: str = MODEL,
                        ) -> Any:
    """
    Processes and summarizes tasks grouped by date. Provides output in various formats
    such as JSON, dictionary, TSV, or a formatted table. The function supports processing
    a range of dates and has an option to simplify the texts in the summaries.

    Parameters
    ----------
        model: LLM model
        date_string (str): The starting date string in the range of tasks to process.
        to_date_string (str | None, optional): The ending date string in the range; if None,
            only the `date_string` is processed. Default is None.
        output_format (TaskOutputFormat): Specifies the format of the output. Can be JSON,
            dictionary, TSV, or a formatted table.
        simplify_texts (bool): Whether to simplify the text in the summaries. Default is False.
        by_period (Period): The granularity of how tasks are summarized, such as daily. Default is Period.day.
    """
    if to_date_string:
        dates = list(get_date_range(date_string, to_date_string))
    else:
        dates = [date_string]

    all_summaries: list[TasksSummary] = []

    date: str
    for date in dates:
        logger.info(f"Processing date: {date}")
        tasks = get_tasks_by_date(date)
        summary_per_tags = get_day_summary_by_tasks(tasks)
        if not summary_per_tags:
            continue
        summary_per_tags: list[TasksSummary] = normalize_time_summaries(summary_per_tags)
        all_summaries.extend(summary_per_tags)

    if by_period in (Period.month, Period.year):
        all_summaries = truncate_tasks_by_tags_and_period(all_summaries, by_period=by_period)

    if simplify_texts:
        all_summaries = make_tasks_text_simpler(all_summaries, model=model)
    match output_format:
        case TaskOutputFormat.dict:
            return day_summary_to_dict(all_summaries)
        case TaskOutputFormat.json:
            return day_summary_to_json(all_summaries)
        case TaskOutputFormat.tsv:
             return day_summary_to_tsv(all_summaries)
        case TaskOutputFormat.pretty_table:
            data = list(csv.reader(io.StringIO(day_summary_to_tsv(all_summaries)), delimiter='\t'))
            return tabulate(data, headers="firstrow")
        case _:
            ...


def get_summarized_time(tasks: list[TaskEntryDict]) -> int:
    """This is the format to JSON that could be used for example StreamDeck"""
    items = []
    total_duration = datetime.timedelta()
    for task in tasks:
        duration = get_duration(task)
        total_duration += duration

    hours_spent = seconds / 3600 if (seconds := total_duration.total_seconds()) else 0
    return int(hours_spent)


def example_tasks():
    # add_task_to_journal("My super duper task")
    # logger.info("Example tasks added")
    journal, journal_file = get_journal()
    entries = search_journal(["task:2"])
    ...



if __name__ == "__main__":
    example_tasks()


