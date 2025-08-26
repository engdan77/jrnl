import dataclasses
import datetime
import re
from typing import Protocol

import nicegui
from shared_memory_dict import SharedMemoryDict
from loguru import logger

from nicegui import ui

from jrnl.tasks.task import get_task_by_id, get_tasks_by_id, get_task_id, get_journal, get_next_sub_taskid, TaskStatus, \
    get_task_status, get_duration, string_to_timedelta, timedelta_to_string

rows = []


def set_shared(value):
    shared_mem = SharedMemoryDict(name='shared', size=16)
    shared_mem['value'] = value
    logger.info(f'Shared memory set to {value}')


def get_shared():
    shared_mem = SharedMemoryDict(name='shared', size=16)
    logger.info(f'Shared memory get to {shared_mem["value"]}')
    return shared_mem['value']


set_shared('1.0')  # Shared memory so that "lambda" functions can access the value.


class NiceGuiElement(Protocol):

    @property
    def value(self): ...

    @property
    def text(self): ...


@dataclasses.dataclass
class Columns:
    id: NiceGuiElement
    date: NiceGuiElement
    title: NiceGuiElement
    starred: NiceGuiElement
    status: NiceGuiElement
    duration: NiceGuiElement

    def to_dict(self):
        return {
            'id': self.id.text,
            'date': self.date.text,
            'title': self.title.value,
            'status': self.status.value,
            'starred': self.starred.value,
            'duration': self.duration.value,
        }


def save_rows():
    headers, *items = rows
    for item in items:
        columns = list(item.descendants())
        item_dict = Columns(*columns).to_dict()
        ...


def validate_duration(duration: str):
    logger.info(f'Validating duration: {duration}')
    valid = re.match(r"^(\d+d)?(\d+h)?(\d+m)?$", duration)
    return bool(valid)


def gui_update_task(taskid: float | str):
    tasks = get_tasks_by_id(float(taskid))

    ui.label("Tasks:")
    ui.dark_mode().enable()
    container = ui.column()

    journal, journal_file = get_journal()
    set_shared(get_next_sub_taskid(journal, taskid))

    column_styling = '30px 80px 700px 100px 60px 90px'
    classes_styling = 'w-full'

    with container:
        with ui.grid(columns=column_styling).classes(classes_styling) as row:
            ui.label('ID')
            ui.label('Date')
            ui.label('Title')
            ui.label('Status')
            ui.label('Starred')
            ui.label('Duration')
            rows.append(row)
        for task in tasks:
            id_ = str(get_task_id(task))
            current_duration_string = timedelta_to_string(get_duration(task))
            with ui.grid(columns=column_styling).classes(classes_styling) as row:
                ui.label(id_)
                ui.label(task['date'])
                ui.input(value=task['title'])
                ui.select({s.title(): s.value for s in TaskStatus}, value=get_task_status(task).title())
                ui.checkbox(value=task['starred'])
                ui.input(value=current_duration_string, validation={'Shall be in 1d2h3m format': validate_duration})
                rows.append(row)

    def add_subtask():
        next_subtask_id = get_shared()
        with container:
            with ui.grid(columns=column_styling).classes(classes_styling) as subtask_row:
                ui.label(str(next_subtask_id))
                ui.label(f'{datetime.datetime.now():%Y-%m-%d}')
                ui.input()
                ui.select({s.title(): s.value for s in TaskStatus}, value='Todo')
                ui.checkbox(value=False)
                ui.input(value='', validation={'Shall be in 1d2h3m format': validate_duration})
                next_subtask_id = round(float(next_subtask_id) + 0.1, 2)
                logger.info(f'Generating next subtask id: {next_subtask_id}')
                set_shared(next_subtask_id)
                rows.append(subtask_row)

    ui.button('Add subtask', on_click=add_subtask)

    ui.button('Save', on_click=save_rows)

    ui.run(native=True, window_size=(1280, 720))


if __name__ in {"__main__", "__mp_main__"}:
    gui_update_task(taskid=5.1)