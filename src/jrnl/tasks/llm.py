from typing import Final

import ollama
from ollama import ChatResponse, chat
from string import Template

SIMPLIFY_TASKS_PROMPT = Template("""Make a one line summary of the below tasks completed:
$tasks_in_bullet_form
""")

MODEL: Final = 'gemma:7b'


def pull_model():
    ollama.pull(MODEL)


def make_task_bullets_simpler(tasks: str) -> str:
    content = SIMPLIFY_TASKS_PROMPT.substitute(tasks_in_bullet_form=tasks)

    response: ChatResponse = chat(model=MODEL, messages=[
        {
            'role': 'user',
            'content': content,
        },
    ])
    return response.message.content



