import json

import cyclopts
from loguru import logger
from enum import StrEnum, auto

import jrnl.tasks.gui
import jrnl.tasks.sharedmem
from jrnl.tasks.gui import gui_update_task
from jrnl.tasks.output import search_result_to_alfred
from jrnl.tasks.task import add_task_to_journal, search_journal, add_duration_to_task, get_all_tasks_as_dict, \
    set_status_to_task, get_journal_file_path, sum_up_by_date
from jrnl.tasks.protocols import TaskStatus

cli_app = cyclopts.App(help="[yellow]Manage tasks in your journal.[/yellow]", help_format='rich')


class OutputFormat(StrEnum):
    json = auto()
    alfred = auto()


@cli_app.command
def list_tasks() -> list[dict]:
    """List all tasks in the journal."""
    tasks = get_all_tasks_as_dict()
    print(json.dumps(tasks, indent=4))
    return tasks


@cli_app.command
def add_task(text: str):
    """Add a task to the journal."""
    logger.info(f"Adding task: {text}")
    add_task_to_journal(text)


@cli_app.command
def search(keywords: list[str], output_format: OutputFormat = OutputFormat.json) -> dict:
    """Search for entries in a journal using keywords as AND condition and return the results."""
    result = search_journal(keywords)
    match output_format:
        case OutputFormat.json:
            print(json.dumps(result, indent=4))
        case OutputFormat.alfred:
            print(search_result_to_alfred(result))
    return result


@cli_app.command
def add_duration(taskid: float, duration: str):
    """Add duration to a task."""
    add_duration_to_task(taskid, duration)
    logger.info(f"Duration added to task: {taskid} with duration: {duration}")


@cli_app.command
def set_status(taskid: float, status: TaskStatus):
    """Set the status of a task."""
    set_status_to_task(taskid, status)
    logger.info(f"Status of task: {taskid} set to: {status.value}")


@cli_app.command
def update_task(taskid: float | None = None):
    """
    Updates a task with the specified task ID. If no task ID is provided, the
    update will target the default or currently selected task in the system.

    Parameters
    ----------
    taskid
        The unique identifier of the task to be updated. Defaults to None and will return all tasks.
    """
    gui_update_task(taskid=taskid)
    logger.info(f"Task: {taskid} updated")


@cli_app.command
def sum_up_day(date_str: str):
    """
    Summarizes tasks for a specific day based on the provided date string.

    Parameters
    ----------
    date_str
        The date string in a valid format representing the day for which tasks need to be summarized.
    """
    summed_up_tasks = sum_up_by_date(date_str)
    ...


@cli_app.command
def journal_file():
    """Print the path to the journal file."""
    j = get_journal_file_path()
    print(j)


def main():
    cli_app()
    jrnl.tasks.sharedmem.close_shared()


if __name__ in {"__main__", "__mp_main__"}:
    main()
