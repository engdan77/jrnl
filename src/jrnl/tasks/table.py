from jrnl.tasks.protocols import DaySummary
from nicegui import ui


def day_summaries_to_table(tasks: list[DaySummary]) -> ui.table:

    t = ui.table(rows=[
    {'make': 'Toyota', 'model': 'Celica', 'price': 35000},
    {'make': 'Ford', 'model': 'Mondeo', 'price': 32000},
    {'make': 'Porsche', 'model': 'Boxster', 'price': 72000},
    ])

    return t


def example_table():
    ui.run()


if __name__ == '__main__':
    example_table()