import time
from typing import Dict, Any, Optional, List
import json
import shortuuid

from mllm import Prompt
from sqlalchemy import asc

from .db.conn import WithDB
from .db.models import ActionRecord, EpisodeRecord, ReviewRecord, ReviewableRecord
from .server.models import (
    V1ActionEvent,
    V1ToolRef,
    V1Action,
    V1Episode,
    ReviewerType,
    V1EnvState,
)
from .review import Review
from .reviewable import Reviewable, reviewable_type_map, reviewable_string_map

# from .img import convert_images not used, do we need it?
from .state import EnvState


class ActionEvent(WithDB):
    """An action taken by an agent."""

    def __init__(
        self,
        state: EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt] = None,
        result: Optional[Any] = None,
        end_state: Optional[EnvState] = None,
        namespace: str = "default",
        metadata: Optional[dict] = None,
        flagged: bool = False,
        owner_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        reviews: Optional[List[Review]] = None,
        reviewables: Optional[List[Reviewable]] = None,
        hidden: bool = False,
        episode_id: Optional[str] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.state = state
        self.prompt = prompt
        self.action = action
        self.result = result
        self.end_state = end_state
        self.tool = tool
        self.namespace = namespace
        self.metadata = metadata if metadata else {}
        self.created = time.time()
        self.flagged = flagged
        self.owner_id = owner_id
        self.model = model
        self.agent_id = agent_id
        self.reviews = reviews or []
        self.reviewables = reviewables or []
        self.hidden = hidden
        self.episode_id = episode_id

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

    def post_reviewable(self, type: str, **kwargs) -> None:
        # Ensure the provided type is valid by checking the string map
        if type not in reviewable_string_map:
            raise ValueError(f"Invalid reviewable type: {type}")

        # Fetch the reviewable class dynamically from the reviewable_type_map using the string map
        reviewable_class = reviewable_type_map.get(reviewable_string_map[type])

        if reviewable_class is None:
            raise ValueError(f"Reviewable class for type '{type}' not found.")

        # Create an instance of the reviewable dynamically using the class
        reviewable = reviewable_class(
            **kwargs,
            resource_type="action",
            resource_id=self.id,  # Set the resource ID to the action's ID
        )

        # Add the new reviewable to the action's reviewables list and save the action
        self.reviewables.append(reviewable)
        self.save()

    def to_v1(self) -> V1ActionEvent:
        return V1ActionEvent(
            id=self.id,
            state=self.state.to_v1(),
            prompt=self.prompt.to_v1() if self.prompt else None,
            action=self.action,
            result=self.result,
            end_state=self.end_state.to_v1() if self.end_state else None,
            tool=self.tool,
            namespace=self.namespace,
            created=self.created,
            flagged=self.flagged,
            model=self.model,
            agent_id=self.agent_id,
            metadata=self.metadata,
            reviews=[review.to_v1() for review in self.reviews] if self.reviews else [],
            reviewables=[
                reviewable.to_v1Reviewable() for reviewable in self.reviewables
            ]
            if self.reviewables
            else [],
            episode_id=self.episode_id,
            hidden=self.hidden,
        )

    @classmethod
    def from_v1(
        cls, v1: V1ActionEvent, owner_id: Optional[str] = None
    ) -> "ActionEvent":
        event = cls.__new__(cls)
        event.id = v1.id
        event.state = EnvState.from_v1(v1.state)
        event.action = v1.action
        event.tool = v1.tool
        event.prompt = (
            Prompt.from_v1(v1.prompt) if v1.prompt else None
        )  # Replace Prompt with your actual class
        event.result = v1.result
        event.end_state = EnvState.from_v1(v1.end_state) if v1.end_state else None
        event.namespace = v1.namespace
        event.metadata = v1.metadata
        event.flagged = v1.flagged
        event.owner_id = owner_id
        event.model = v1.model
        event.agent_id = v1.agent_id
        event.episode_id = v1.episode_id
        event.reviews = (
            [Review.from_v1(review_v1) for review_v1 in v1.reviews]
            if v1.reviews
            else []
        )
        event.reviewables = (
            [
                Reviewable.from_v1Reviewable(reviewable_v1)
                for reviewable_v1 in v1.reviewables
            ]
            if v1.reviewables
            else []
        )
        event.created = v1.created
        event.hidden = v1.hidden
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
                    if not review.resource_id:
                        review.resource_id = self.id
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

            # After committing the action, associate the reviewables TODO combine this with reviews if possible
            if self.reviewables:
                for reviewable in self.reviewables:
                    if not reviewable.resource_id:
                        reviewable.resource_id = self.id
                    reviewable.save()
                # Refresh the record to get the latest state
                record = (
                    db.query(ActionRecord).filter(ActionRecord.id == self.id).first()
                )

                if not record:
                    raise ValueError(f"ActionRecord with id {self.id} not found")
                # Associate the reviewables with the action via the association table
                record.reviewables = [
                    db.query(ReviewableRecord).filter_by(id=reviewable.id).first()
                    for reviewable in self.reviewables
                ]
            db.commit()

    def to_record(self) -> ActionRecord:
        """Converts the instance to a database record."""
        prompt_id = None
        if self.prompt:
            prompt_id = self.prompt.id

        return ActionRecord(
            id=self.id,
            prompt_id=prompt_id,
            state=self.state.to_v1().model_dump_json(),  # Adjust serialization as needed
            action=self.action.model_dump_json(),
            result=json.dumps(self.result),
            end_state=self.end_state.to_v1().model_dump_json()
            if self.end_state
            else None,
            tool=self.tool.model_dump_json(),
            namespace=self.namespace,
            metadata_=json.dumps(self.metadata),
            flagged=self.flagged,
            created=self.created,
            owner_id=self.owner_id,
            model=self.model,
            agent_id=self.agent_id,
            episode_id=self.episode_id,
            hidden=self.hidden,
        )

    @classmethod
    def from_record(cls, record: ActionRecord) -> "ActionEvent":
        event = cls.__new__(cls)
        # Load reviews associated with the action
        reviews = [
            Review.from_record(review_record) for review_record in record.reviews
        ]
        reviewables = [
            Reviewable.from_record(reviewable_record)
            for reviewable_record in record.reviewables
        ]
        event.id = record.id
        event.state = EnvState.from_v1(V1EnvState.model_validate_json(record.state))  # type: ignore
        event.action = V1Action.model_validate_json(record.action)  # type: ignore
        event.tool = V1ToolRef.model_validate_json(record.tool)  # type: ignore

        event.prompt = (
            Prompt.find(id=record.prompt_id)[0] if record.prompt_id else None  # type: ignore
        )  # Replace Prompt with your actual class
        event.result = json.loads(record.result)  # type: ignore
        event.end_state = (
            EnvState.from_v1(V1EnvState.model_validate_json(record.end_state))  # type: ignore
            if record.end_state  # type: ignore
            else None
        )  # type: ignore
        event.namespace = record.namespace
        event.metadata = json.loads(record.metadata_)  # type: ignore
        event.flagged = record.flagged
        event.owner_id = record.owner_id
        event.model = record.model
        event.agent_id = record.agent_id
        event.reviews = reviews
        event.reviewables = reviewables
        event.created = record.created
        event.episode_id = record.episode_id
        event.hidden = record.hidden
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
        actions: Optional[List[ActionEvent]] = None,
        remote: Optional[str] = None,
        tags: Optional[List[str]] = None,
        labels: Optional[Dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        device: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.actions = actions if actions else []
        self.created = time.time()
        self.updated = time.time()
        self.remote = remote
        self.tags = tags if tags else []
        self.labels = labels if labels else {}
        self.owner_id = owner_id
        self.device = device
        self.device_type = device_type

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
        episode.device = v1.device
        episode.device_type = v1.device_type
        episode.created = time.time()
        episode.updated = time.time()
        episode.owner_id = owner_id
        return episode

    def record_event(self, action: ActionEvent) -> None:
        """Records an action to the episode."""
        action.episode_id = self.id
        self.actions.append(action)
        self.updated = time.time()
        self.save()

    def record(
        self,
        state: EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt | str] = None,
        result: Optional[Any] = None,
        end_state: Optional[EnvState] = None,
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
            episode_id=self.id,
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
            device=self.device,
            device_type=self.device_type,
            actions=[action.to_record() for action in self.actions],
        )
        # Convert all actions to records and associate with this episode record
        return episode_record

    @classmethod
    def from_record(cls, record: EpisodeRecord) -> "Episode":
        """Creates an episode instance from a database record."""
        episode = cls.__new__(cls)
        episode.id = record.id
        episode.actions = [
            ActionEvent.from_record(action)
            for action in sorted(record.actions, key=lambda x: x.created)
        ]
        episode.tags = json.loads(str(record.tags))
        episode.labels = json.loads(str(record.labels))
        episode.created = record.created
        episode.updated = record.updated
        episode.owner_id = record.owner_id
        episode.device = record.device  # Retrieve device
        episode.device_type = record.device_type  # Retrieve device_type
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
        # Find the index of the target event
        target_index = None
        for index, event in enumerate(self.actions):
            if event.id == event_id:
                target_index = index
                break

        if target_index is None:
            raise ValueError(f"ActionEvent with id {event_id} not found")

        # Approve the target event and all prior events
        for i in range(target_index + 1):
            self.actions[i].post_review(
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
        """Fail the given event and all prior actions."""
        # Find the index of the target event
        target_index = None
        for index, event in enumerate(self.actions):
            if event.id == event_id:
                target_index = index
                break

        if target_index is None:
            raise ValueError(f"ActionEvent with id {event_id} not found")

        # Fail the target event and all prior events
        for i in range(target_index + 1):
            self.actions[i].post_review(
                reviewer=reviewer,
                reviewer_type=reviewer_type,
                approved=False,
            )

        self.save()
