import time
from typing import Dict, Any, Optional, List
import json
import shortuuid

from mllm import Prompt
from sqlalchemy import asc

from .db.conn import WithDB
from .db.models import ActionRecord, EpisodeRecord, ReviewRecord
from .server.models import (
    V1ActionEvent,
    V1ToolRef,
    V1Action,
    V1Episode,
    V1EnvState,
    ReviewerType,
)
from .review import Review


class ActionEvent(WithDB):
    """An action taken by an agent."""

    def __init__(
        self,
        state: V1EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt] = None,
        result: Optional[Any] = None,
        end_state: Optional[V1EnvState] = None,
        namespace: str = "default",
        metadata: dict = {},
        flagged: bool = False,
        owner_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        reviews: Optional[List[Review]] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.state = state
        self.prompt = prompt
        self.action = action
        self.result = result
        self.end_state = end_state
        self.tool = tool
        self.namespace = namespace
        self.metadata = metadata
        self.created = time.time()
        self.flagged = flagged
        self.owner_id = owner_id
        self.model = model
        self.agent_id = agent_id
        self.reviews = reviews or []

    def post_review(
        self,
        reviewer: str,
        approved: bool,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> None:
        review = Review(
            reviewer=reviewer,
            approved=approved,
            reviewer_type=reviewer_type,
            reason=reason,
            parent_id=parent_id,
            resource_type="action",
            resource_id=self.id,
        )
        self.reviews.append(review)
        self.save()

    def to_v1(self) -> V1ActionEvent:
        return V1ActionEvent(
            id=self.id,
            state=self.state,
            prompt=self.prompt.to_v1() if self.prompt else None,
            action=self.action,
            result=self.result,
            end_state=self.end_state,
            tool=self.tool,
            namespace=self.namespace,
            created=self.created,
            flagged=self.flagged,
            model=self.model,
            agent_id=self.agent_id,
            metadata=self.metadata,
            reviews=[review.to_v1() for review in self.reviews] if self.reviews else [],
        )

    @classmethod
    def from_v1(
        cls, v1: V1ActionEvent, owner_id: Optional[str] = None
    ) -> "ActionEvent":
        event = cls.__new__(cls)
        event.id = v1.id
        event.state = v1.state
        event.action = v1.action
        event.tool = v1.tool
        event.prompt = (
            Prompt.from_v1(v1.prompt) if v1.prompt else None
        )  # Replace Prompt with your actual class
        event.result = v1.result
        event.end_state = v1.end_state
        event.namespace = v1.namespace
        event.metadata = v1.metadata
        event.flagged = v1.flagged
        event.owner_id = owner_id
        event.model = v1.model
        event.agent_id = v1.agent_id
        event.reviews = (
            [Review.from_v1(review_v1) for review_v1 in v1.reviews]
            if v1.reviews
            else []
        )
        event.created = v1.created
        return event

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            record = self.to_record()
            if self.prompt:
                self.prompt.save()
            db.merge(record)
            db.commit()

            # After committing the action, associate the reviews
            if self.reviews:
                for review in self.reviews:
                    review.save()
                # Refresh the record to get the latest state
                record = (
                    db.query(ActionRecord).filter(ActionRecord.id == self.id).first()
                )

                if not record:
                    raise ValueError(f"ActionRecord with id {self.id} not found")
                # Associate the reviews with the action via the association table
                record.reviews = [
                    db.query(ReviewRecord).filter_by(id=review.id).first()
                    for review in self.reviews
                ]
                db.commit()

    def to_record(self) -> ActionRecord:
        """Converts the instance to a database record."""
        prompt_id = self.prompt.id if self.prompt else None
        return ActionRecord(
            id=self.id,
            prompt_id=prompt_id,
            state=self.state.model_dump_json(),  # Adjust serialization as needed
            action=self.action.model_dump_json(),
            result=json.dumps(self.result),
            end_state=self.end_state.model_dump_json() if self.end_state else None,
            tool=self.tool.model_dump_json(),
            namespace=self.namespace,
            metadata_=json.dumps(self.metadata),
            flagged=self.flagged,
            created=self.created,
            owner_id=self.owner_id,
            model=self.model,
            agent_id=self.agent_id,
            # reviews are associated via the relationship, not stored directly
        )

    @classmethod
    def from_record(cls, record: ActionRecord) -> "ActionEvent":
        event = cls.__new__(cls)
        # Load reviews associated with the action
        reviews = [
            Review.from_record(review_record) for review_record in record.reviews
        ]
        event.id = record.id
        event.state = json.loads(record.state)  # type: ignore
        event.action = json.loads(record.action)  # type: ignore
        event.tool = json.loads(record.tool)  # type: ignore

        event.prompt = (
            Prompt.find(id=record.prompt_id)[0] if record.prompt_id else None  # type: ignore
        )  # Replace Prompt with your actual class
        event.result = json.loads(record.result)  # type: ignore
        event.end_state = json.loads(record.end_state) if record.end_state else None  # type: ignore
        event.namespace = record.namespace
        event.metadata = json.loads(record.metadata_)  # type: ignore
        event.flagged = record.flagged
        event.owner_id = record.owner_id
        event.model = record.model
        event.agent_id = record.agent_id
        event.reviews = reviews
        event.created = record.created
        return event

    @classmethod
    def find(cls, tool: Optional[Any] = None, **kwargs) -> List["ActionEvent"]:
        for db in cls.get_db():
            records = (
                db.query(ActionRecord)
                .filter_by(**kwargs)
                .order_by(ActionRecord.created.asc())
                .all()
            )
            out = [cls.from_record(record) for record in records]
            if tool:
                out = [
                    action
                    for action in out
                    if action.tool == tool  # Adjust comparison as needed
                ]
            return out
        raise ValueError("No database session available")

    def delete(self) -> None:
        """Deletes the instance from the database."""
        for db in self.get_db():
            record = db.query(ActionRecord).filter(ActionRecord.id == self.id).first()
            if record:
                # Optionally delete associated reviews
                for review in self.reviews:
                    review.delete()
                db.delete(record)
                db.commit()
            else:
                raise ValueError("ActionEvent not found")


class Episode(WithDB):
    """An agent episode"""

    def __init__(
        self,
        actions: List[ActionEvent] = [],
        remote: Optional[str] = None,
        tags: List[str] = [],
        labels: Dict[str, Any] = {},
        owner_id: Optional[str] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.actions = actions
        self.created = time.time()
        self.updated = time.time()
        self.remote = remote
        self.tags = tags
        self.labels = labels
        self.owner_id = owner_id

    def to_v1(self) -> V1Episode:
        """Converts the instance to a V1Episode."""
        return V1Episode(
            actions=[action.to_v1() for action in self.actions],
            tags=self.tags,
            labels=self.labels,
        )

    @classmethod
    def from_v1(cls, v1: V1Episode, owner_id: Optional[str] = None) -> "Episode":
        """Creates an instance from a V1Episode object."""
        episode = cls.__new__(cls)
        episode.id = str(
            shortuuid.uuid()
        )  # Generate a new ID or retrieve from context if needed
        episode.actions = [ActionEvent.from_v1(action) for action in v1.actions]
        episode.tags = v1.tags
        episode.labels = v1.labels
        episode.created = time.time()
        episode.updated = time.time()
        episode.owner_id = owner_id
        return episode

    def record_event(self, action: ActionEvent) -> None:
        """Records an action to the episode."""
        self.actions.append(action)
        self.updated = time.time()
        self.save()

    def record(
        self,
        state: V1EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt | str] = None,
        result: Optional[Any] = None,
        end_state: Optional[V1EnvState] = None,
        namespace: str = "default",
        metadata: dict = {},
        owner_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> ActionEvent:
        """Records an action to the episode."""
        if isinstance(prompt, str):
            prompt = Prompt.find(id=prompt)[0]

        event = ActionEvent(
            state=state,
            prompt=prompt,
            action=action,
            result=result,
            end_state=end_state,
            tool=tool,
            namespace=namespace,
            metadata=metadata,
            owner_id=owner_id,
            model=model,
            agent_id=agent_id,
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
            owner_id=self.owner_id,
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
        episode.owner_id = record.owner_id
        return episode

    @classmethod
    def find(cls, **kwargs) -> List["Episode"]:
        for db in cls.get_db():
            records = (
                db.query(EpisodeRecord)
                .filter_by(**kwargs)
                .order_by(asc(EpisodeRecord.created))
                .all()
            )
            return [cls.from_record(record) for record in records]

        raise ValueError("no session")

    def get_event(self, id: str) -> ActionEvent:
        """Retrieves a single action event by ID."""
        for db in self.get_db():
            record = db.query(ActionRecord).filter(ActionRecord.id == id).first()
            if record:
                return ActionEvent.from_record(record)
            raise ValueError("No action event found with id " + id)
        raise ValueError("no session")

    def delete(self) -> None:
        """Deletes the episode and all associated actions from the database."""
        for db in self.get_db():
            # Delete all associated action records first
            action_records = (
                db.query(ActionRecord).filter(ActionRecord.episode_id == self.id).all()
            )
            for action_record in action_records:
                db.delete(action_record)

            # Now delete the episode record
            episode_record = (
                db.query(EpisodeRecord).filter(EpisodeRecord.id == self.id).first()
            )
            if episode_record:
                db.delete(episode_record)
                db.commit()
            else:
                raise ValueError("Episode record not found")

    def fail_one(
        self,
        event_id: str,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
    ) -> None:
        """Fail the given event."""
        for event in self.actions:
            if event.id == event_id:
                event.post_review(
                    reviewer=reviewer,
                    reviewer_type=reviewer_type,
                    reason=reason,
                    approved=False,
                )
                break

    def approve_one(
        self,
        event_id: str,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
    ) -> None:
        """Approve the given event."""
        for event in self.actions:
            if event.id == event_id:
                event.post_review(
                    reviewer=reviewer,
                    reviewer_type=reviewer_type,
                    reason=reason,
                    approved=True,
                )
                break

    def approve_all(
        self,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
    ) -> None:
        """Approve all actions in the episode."""
        for event in self.actions:
            event.post_review(
                reviewer=reviewer,
                reviewer_type=reviewer_type,
                approved=True,
            )
        self.save()

    def fail_all(
        self,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
    ) -> None:
        """Fail all actions in the episode."""
        for event in self.actions:
            event.post_review(
                reviewer=reviewer,
                reviewer_type=reviewer_type,
                approved=False,
            )
        self.save()

    def approve_prior(
        self,
        event_id: str,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
    ) -> None:
        """Approve the given event and all prior actions."""
        self.approve_one(event_id, reviewer, reviewer_type)
        for i in range(len(self.actions) - 1):
            if self.actions[i].id == event_id:
                for j in range(i + 1, len(self.actions)):
                    self.actions[j].post_review(
                        reviewer=reviewer,
                        reviewer_type=reviewer_type,
                        approved=True,
                    )
        self.save()

    def fail_prior(
        self,
        event_id: str,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
    ) -> None:
        """Approve the given event and all prior actions."""
        self.approve_one(event_id, reviewer, reviewer_type)
        for i in range(len(self.actions) - 1):
            if self.actions[i].id == event_id:
                for j in range(i + 1, len(self.actions)):
                    self.actions[j].post_review(
                        reviewer=reviewer,
                        reviewer_type=reviewer_type,
                        approved=True,
                    )
        self.save()
