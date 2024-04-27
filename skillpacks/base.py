import time
from typing import Dict, Any, Optional, List
import uuid
import json
import os

from pydantic import BaseModel
from mllm import Prompt, PromptModel

from .db.conn import WithDB
from .db.models import ActionRecord, EpisodeRecord
from .models import V1ActionEvent, V1ToolRef, V1ActionSelection, V1Action, V1Episode
from .env import HUB_API_KEY_ENV


class ActionEvent(WithDB):
    """An action taken by an agent."""

    def __init__(
        self,
        prompt: Prompt,
        action: V1Action,
        tool: V1ToolRef,
        result: Optional[Any] = None,
        namespace: str = "default",
        metadata: dict = {},
        approved: bool = False,
        flagged: bool = False,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.prompt = prompt
        self.action = action
        self.result = result
        self.tool = tool
        self.namespace = namespace
        self.metadata = metadata
        self.created = time.time()
        self.approved = approved
        self.flagged = flagged

    def to_v1(self) -> V1ActionEvent:
        return V1ActionEvent(
            id=self.id,
            prompt=self.prompt.to_schema(),
            action=self.action,
            result=self.result,
            tool=self.tool,
            namespace=self.namespace,
            created=self.created,
        )

    @classmethod
    def from_v1(cls, v1: V1ActionEvent) -> "ActionEvent":
        event = cls.__new__(cls)
        event.id = v1.id
        event.prompt = Prompt.from_schema(v1.prompt)
        event.action = v1.action
        event.result = v1.result
        event.tool = v1.tool
        event.namespace = v1.namespace
        event.created = v1.created
        event.approved = v1.approved
        event.flagged = v1.flagged
        return event

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

    def to_record(self) -> ActionRecord:
        """Converts the instance to a database record."""
        return ActionRecord(
            id=self.id,
            prompt_id=self.prompt.id,
            action=json.dumps(self.action.model_dump()),
            result=json.dumps(self.result),
            tool=json.dumps(self.tool.model_dump()),
            namespace=self.namespace,
            metadata_=json.dumps(self.metadata),
            approved=self.approved,
            flagged=self.flagged,
            created=self.created,
        )

    @classmethod
    def from_record(cls, record: ActionRecord) -> "ActionEvent":
        """Creates an instance from a database record using the __new__ method."""
        event = cls.__new__(cls)
        event.id = record.id
        event.prompt = Prompt.find(id=str(record.prompt_id))[0]
        event.action = V1Action.model_validate_json(str(record.action))
        event.result = json.loads(str(record.result))
        event.tool = V1ToolRef.model_validate_json(str(record.tool))
        event.namespace = record.namespace
        event.metadata = json.loads(str(record.metadata_))
        event.created = record.created
        event.approved = record.approved
        event.flagged = record.flagged
        return event


class Episode(WithDB):
    """An agent episode"""

    def __init__(
        self,
        actions: List[ActionEvent] = [],
        remote: Optional[str] = None,
        tags: List[str] = [],
        labels: Dict[str, Any] = {},
    ) -> None:
        self.id = str(uuid.uuid4())
        self.actions = actions
        self.created = time.time()
        self.updated = time.time()
        self.remote = remote
        self.tags = tags
        self.labels = labels

    def to_v1(self) -> V1Episode:
        """Converts the instance to a V1Episode."""
        return V1Episode(
            actions=[action.to_v1() for action in self.actions],
            tags=self.tags,
            labels=self.labels,
        )

    @classmethod
    def from_v1(cls, v1: V1Episode) -> "Episode":
        """Creates an instance from a V1Episode object."""
        episode = cls.__new__(cls)
        episode.id = str(
            uuid.uuid4()
        )  # Generate a new ID or retrieve from context if needed
        episode.actions = [ActionEvent.from_v1(action) for action in v1.actions]
        episode.tags = v1.tags
        episode.labels = v1.labels
        episode.created = time.time()
        episode.updated = time.time()
        return episode

    def record_event(self, action: ActionEvent) -> None:
        """Records an action to the episode."""
        self.actions.append(action)
        self.updated = time.time()
        self.save()

    def record(
        self,
        prompt: Prompt | str,
        action: V1Action,
        tool: V1ToolRef,
        result: Optional[Any] = None,
        namespace: str = "default",
        metadata: dict = {},
    ) -> ActionEvent:
        """Records an action to the episode."""
        if isinstance(prompt, str):
            prompt = Prompt.find(prompt_id=prompt)[0]

        event = ActionEvent(
            prompt=prompt,
            action=action,
            result=result,
            tool=tool,
            namespace=namespace,
            metadata=metadata,
        )
        self.record_event(event)

        return event

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

    def to_record(self) -> EpisodeRecord:
        """Converts the episode instance to a database record."""
        episode_record = EpisodeRecord(
            id=self.id,
            tags=json.dumps(self.tags),
            labels=json.dumps(self.labels),
            created=self.created,
            updated=self.updated,
        )
        # Convert all actions to records and associate with this episode record
        episode_record.actions = [action.to_record() for action in self.actions]
        return episode_record

    @classmethod
    def from_record(cls, record: EpisodeRecord) -> "Episode":
        """Creates an episode instance from a database record."""
        episode = cls.__new__(cls)
        episode.id = record.id
        episode.actions = [ActionEvent.from_record(action) for action in record.actions]
        episode.tags = json.loads(str(record.tags))
        episode.labels = json.loads(str(record.labels))
        episode.created = record.created
        episode.updated = record.updated
        return episode
