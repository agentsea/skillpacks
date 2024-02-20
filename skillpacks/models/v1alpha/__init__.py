from typing import List, Optional, Any
from pydantic import BaseModel


class V1ToolMeta(BaseModel):
    name: str
    module: str
    version: str
    parameters: Optional[dict] = None


class V1Observation(BaseModel):
    name: str
    parameters: Optional[dict] = None
    result: Optional[Any] = None


class V1Action(BaseModel):
    name: str
    user: Optional[str] = None
    reason: Optional[str] = None
    parameters: Optional[dict] = None
    result: Optional[Any] = None


class V1StateAction(BaseModel):
    observations: List[V1Observation]
    action: V1Action


class V1AcceptedSolution(BaseModel):
    description: str
    tool: V1ToolMeta
    state_actions: List[V1StateAction]


class V1Attempt(BaseModel):
    task_id: str
    status: str
    state_actions: List[V1StateAction]


class V1Task(BaseModel):
    id: str
    description: str
    attempts: List[V1Attempt]
