# type: ignore
from typing import List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import uuid

from toolfuse import Tool

from skillpacks.models.v1alpha import (
    V1ActionEvent,
    V1Attempt,
    V1AcceptedSolution,
    V1StateAction,
    V1Task,
)


class AttemptStatus(Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    ERROR = "error"
    FINISHED = "finished"


@dataclass
class ActionEvent:
    """A record of an action taken"""

    name: str
    user: Optional[str] = None
    reason: Optional[str] = None
    parameters: Optional[dict] = None
    result: Optional[Any] = None

    def to_v1(self) -> V1ActionEvent:
        pass


@dataclass
class StateAction:
    """A state-action pair"""

    observations: List[ActionEvent]
    action: ActionEvent

    def to_v1(self) -> V1StateAction:
        pass


@dataclass
class AcceptedSolution:
    """An accepted solution to a task"""

    task_id: str
    tool: Tool
    history: List[ActionEvent]
    id: str = str(uuid.uuid4())

    def to_v1(self) -> V1AcceptedSolution:
        pass


class TaskStatus(Enum):
    DEFINED = "defined"
    COMPLETED = "completed"


class Task:
    """A task to be accomplished"""

    def __init__(self, description: str, tool: Tool) -> None:
        self.description: str = description
        self.status: TaskStatus = TaskStatus.DEFINED
        self.tool: Tool = tool
        self.attempts: List[Attempt] = []
        self.id = str(uuid.uuid4())
        self.accepted_solution = None

    def record_attempt(self, attempt: "Attempt") -> None:
        self.attempts.append(attempt)

    def attempt(self) -> "Attempt":
        return Attempt(task_id=self.id, tool=self.tool)

    def to_v1(self) -> V1Task:
        pass


class TrainingSet:
    """A training set"""

    def __init__(
        self, solutions: List[AcceptedSolution] = [], tool: Optional[Tool] = None
    ) -> None:
        self.solutions = solutions
        self.tool = tool


class Attempt:
    """An attempt to complete a task"""

    def __init__(self, task: Task, tool: Optional[Tool] = None) -> None:
        self.status: AttemptStatus = AttemptStatus.CREATED
        self.task: Task = task
        self.tool: Optional[Tool] = tool
        self.history: List[ActionEvent] = []
        self.id: str = str(uuid.uuid4())

    def to_v1(self) -> V1Attempt:
        pass

    def start(self) -> None:
        self.status = AttemptStatus.IN_PROGRESS

    def stop(self) -> None:
        self.status = AttemptStatus.FINISHED

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
