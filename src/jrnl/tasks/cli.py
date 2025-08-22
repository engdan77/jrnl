import cyclopts
from loguru import logger

from jrnl.tasks.task import add_task_to_journal

cli_app = cyclopts.App()


@cli_app.command
def add(text: str):
    """Add a task to the journal."""
    logger.info(f"Adding task: {text}")
    add_task_to_journal(text)


def main():
    cli_app()


if __name__ == "__main__":
    main()