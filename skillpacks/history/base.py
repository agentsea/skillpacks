# type: ignore

from typing import List, Optional, Any
from dataclasses import dataclass


@dataclass
class Event:
    """A historical event"""

    id: str
    created: int
    creator: str
    role: Optional[str] = None


@dataclass
class History:
    """A history of events"""

    events: List[Event]


@dataclass
class Histories:
    """A set of histories"""

    histories: List[History]


@dataclass
class ActionEvent(Event):
    """A record of an action taken"""

    name: str
    reason: Optional[str] = None
    parameters: Optional[dict] = None
    result: Optional[Any] = None


@dataclass
class SelectionEvent(Event):
    """A record of a action selection"""

    name: str
    reason: Optional[str] = None
    parameters: Optional[dict] = None


@dataclass
class MessageEvent(Event):
    """A record of a action selection"""

    text: str
