from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from mllm import V1Prompt
from pydantic import BaseModel, Field
from toolfuse.models import V1ToolRef

from ..chat import V1ChatEvent


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
    resource_id: Optional[str] = None
    with_resources: Optional[List[str]] = Field(
        default=None,
        description="A list of resource IDs of resource_type (EX. Action, Task) that the resource_id was mass reviewed with.",
    )
    parent_id: Optional[str] = None
    correction: Optional[str | Dict[str, Any]] = None
    correction_schema: Optional[Dict[str, Any]] = None
    created: float
    updated: Optional[float] = None


class V1Rating(BaseModel):
    """A review of an agent action"""

    id: str
    reviewer: str
    rating: int
    reviewer_type: str = ReviewerType.HUMAN.value
    rating_upper_bound: int = 5
    rating_lower_bound: int = 1
    reason: Optional[str] = None
    resource_type: str
    resource_id: Optional[str] = None
    with_resources: Optional[List[str]] = Field(
        default=None,
        description="A list of resource IDs of resource_type (EX. Action, Task) that the resource_id was mass reviewed with.",
    )
    parent_id: Optional[str] = None
    correction: Optional[str] = None
    correction_schema: Optional[Dict[str, Any]] = None
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

    images: Optional[List[str]] = None
    coordinates: Optional[Tuple[int, int]] = None
    video: Optional[str] = None
    text: Optional[str] = None
    timestamp: Optional[float] = None


class V1Reviewable(BaseModel):
    type: str
    id: str
    reviewable: Dict[str, Any]
    reviews: List[V1Review] = []
    resource_type: str
    resource_id: str
    created: float
    updated: Optional[float] = None


class V1ActionOpt(BaseModel):
    """An action that could have occurred"""

    id: str
    action: Optional[V1Action] = None
    prompt: Optional[V1Prompt] = None
    ratings: List[V1Rating] = []
    action_id: Optional[str] = None
    created: float
    updated: Optional[float] = None


class V1ActionEvent(BaseModel):
    """An action that has occurred"""

    id: str
    state: V1EnvState
    action: V1Action
    result: Any
    end_state: Optional[V1EnvState] = None
    event_order: Optional[int] = None
    tool: V1ToolRef
    namespace: str
    prompt: Optional[V1Prompt | V1ChatEvent] = None
    reviews: List[V1Review] = []
    reviewables: List[V1Reviewable] = []
    flagged: bool = False
    model: Optional[str] = None
    action_opts: Optional[List[V1ActionOpt]] = None
    agent_id: Optional[str] = None
    created: float
    started: float
    ended: float
    metadata: dict = {}
    episode_id: Optional[str] = None
    hidden: bool = False


class V1ActionEvents(BaseModel):
    """A list of action events"""

    events: List[V1ActionEvent] = []


class V1CreateActionEvent(
    BaseModel
):  # out of date, will need to be updated if we want to use it. Right now only in skillpacks server
    """An action that has occurred"""

    state: V1EnvState
    action: V1Action
    result: Any
    tool: V1ToolRef
    namespace: str
    metadata: dict = {}
    prompt: Optional[V1Prompt | V1ChatEvent] = None
    reviews: List[V1Review] = []
    reviewables: List[V1Reviewable] = []
    flagged: bool = False
    model: Optional[str] = None
    agent_id: Optional[str] = None


class V1ThoughtEvent(BaseModel):
    """An thought that has occurred"""

    id: str
    thought: str
    state: V1EnvState
    event_order: Optional[int] = None
    tool: Optional[V1ToolRef] = None
    namespace: str
    prompt: Optional[V1Prompt | V1ChatEvent] = None
    reviews: List[V1Review] = []
    reviewables: List[V1Reviewable] = []
    flagged: bool = False
    model: Optional[str] = None
    agent_id: Optional[str] = None
    created: float
    started: float
    ended: float
    metadata: dict = {}
    episode_id: Optional[str] = None
    hidden: bool = False


class V1Episode(BaseModel):
    """An agent episode"""

    actions: List[V1ActionEvent] = []
    tags: List[str] = []
    labels: Dict[str, Any] = {}
    device: Optional[str] = None
    device_type: Optional[str] = None


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


class V1BoundingBox(BaseModel):
    """A bounding box"""

    x0: int
    x1: int
    y0: int
    y1: int


class V1BoundingBoxReviewable(BaseModel):
    """A bounding box"""

    type: str = "BoundingBoxReviewable"
    img: str
    target: str
    bbox: V1BoundingBox


class V1AnnotationReviewable(BaseModel):
    """An annotation reviewable"""

    type: str = "AnnotationReviewable"
    key: str
    value: str
    annotator: Optional[str] = None
    annotator_type: str = ReviewerType.AGENT.value
