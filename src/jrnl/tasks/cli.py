import json

import cyclopts
from loguru import logger

from jrnl.tasks.task import add_task_to_journal, search_journal, add_duration_to_task, get_all_tasks

cli_app = cyclopts.App()


@cli_app.command
def list_tasks() -> list[dict]:
    """List all tasks in the journal."""
    tasks = get_all_tasks()
    print(json.dumps(tasks, indent=4))
    return tasks


@cli_app.command
def add_task(text: str):
    """Add a task to the journal."""
    logger.info(f"Adding task: {text}")
    add_task_to_journal(text)


@cli_app.command
def search(keywords: list[str]) -> dict:
    """Search for entries in a journal with OR condition and return the results."""
    result = search_journal(keywords)
    print(json.dumps(result, indent=4))
    return result


@cli_app.command
def add_duration(taskid: float, duration: str):
    """Add duration to a task."""
    add_duration_to_task(taskid, duration)
    logger.info(f"Duration added to task: {taskid} with duration: {duration}")



def main():
    cli_app()


if __name__ == "__main__":
    main()