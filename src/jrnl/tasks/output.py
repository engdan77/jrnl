import dataclasses
import json

from jrnl.tasks.task import get_task_id


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


def search_result_to_alfred(result: dict) -> str:
    """This is the format that macOS Alfred JSON expects as output based on search results."""
    items = []
    for entry in result['entries']:
        task_id = get_task_id(entry['title'])
        entry['title'] = (
            f"{entry['title']} ({task_id})" if task_id else entry['title']
        )
        show_tags = entry.get('tags', [])
        show_tags.remove('@task')
        item = AlfredItem(
            title=f'{entry["date"]} {' '.join(show_tags)}',
            subtitle=entry['title'],
            arg=task_id,
            autocomplete=entry['title'],
        )
        items.append(item)
    return json.dumps({
        'cache': {
            'seconds': 30
        },
        'items': [item.to_dict() for item in sorted(items, key=lambda x: x.title)]
    })