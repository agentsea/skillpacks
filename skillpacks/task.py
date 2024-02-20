from typing import List
from enum import Enum
from dataclasses import dataclass
import uuid

from agent_tools import Tool

from skillpacks.models.v1alpha import (
    V1Action,
    V1Attempt,
    V1AcceptedSolution,
    V1Observation,
    V1StateAction,
    V1Task,
)


TOOL_SCOPE = List[str] | str | None | List[Tool] | Tool


class AttemptStatus(Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    ERROR = "error"
    FINISHED = "finished"


@dataclass
class StateAction:
    """A state-action pair"""

    observations: List[V1Observation]
    action: V1Action

    def to_v1(self) -> V1StateAction:
        pass


@dataclass
class AcceptedSolution:
    task_id: str
    tool: TOOL_SCOPE
    state_actions: List[StateAction]
    id: str = str(uuid.uuid4())

    def to_v1(self) -> V1AcceptedSolution:
        pass


class Attempt:
    """An attempt to complete a task"""

    def __init__(self, task_id: str) -> None:
        self.status: AttemptStatus = AttemptStatus.CREATED
        self.task_id = task_id
        self.id = str(uuid.uuid4())

    def to_v1(self) -> V1Attempt:
        pass


class TaskStatus(Enum):
    DEFINED = "defined"
    COMPLETED = "completed"


class Task:
    """A task to be accomplished"""

    def __init__(self, description: str, tool_scope: TOOL_SCOPE = None) -> None:
        self.description: str = description
        self.status: TaskStatus = TaskStatus.DEFINED
        self.tool_scope: TOOL_SCOPE = tool_scope
        self.attempts: List[Attempt] = []
        self.id = str(uuid.uuid4())

    def record_attempt(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)

    def to_v1(self) -> V1Task:
        pass
