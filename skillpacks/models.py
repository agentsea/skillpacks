from typing import Optional, Dict, Any, List

from pydantic import BaseModel
from mllm import PromptModel


class V1ToolRef(BaseModel):
    """A reference to a tool or device"""

    module: str
    name: str
    version: Optional[str] = None


class V1Action(BaseModel):
    """An action on a tool"""

    name: str
    parameters: Dict[str, Any]


class V1ActionSelection(BaseModel):
    """An action selection from the model"""

    observation: str
    reason: str
    action: V1Action


class V1ActionEvent(BaseModel):
    """An action that has occurred"""

    id: str
    prompt: PromptModel
    action: V1Action
    result: Any
    tool: V1ToolRef
    namespace: str
    approved: bool = False
    flagged: bool = False
    created: float


class V1CreateActionEvent(BaseModel):
    """An action that has occurred"""

    prompt: PromptModel
    action: V1Action
    result: Any
    tool: V1ToolRef
    namespace: str


class V1Episode(BaseModel):
    """An agent episode"""

    actions: List[V1ActionEvent]
    tags: List[str] = []
    labels: Dict[str, Any] = {}
