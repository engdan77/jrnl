import csv
import io
import json

import cyclopts
import dateparser
from loguru import logger
from tabulate import tabulate

import jrnl.tasks.gui
import jrnl.tasks.sharedmem
from jrnl.tasks.gui import gui_update_task, gui_display_stats
from jrnl.tasks.llm import make_task_bullets_simpler
from jrnl.tasks.output import search_result_to_alfred
from jrnl.tasks.task import add_task_to_journal, search_journal, add_duration_to_task, get_all_tasks_as_dict, \
    set_status_to_task, get_journal_file_path, get_summed_up_tasks, tasks_to_tsv, get_task_date
from jrnl.tasks.protocols import TaskStatus, TaskOutputFormat, EntryOutputFormat, Period

cli_app = cyclopts.App(help="[yellow]Manage tasks in your journal.[/yellow]", help_format='rich')


@cli_app.command
def list_tasks(date: str | None = None, output_format: EntryOutputFormat = EntryOutputFormat.json) -> list[dict]:
    """List all tasks in the journal in its native format."""
    result = get_all_tasks_as_dict()
    if date:
        filtered_entries = []
        parsed_date = dateparser.parse(date).strftime('%Y-%m-%d')
        for result_entry in result['entries']:
            if result_entry['date'] == parsed_date or (get_task_date(result_entry, TaskStatus.completed) == parsed_date):
                filtered_entries.append(result_entry)
        result['entries'] = filtered_entries
    match output_format:
        case EntryOutputFormat.json:
            print(json.dumps(result, indent=4))
        case EntryOutputFormat.alfred:
            print(search_result_to_alfred(result, time_left=True))
        case EntryOutputFormat.tsv:
            tsv = tasks_to_tsv(result['entries'])
            print(tsv)
        case EntryOutputFormat.pretty_table:
            tsv = tasks_to_tsv(result['entries'])
            data = list(csv.reader(io.StringIO(tsv), delimiter='\t'))
            print(tabulate(data, headers="firstrow"))

@cli_app.command
def add_task(text: str):
    """ Add a task to the journal."""
    logger.info(f"Adding task: {text}")
    add_task_to_journal(text)


@cli_app.command
def search(keywords: list[str], output_format: EntryOutputFormat = EntryOutputFormat.pretty_table) -> dict:
    """Search for entries in a journal using keywords as AND condition and return the results."""
    result = search_journal(keywords)
    match output_format:
        case EntryOutputFormat.json:
            print(json.dumps(result, indent=4))
        case EntryOutputFormat.alfred:
            print(search_result_to_alfred(result))
        case EntryOutputFormat.tsv:
            tsv = tasks_to_tsv(result['entries'])
            print(tsv)
        case EntryOutputFormat.pretty_table:
            tsv = tasks_to_tsv(result['entries'])
            data = list(csv.reader(io.StringIO(tsv), delimiter='\t'))
            print(tabulate(data, headers="firstrow"))
    return result


@cli_app.command
def add_duration(taskid: float, duration: str):
    """ Add duration to a task."""
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
    The update will target the default or currently selected task in the system.

    Parameters
    ----------
    taskid
        The unique identifier of the task to be updated. Defaults to None and will return all tasks.
    """
    gui_update_task(taskid=taskid)
    logger.info(f"Task: {taskid} updated")


@cli_app.command
def sum_up_tasks(date: str,
                 to_date: str | None = None,
                 output_format: TaskOutputFormat = TaskOutputFormat.json,
                 simplify_texts: bool = False,
                 by_period: Period = Period.day):
    """
    Summarizes and outputs tasks for a given day or a time period.

    This command aggregates tasks based on the provided date, optional end date, and
    selected period. The tasks can be simplified and output in the desired format.

    Parameters:
    date : str
        The starting date for the task summary. Expected format is `YYYY-MM-DD`.
    to_date : str | None, optional
        The optional ending date for the task summary. If not provided, only the
        `date` parameter is considered. Expected format is `YYYY-MM-DD`.
    output_format : TaskOutputFormat
        The format in which the tasks should be displayed. Defaults to JSON format.
    simplify_texts : bool
        Determines whether task texts are simplified during output. Defaults to False.
    by_period : Period
        The time period for aggregating tasks. Defaults to daily (`Period.day`).

    Returns:
    None

    Raises:
    Exception
        If an error occurs during the task aggregation or output process.
    """
    summed_up_tasks = get_summed_up_tasks(date,
                                          to_date_string=to_date,
                                          output_format=output_format,
                                          simplify_texts=simplify_texts,
                                          by_period=by_period)
    print(summed_up_tasks)
    ...


@cli_app.command
def journal_file():
    """Print the path to the journal file."""
    j = get_journal_file_path()
    print(j)


@cli_app.command
def stats(from_date: str = 'Monday', to_date: str = 'Today'):
    """Displays statistics for the period."""
    gui_display_stats(from_date, to_date)


@cli_app.command
def clear_cache():
    """Clears the cache for such as LLM summarization."""
    logger.info('Clearing cache')
    make_task_bullets_simpler.cache_clear()


def main():
    logger.info(f'Starting version JRNL {jrnl.__version__}')
    cli_app()
    jrnl.tasks.sharedmem.close_shared()
    logger.info('Exiting JRNL')


if __name__ == "__main__":
    main()
