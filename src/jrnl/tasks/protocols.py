import dataclasses
import datetime
from enum import StrEnum, auto
from typing import TypedDict, Protocol, Iterable

from jrnl.tasks.time import timedelta_to_string


class NiceGuiElement(Protocol):

    @property
    def value(self): ...

    @property
    def text(self): ...


class TaskEntryDict(TypedDict):
    title: str
    body: str
    date: str
    time: str
    tags: list[str]
    starred: bool


class ColumnsDict(TypedDict):
    id: str
    date: str
    title: str
    starred: bool
    status: str
    duration: str


@dataclasses.dataclass
class Columns:
    id: NiceGuiElement
    date: NiceGuiElement
    title: NiceGuiElement
    status: NiceGuiElement
    starred: NiceGuiElement
    duration: NiceGuiElement

    def to_dict(self) -> ColumnsDict:
        return {
            'id': self.id.text,
            'date': self.date.text,
            'title': self.title.value,
            'status': self.status.value,
            'starred': self.starred.value,
            'duration': self.duration.value,
        }


@dataclasses.dataclass
class DaySummary:
    date: str
    tags: Iterable[str]
    total_time: datetime.timedelta | str
    task_ids: Iterable[float]
    text_summary: str
    starred: bool
    tags: Iterable[str]

    def to_simpler_dict(self):
        return {
            'date': self.date,
            'tags': ', '.join(self.tags),
            'total_time': timedelta_to_string(self.total_time),
            'task_ids': ', '.join(str(_) for _ in self.task_ids),
            'text_summary': self.text_summary,
            'starred': self.starred
        }


class TaskStatus(StrEnum):
    todo = auto()
    completed = auto()


class TaskOutputFormat(StrEnum):
    dict = auto()
    json = auto()
    tsv = auto()
    pretty_table = auto()
