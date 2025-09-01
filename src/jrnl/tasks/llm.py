from typing import Final

import ollama
from ollama import ChatResponse, chat, ResponseError
from string import Template
from loguru import logger
import rich

SIMPLIFY_TASKS_PROMPT = Template("""Make a one line summary of the below tasks completed:
$tasks_in_bullet_form
""")

MODEL: Final = 'gemma:7b'

console = rich.console.Console()

def pull_model():
    with console.status("Initial status") as status:
        ollama.pull(MODEL)


def make_task_bullets_simpler(tasks: str) -> str:
    content = SIMPLIFY_TASKS_PROMPT.substitute(tasks_in_bullet_form=tasks)

    try:
        response: ChatResponse = chat(model=MODEL, messages=[
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



