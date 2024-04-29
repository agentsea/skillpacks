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
    model: Optional[str] = None
    agent_id: Optional[str] = None
    created: float


class V1ActionEvents(BaseModel):
    """A list of action events"""

    events: List[V1ActionEvent] = []


class V1CreateActionEvent(BaseModel):
    """An action that has occurred"""

    prompt: PromptModel
    action: V1Action
    result: Any
    tool: V1ToolRef
    namespace: str
    metadata: dict = {}
    approved: bool = False
    flagged: bool = False
    model: Optional[str] = None
    agent_id: Optional[str] = None


class V1Episode(BaseModel):
    """An agent episode"""

    actions: List[V1ActionEvent] = []
    tags: List[str] = []
    labels: Dict[str, Any] = {}


class V1Episodes(BaseModel):
    """A list of episodes"""

    episodes: List[V1Episode] = []


class V1UserProfile(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    handle: Optional[str] = None
    picture: Optional[str] = None
    created: Optional[int] = None
    updated: Optional[int] = None
    token: Optional[str] = None
