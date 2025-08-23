import json

import cyclopts
from loguru import logger

from jrnl.tasks.task import add_task_to_journal, search_journal

cli_app = cyclopts.App()


@cli_app.command
def add(text: str):
    """Add a task to the journal."""
    logger.info(f"Adding task: {text}")
    add_task_to_journal(text)


@cli_app.command
def search(keywords: list[str]):
    """Search for entries in a journal with OR condition and return the results."""
    result = search_journal(keywords)
    print(json.dumps(result, indent=4))


def main():
    cli_app()


if __name__ == "__main__":
    main()