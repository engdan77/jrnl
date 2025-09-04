import dataclasses
import datetime
import json

from jrnl.tasks.task import get_task_id, get_duration
from jrnl.tasks.time import timedelta_to_string


# Example Alfred JSON output
# {"items": [
#     {
#         "uid": "desktop",
#         "type": "file",
#         "title": "Desktop",
#         "subtitle": "~/Desktop",
#         "arg": "~/Desktop",
#         "autocomplete": "Desktop",
#         "icon": {
#             "type": "fileicon",
#             "path": "~/Desktop"
#         }
#     }
# ]}


@dataclasses.dataclass
class AlfredItem:
    title: str
    subtitle: str
    arg: float | int
    autocomplete: str

    def to_json(self):
        return json.dumps(dataclasses.asdict(self))

    def to_dict(self):
        return dataclasses.asdict(self)


def search_result_to_alfred(result: dict, time_left: bool = False) -> str:
    """This is the format that macOS Alfred JSON expects as output based on search results."""
    items = []
    total_duration = datetime.timedelta()
    for entry in result['entries']:
        task_id = get_task_id(entry['title'])
        entry['title'] = (
            f"{entry['title']} ({task_id})" if task_id else entry['title']
        )
        show_tags = entry.get('tags', [])
        show_tags.remove('@task')
        duration = get_duration(entry)
        total_duration += duration
        duration_str = timedelta_to_string(duration)
        item = AlfredItem(
            title=f'{entry["date"]} {' '.join(show_tags)} {x if (x := duration_str) else ''}'.strip(),
            subtitle=entry['title'],
            arg=task_id,
            autocomplete=entry['title'],
        )
        items.append(item)
    if time_left:
        time_left_item = AlfredItem(
            title=f'Total time: {timedelta_to_string(total_duration)}.',
            subtitle='',
            arg=0.0,
            autocomplete=''
        )
        items.append(time_left_item)
    return json.dumps({
        'cache': {
            'seconds': 30
        },
        'items': [item.to_dict() for item in sorted(items, key=lambda x: x.title)]
    })