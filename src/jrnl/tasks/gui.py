import dataclasses
import datetime
import functools
import re

from loguru import logger

from nicegui import ui, app, Tailwind
from nicegui.functions.page_title import page_title

from jrnl import __version__
from jrnl.tasks.chart import plot_pie, plot_stacked_bar
from jrnl.tasks.sharedmem import set_shared, get_shared, create_shared, close_shared
from jrnl.tasks.table import day_summaries_to_table
from jrnl.tasks.task import get_tasks_by_id, get_task_id, get_journal, get_next_sub_taskid, get_task_status, \
    get_duration, update_task_by_gui_columns, get_all_tasks, get_next_taskid, get_summed_up_tasks, \
    day_summary_to_bar_chart_data, day_summary_per_tags, get_tasks_by_status, get_tasks_grouped_by_tags
from jrnl.tasks.time import timedelta_to_string
from jrnl.tasks.protocols import Columns, TaskStatus, TaskOutputFormat, DaySummaryDict

TITLE = '📔 Task Journal ✅'

rows = []


def save_rows():
    headers, *items = rows
    for item in items:
        columns = Columns(*list(item.descendants()))
        if not columns.to_dict().get('title', None):
            logger.info('Skipping empty row')
            continue
        if columns.starred.value is True and not columns.title.value.endswith('*'):
            columns.title.value += ' *'
        update_task_by_gui_columns(columns)
        logger.info(f'Saving task: {columns}')
    app.shutdown()


def validate_duration(duration: str):
    logger.info(f'Validating duration: {duration}')
    valid = re.match(r"^(\d+d)?(\d+h)?(\d+m)?$", duration)
    return bool(valid)


@dataclasses.dataclass
class TaskRowsStyle:
    column_styling: str = '30px 80px 700px 100px 60px 90px'
    classes_styling: str = 'w-full'
    red_style: Tailwind = Tailwind().text_color('red-600').font_weight('bold')
    header_style: Tailwind = Tailwind().text_color('yellow-600').font_weight('bold')


def gui_display_todos():
    all_todos = get_tasks_by_status(TaskStatus.todo)
    tasks_per_tag = get_tasks_grouped_by_tags(all_todos)
    for tag, tasks in sorted(tasks_per_tag.items()):
        logger.info(f'Tag: {tag}')
        all_containers = []
        header = ', '.join(tag).replace('@', '')
        container = gui_get_task_rows_container(header_markdown=f'#### {header}', display_version=False)
        all_containers.append(container)
        gui_create_task_rows(
            tasks=tasks,
            container=container,
            styling=TaskRowsStyle(),
        )
    run_gui()


def gui_update_task(taskid: float | str | None = None):
    journal, journal_file = get_journal()

    create_shared()
    if taskid is None:
        tasks = get_all_tasks()
    else:
        logger.info(f'Updating task: {taskid}')
        set_shared(get_next_sub_taskid(journal, taskid))
        tasks = get_tasks_by_id(float(taskid))

    if taskid is not None:
        set_shared(get_next_sub_taskid(journal, taskid))
    else:
        set_shared(get_next_taskid(journal))

    container = gui_get_task_rows_container(header_markdown="#### Tasks ✅", display_version=True)

    s = TaskRowsStyle()

    gui_create_task_rows(tasks=tasks, container=container, styling=s, highlight_taskid=taskid)

    def add_task(container_: ui.column, styling: TaskRowsStyle=s):
        next_subtask_id = get_shared()
        with container_:
            with ui.grid(columns=styling.column_styling).classes(styling.classes_styling) as subtask_row:
                ui.label(str(next_subtask_id))
                ui.label(f'{datetime.datetime.now():%Y-%m-%d}')
                ui.input()
                ui.select({s_.title(): s_.value for s_ in TaskStatus}, value='Todo')
                ui.checkbox(value=False)
                ui.input(value='', validation={'Shall be in 1d2h3m format': validate_duration})
                next_subtask_id = round(float(next_subtask_id) + 0.1, 2)
                logger.info(f'Generating next subtask id: {next_subtask_id}')
                set_shared(next_subtask_id)
                rows.append(subtask_row)

    if taskid:
        add_label = 'Add subtask'
    else:
        add_label = 'Add task'

    ui.button(add_label, on_click=functools.partial(add_task, *[container, s]))
    ui.button('Save', on_click=save_rows)
    ui.on_shutdown = close_shared
    run_gui()


def run_gui(title: str = TITLE, window_size: tuple[int, int] = (1280, 720)):
    ui.run(native=True, reload=False, window_size=window_size, title=title)


def gui_get_task_rows_container(header_markdown: str = "#### Tasks ✅", display_version: bool = True):
    ui.markdown(header_markdown)
    if display_version:
        ui.label(__version__)
    ui.dark_mode().enable()
    container = ui.column()
    return container


def gui_create_task_rows(tasks: list, container: ui.column, styling: TaskRowsStyle, highlight_taskid: float | str | None = None):
    header_titles = ('ID', 'Date', 'Title', 'Status', 'Starred', 'Duration')
    with container:
        with ui.grid(columns=styling.column_styling).classes(styling.classes_styling) as row:
            for h in header_titles:
                styling.header_style.apply(ui.label(h))
            rows.append(row)
        for task in tasks:
            id_ = str(get_task_id(task))
            current_duration_string = timedelta_to_string(get_duration(task))
            with ui.grid(columns=styling.column_styling).classes(styling.classes_styling) as row:
                id_label = ui.label(id_)
                if highlight_taskid and str(highlight_taskid) == id_:
                    styling.red_style.apply(id_label)
                ui.label(task['date'])
                ui.input(value=task['title'])
                ui.select({s.title(): s.value for s in TaskStatus}, value=get_task_status(task).title())
                ui.checkbox(value=task['starred'])
                ui.input(value=current_duration_string, validation={'Shall be in 1d2h3m format': validate_duration})
                rows.append(row)


def gui_display_stats(from_date: str, to_date: str, dark_theme=False):
    if dark_theme:
        ui.dark_mode().enable()
    day_summaries: list [DaySummaryDict] = get_summed_up_tasks(from_date, to_date, simplify_texts=True, output_format=TaskOutputFormat.dict)
    duration_per_tags = day_summary_per_tags(day_summaries)
    x_axis, series, labels = day_summary_to_bar_chart_data(day_summaries)
    with ui.matplotlib(figsize=(16, 6)).figure as fig:
        categories = x_axis
        plot_stacked_bar(
            categories,
            series=series,
            labels=labels,
            title='Projekt och tid',
            y_label='Timmar',
            input_fig=fig,
        )
    with ui.matplotlib(figsize=(9, 6)).figure as fig:
        labels = [f'{_} [{duration_per_tags[_]:g}h]' for _ in duration_per_tags.keys()]
        plot_pie(
            labels,
            values=duration_per_tags.values(),
            title=f'Tid per projekt [total {duration_per_tags.total():g}h]',
            input_fig=fig
        )
    day_summaries_to_table(day_summaries)
    run_gui()
