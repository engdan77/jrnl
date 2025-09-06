from jrnl.tasks.protocols import DaySummary
from nicegui import ui


def day_summaries_to_table(tasks: list[dict]) -> ui.table:
    columns = [
    {'name': 'date', 'label': 'Date', 'field': 'date', 'required': True, 'align': 'left', 'sortable': True},
    {'name': 'total_time', 'label': 'Time', 'field': 'total_time', 'required': True, 'align': 'left', 'sortable': True},
    {'name': 'tags', 'label': 'Tags', 'field': 'tags', 'required': True, 'align': 'left'},
    {'name': 'text_summary', 'label': 'Title', 'field': 'text_summary', 'required': True, 'align': 'left'},
    {'name': 'task_ids', 'label': 'Task IDs', 'field': 'task_ids', 'required': True, 'align': 'left'},
    {'name': 'starred', 'label': 'Starred', 'field': 'starred', 'required': True, 'align': 'left', 'sortable': True},
]
    rows = [DaySummary(**t).to_simpler_dict() for t in tasks]
    table = ui.table(rows=rows, columns=columns)
    return table


def example_table():
    ui.run()


if __name__ == '__main__':
    example_table()