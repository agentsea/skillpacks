from typing import Any, Dict, List, Optional
from enum import Enum

from mllm import V1Prompt
from pydantic import BaseModel, Field
from toolfuse.models import V1ToolRef


class ReviewerType(Enum):
    HUMAN = "human"
    AGENT = "agent"


class V1Review(BaseModel):
    """A review of an agent action"""

    id: str
    reviewer: str
    approved: bool
    reviewer_type: str = ReviewerType.HUMAN.value
    reason: Optional[str] = None
    resource_type: str
    resource_id: str
    parent_id: Optional[str] = None
    created: float
    updated: Optional[float] = None


class V1Action(BaseModel):
    """An action on a tool"""

    name: str = Field(..., description="The name of the action to be performed.")
    parameters: Dict[str, Any] = Field(
        ...,
        description="A dictionary containing parameters necessary for the action, with keys as parameter names and values as parameter details.",
    )


class V1ActionSelection(BaseModel):
    """An action selection from the model"""

    observation: str = Field(
        ..., description="Observations of the current state of the environment"
    )
    reason: str = Field(
        ...,
        description="The reason why this action was chosen, explaining the logic or rationale behind the decision.",
    )
    action: V1Action = Field(
        ...,
        description="The action object detailing the specific action to be taken, including its name and parameters.",
    )
    expectation: str = Field(
        ...,
        description="The expected outcome of the action e.g. 'a login page should open'",
    )


class V1EnvState(BaseModel):
    """The state of the environment"""

    image: Optional[str] = None


class V1ActionEvent(BaseModel):
    """An action that has occurred"""

    id: str
    state: V1EnvState
    action: V1Action
    result: Any
    end_state: Optional[V1EnvState] = None
    tool: V1ToolRef
    namespace: str
    prompt: Optional[V1Prompt] = None
    reviews: List[V1Review] = []
    flagged: bool = False
    model: Optional[str] = None
    agent_id: Optional[str] = None
    created: float
    metadata: dict = {}


class V1ActionEvents(BaseModel):
    """A list of action events"""

    events: List[V1ActionEvent] = []


class V1CreateActionEvent(BaseModel):
    """An action that has occurred"""

    state: V1EnvState
    action: V1Action
    result: Any
    tool: V1ToolRef
    namespace: str
    metadata: dict = {}
    prompt: Optional[V1Prompt] = None
    reviews: List[V1Review] = []
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
