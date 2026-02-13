import datetime
from typing import Final

import ollama
from ollama import ChatResponse, chat, ResponseError
from string import Template
from loguru import logger
import rich
from persist_cache import cache

from jrnl.tasks.dirs import CACHE_DIR

SIMPLIFY_TASKS_PROMPT = Template("""Make a one line summary of the below tasks completed:
$tasks_in_bullet_form
""")

SIMPLIFY_LONGER_TASKS_PROMPT = Template("""Make a one line summary of the below tasks completed, if there is more than one task, mention that these were a few of many tasks completed:
$tasks_in_bullet_form
""")

MODEL: Final = 'gemma:7b'

HOUR_IN_SECONDS: Final = 60 * 60

console = rich.console.Console()


def pull_model():
    with console.status("Initial status") as status:
        ollama.pull(MODEL)


@cache(dir=CACHE_DIR)
def make_task_bullets_simpler(tasks: str, duration: datetime.timedelta | None, model: str = MODEL) -> str:

    if duration is not None and duration.total_seconds() > HOUR_IN_SECONDS * 2:
        template = SIMPLIFY_LONGER_TASKS_PROMPT
    else:
        template = SIMPLIFY_TASKS_PROMPT

    content = template.substitute(tasks_in_bullet_form=tasks)

    try:
        response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'user',
                'content': content,
            },
        ])
    except ResponseError as e:
        logger.warning(f'Error using LLM: {e}')
        logger.info('Attempting to download model... please try again after this.')
        pull_model()
        raise SystemExit(1)

    return response.message.content



