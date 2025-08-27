import datetime
import re

from shared_memory_dict import SharedMemoryDict
from loguru import logger

from nicegui import ui, app, Tailwind

from jrnl.tasks.task import get_tasks_by_id, get_task_id, get_journal, get_next_sub_taskid, get_task_status, \
    get_duration, timedelta_to_string, update_task_by_gui_columns
from jrnl.tasks.protocols import Columns, TaskStatus

rows = []


def set_shared(value):
    shared_mem = SharedMemoryDict(name='shared', size=16)
    shared_mem['value'] = value


def get_shared():
    shared_mem = SharedMemoryDict(name='shared', size=16)
    return shared_mem['value']


set_shared('1.0')  # Shared memory so that "lambda" functions can access the value.


def save_rows():
    headers, *items = rows
    for item in items:
        columns = Columns(*list(item.descendants()))
        update_task_by_gui_columns(columns)
        logger.info(f'Saving task: {columns}')
    app.shutdown()


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

    red_style = Tailwind().text_color('red-600').font_weight('bold')

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
                id_label = ui.label(id_)
                if str(taskid) == id_:
                    red_style.apply(id_label)
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