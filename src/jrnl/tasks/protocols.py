import dataclasses
from enum import StrEnum, auto
from typing import TypedDict, Protocol


class NiceGuiElement(Protocol):

    @property
    def value(self): ...

    @property
    def text(self): ...


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


class TaskStatus(StrEnum):
    todo = auto()
    completed = auto()
