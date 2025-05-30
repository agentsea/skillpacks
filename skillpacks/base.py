import json
import time
from typing import Any, Dict, List, Optional

import shortuuid
from mllm import Prompt
from sqlalchemy import asc
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import StaleDataError

from skillpacks.action_opts import ActionOpt
from skillpacks.rating import Rating

from .chat import V1ChatEvent
from .db.conn import WithDB
from .db.models import (
    ActionRecord,
    EpisodeRecord,
    ReviewableRecord,
    ReviewRecord,
)
from .review import Resource, Review
from .reviewable import Reviewable, reviewable_string_map, reviewable_type_map
from .server.models import (
    ReviewerType,
    V1Action,
    V1ActionEvent,
    V1EnvState,
    V1Episode,
    V1ToolRef,
)
from .state import EnvState


class ActionEvent(WithDB):
    """An action taken by an agent."""

    def __init__(
        self,
        state: EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt | V1ChatEvent] = None,
        result: Optional[Any] = None,
        end_state: Optional[EnvState] = None,
        event_order: Optional[int] = None,
        namespace: str = "default",
        metadata: Optional[dict[str, Any]] = None,
        flagged: bool = False,
        owner_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        reviews: Optional[List[Review]] = None,
        reviewables: Optional[List[Reviewable[Any, Any]]] = None,
        action_opts: Optional[List[ActionOpt]] = None,
        hidden: bool = False,
        episode_id: Optional[str] = None,
        started: Optional[float] = None,
        ended: Optional[float] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.state = state
        self.prompt = prompt
        self.action = action
        self.result = result
        self.end_state = end_state
        self.event_order = event_order
        self.tool = tool
        self.namespace = namespace
        self.metadata = metadata if metadata else {}
        self.created = time.time()
        self.started = started if started else time.time()
        self.ended = ended if ended else time.time()
        self.flagged = flagged
        self.owner_id = owner_id
        self.model = model
        self.agent_id = agent_id
        self.reviews = reviews or []
        self.reviewables = reviewables or []
        self.action_opts = action_opts or []
        self.hidden = hidden
        self.episode_id = episode_id

        # Set action_id for each ActionOpt
        for action_opt in self.action_opts:
            action_opt.action_id = self.id

    def add_actionOpt(
        self,
        action: V1Action,
        prompt: Optional[Prompt] = None,
        ratings: List[Rating] = [],
        created: Optional[float] = None,
        updated: Optional[float] = None,
    ) -> None:
        actionOpt = ActionOpt(
            action=action,
            prompt=prompt,
            ratings=ratings,
            created=created,
            updated=updated,
            action_id=self.id,
        )
        self.action_opts.append(actionOpt)
        self.save()

    def post_review(
        self,
        reviewer: str,
        approved: bool,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        parent_id: Optional[str] = None,
        correction: Optional[V1Action] = None,
    ) -> None:
        reviewerReview = False
        correctionRecord = correction.model_dump_json() if correction else None
        correctionSchema = V1Action
        for review in self.reviews:
            if review.reviewer == reviewer and review.reviewer_type == reviewer_type:
                reviewerReview = True
                review.approved = approved
                review.reason = reason
                review.updated = time.time()
                review.correction = (
                    correctionRecord if correctionRecord else review.correction
                )

        if not reviewerReview:
            review = Review(
                reviewer=reviewer,
                approved=approved,
                reviewer_type=reviewer_type,
                reason=reason,
                parent_id=parent_id,
                resource_type=Resource.Action.value,
                resource_id=self.id,
                correction=correctionRecord,
                correction_schema=correctionSchema,
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
            resource_type=Resource.Action.value,
            resource_id=self.id,  # Set the resource ID to the action's ID
        )

        # Add the new reviewable to the action's reviewables list and save the action
        self.reviewables.append(reviewable)
        self.save()

    def to_v1(self) -> V1ActionEvent:
        if isinstance(self.prompt, V1ChatEvent):
            prompt = self.prompt
        else:
            prompt = self.prompt.to_v1() if self.prompt else None
        return V1ActionEvent(
            id=self.id,
            state=self.state.to_v1(),
            prompt=prompt,
            action=self.action,
            result=self.result,
            end_state=self.end_state.to_v1() if self.end_state else None,
            tool=self.tool,
            namespace=self.namespace,
            event_order=self.event_order,
            created=self.created,
            started=self.started,
            ended=self.ended,
            flagged=self.flagged,
            model=self.model,
            agent_id=self.agent_id,
            metadata=self.metadata,
            action_opts=[actionOpt.to_v1() for actionOpt in self.action_opts],
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
        if isinstance(v1.prompt, V1ChatEvent):
            event.prompt = v1.prompt
        else:
            event.prompt = Prompt.from_v1(v1.prompt) if v1.prompt else None
        event.result = v1.result
        event.result = v1.result
        event.end_state = EnvState.from_v1(v1.end_state) if v1.end_state else None
        event.namespace = v1.namespace
        event.metadata = v1.metadata
        event.flagged = v1.flagged
        event.owner_id = owner_id
        event.model = v1.model
        event.agent_id = v1.agent_id
        event.episode_id = v1.episode_id
        event.action_opts = (
            [ActionOpt.from_v1(actionOpt_v1) for actionOpt_v1 in v1.action_opts]
            if v1.action_opts
            else []
        )
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
        event.started = v1.started
        event.ended = v1.ended
        event.hidden = v1.hidden
        event.event_order = v1.event_order
        return event

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            try:
                record = self.to_record()
                if self.prompt:
                    if isinstance(self.prompt, Prompt):
                        self.prompt.save()
                merged_record = db.merge(record)

                # Associate the reviews
                if self.reviews:
                    for review in self.reviews:
                        if not review.resource_id:
                            review.resource_id = self.id
                        if not review.resource_type:
                            review.resource_type = Resource.Action.value
                        review.save()

                    # Associate the freshly saved ReviewRecords with the merged ActionRecord
                    merged_record.reviews = [
                        db.query(ReviewRecord).filter_by(id=r.id).one()
                        for r in self.reviews
                    ]

                # Handle Reviewables
                if self.reviewables:
                    for reviewable in self.reviewables:
                        if not reviewable.resource_id:
                            reviewable.resource_id = self.id
                        if not reviewable.resource_type:
                            reviewable.resource_type = Resource.Action.value
                        reviewable.save()

                    merged_record.reviewables = [
                        db.query(ReviewableRecord).filter_by(id=rv.id).one()
                        for rv in self.reviewables
                    ]

                # After committing the action, associate the action_opts
                if self.action_opts:
                    for action_opt in self.action_opts:
                        action_opt.action_id = self.id
                        action_opt.save()
                    # Refresh the record to get the latest state
                    record = (
                        db.query(ActionRecord)
                        .filter(ActionRecord.id == self.id)
                        .first()
                    )
                    if not record:
                        raise ValueError(f"ActionRecord with id {self.id} not found")

                db.commit()
            except StaleDataError:
                # This indicates another transaction updated this ActionRecord
                # (version_id) before we could commit.
                db.rollback()
                print(
                    f"Concurrent update detected, trying so save again with updates reviews and reviewables, lost version is {self.to_v1()}",
                    flush=True,
                )
                try:
                    # Reload the latest ActionRecord from the database
                    latest_record = (
                        db.query(ActionRecord).filter(ActionRecord.id == self.id).one()
                    )

                    concurrent_update_for_associated_object = False

                    # Merge missing Reviews
                    if self.reviews:
                        existing_review_ids = {
                            review.id for review in latest_record.reviews
                        }
                        new_reviews = [
                            r for r in self.reviews if r.id not in existing_review_ids
                        ]
                        for review in new_reviews:
                            concurrent_update_for_associated_object = True
                            if not review.resource_id:
                                review.resource_id = self.id
                            if not review.resource_type:
                                review.resource_type = Resource.Action.value
                            review.save()
                            latest_record.reviews.append(review)

                    # Merge missing Reviewables
                    if self.reviewables:
                        existing_reviewable_ids = {
                            rv.id for rv in latest_record.reviewables
                        }
                        new_reviewables = [
                            rv
                            for rv in self.reviewables
                            if rv.id not in existing_reviewable_ids
                        ]
                        for reviewable in new_reviewables:
                            concurrent_update_for_associated_object = True
                            if not reviewable.resource_id:
                                reviewable.resource_id = self.id
                            if not reviewable.resource_type:
                                reviewable.resource_type = Resource.Action.value
                            reviewable.save()
                            latest_record.reviewables.append(reviewable)

                    # Handle ActionOpts (assuming they are won't be a conflict)
                    if self.action_opts:
                        existing_action_opt_ids = {
                            opt.id for opt in latest_record.action_opts
                        }
                        new_action_opts = [
                            opt
                            for opt in self.action_opts
                            if opt.id not in existing_action_opt_ids
                        ]
                        for action_opt in new_action_opts:
                            concurrent_update_for_associated_object = True
                            action_opt.action_id = self.id
                            action_opt.save()
                            latest_record.action_opts.append(action_opt)
                        # No need to reassign action_opts if they are already handled

                    if concurrent_update_for_associated_object:
                        # Retry the commit once
                        db.commit()
                        print(
                            f"Successfully retried action save {self.to_v1()}",
                            flush=True,
                        )
                    else:
                        print(
                            f"concurrent update was not an associated object not retrying, lost action: {self.to_v1()} existing action: {self.from_record(latest_record).to_v1()}"
                        )
                except StaleDataError:
                    db.rollback()
                    raise ValueError(
                        f"Concurrent update detected again and could not resolve the conflict; please retry. {self.to_v1()}"
                    )
                except Exception as e:
                    db.rollback()
                    raise ValueError(
                        f"An error occurred while handling concurrent updates: {str(e)} Action lost: {self.to_v1()}"
                    )

    def to_record(self) -> ActionRecord:
        """Converts the instance to a database record."""
        prompt = None
        if self.prompt:
            if isinstance(self.prompt, Prompt):
                prompt = self.prompt.id
            else:
                prompt = self.prompt.model_dump_json()

        return ActionRecord(
            id=self.id,
            prompt_id=prompt,
            state=self.state.to_v1().model_dump_json(),  # Adjust serialization as needed
            action=self.action.model_dump_json(),
            result=json.dumps(self.result),
            end_state=self.end_state.to_v1().model_dump_json()
            if self.end_state
            else None,
            event_order=self.event_order,
            tool=self.tool.model_dump_json(),
            namespace=self.namespace,
            metadata_=json.dumps(self.metadata),
            flagged=self.flagged,
            created=self.created,
            started=self.started,
            ended=self.ended,
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
        # Load action_opts associated with the action
        action_opts = [
            ActionOpt.from_record(action_opt_record)
            for action_opt_record in record.action_opts
        ]
        event.id = record.id
        event.state = EnvState.from_v1(V1EnvState.model_validate_json(record.state))  # type: ignore
        event.action = V1Action.model_validate_json(record.action)  # type: ignore
        event.tool = V1ToolRef.model_validate_json(record.tool)  # type: ignore
        try:
            event.prompt = V1ChatEvent.model_validate_json(record.prompt_id)  # type: ignore
        except Exception:
            event.prompt = (
                Prompt.find(id=record.prompt_id)[0] if record.prompt_id else None  # type: ignore
            )  # type: ignore
        event.result = json.loads(record.result)  # type: ignore
        event.end_state = (
            EnvState.from_v1(V1EnvState.model_validate_json(record.end_state))  # type: ignore
            if record.end_state  # type: ignore
            else None
        )  # type: ignore
        event.event_order = record.event_order
        event.action_opts = action_opts
        event.namespace = record.namespace
        event.metadata = json.loads(record.metadata_)  # type: ignore
        event.flagged = record.flagged
        event.owner_id = record.owner_id
        event.model = record.model
        event.agent_id = record.agent_id
        event.reviews = reviews
        event.reviewables = reviewables
        event.created = record.created
        event.started = record.started
        event.ended = record.ended
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
                # for reviewable in record.reviewables:
                #     reviewable = Reviewable.from_record(reviewable)
                #     reviewable.delete()

                # # Optionally delete associated reviews
                # for review in record.reviews:
                #     db.delete(review)

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
        print(
            f"saving and recording action: {action.id} event_order: {action.event_order} episode: {self.id}",
            flush=True,
        )
        action.save()
        # update in-memory copy only
        self.actions.append(action)
        self.updated = time.time()
        # minimal DB update for the Episode updated
        for db in self.get_db():
            db.execute(
                EpisodeRecord.__table__.update()
                .where(EpisodeRecord.id == self.id)
                .values(updated=self.updated)
            )
            db.commit()

    def delete_action(self, action_id: str) -> None:
        """Records an action to the episode."""
        self.actions = [action for action in self.actions if action.id != action_id]
        actionResults = ActionEvent.find(id=action_id)
        actionResults[0].delete()
        self.updated = time.time()
        self.save()

    def record(
        self,
        state: EnvState,
        action: V1Action,
        tool: V1ToolRef,
        prompt: Optional[Prompt | str | V1ChatEvent] = None,
        result: Optional[Any] = None,
        end_state: Optional[EnvState] = None,
        action_opts: Optional[List[ActionOpt]] = None,
        namespace: str = "default",
        metadata: Dict[str, Any] = {},
        owner_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        reviews: Optional[List[Review]] = None,
        reviewables: Optional[List[Reviewable]] = None,
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
            action_opts=action_opts,
            owner_id=owner_id,
            model=model,
            agent_id=agent_id,
            reviews=reviews,
            episode_id=self.id,
            reviewables=reviewables,
        )
        self.record_event(event)

        return event

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            for action in self.actions:
                action.episode_id = self.id
                action.save()
            record = self.to_record()
            db.merge(record)
            db.commit()
        print(
            f"episode {self.id} saved with actions: {[action.id for action in self.actions]}"
        )

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
    def from_record(
        cls,
        record: EpisodeRecord,
        action_recs: List[ActionRecord],
    ) -> "Episode":
        """Creates an episode instance from a database record."""
        episode = cls.__new__(cls)
        episode.id = record.id
        episode.tags = json.loads(str(record.tags))
        episode.labels = json.loads(str(record.labels))
        episode.created = record.created
        episode.updated = record.updated
        episode.owner_id = record.owner_id
        episode.device = record.device
        episode.device_type = record.device_type

        # hydrate each ActionEvent from the ActionRecord
        episode.actions = [ActionEvent.from_record(ar) for ar in action_recs]

        return episode

    @classmethod
    def find(cls, **kwargs) -> List["Episode"]:
        """
        Load episodes + their actions in one go.
        Returns a list of Episode instances.
        """
        for db in cls.get_db():
            # 1) pull only the episodes you want
            episode_subq = db.query(EpisodeRecord).filter_by(**kwargs).subquery()
            episode = aliased(EpisodeRecord, episode_subq)

            # 2) join their actions
            rows = (
                db.query(episode, ActionRecord)
                  .outerjoin(ActionRecord, ActionRecord.episode_id == episode.id)
                  .order_by(asc(episode.created), asc(ActionRecord.created))
                  .all()
            )

            # group action-records under each episode
            episodes: dict[str, dict] = {}
            for ep_rec, act_rec in rows:
                if ep_rec.id not in episodes:
                    episodes[ep_rec.id] = {"ep": ep_rec, "actions": []}
                if act_rec is not None:
                    episodes[ep_rec.id]["actions"].append(act_rec)

            # build Episode objects
            return [
                cls.from_record(info["ep"], info["actions"])
                for info in episodes.values()
            ]

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

    def delete_all_actions(self) -> None:
        """Deletes all actions associated with this episode from the database."""
        for db in self.get_db():
            # Retrieve all action records associated with this episode
            action_records = (
                db.query(ActionRecord).filter(ActionRecord.episode_id == self.id).all()
            )
            # Delete each action and its associated data
            for action_record in action_records:
                action = ActionEvent.from_record(action_record)
                action.delete()
            db.commit()
        # Clear the actions list in memory
        self.actions = []
        self.save()

    def fail_one(
        self,
        event_id: str,
        reviewer: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        correction: Optional[V1Action] = None,
    ) -> None:
        """Fail the given event."""
        for event in self.actions:
            if event.id == event_id:
                event.post_review(
                    reviewer=reviewer,
                    reviewer_type=reviewer_type,
                    reason=reason,
                    approved=False,
                    correction=correction,
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
        approve_hidden: bool = False,
    ) -> None:
        """Approve all actions in the episode."""
        for event in self.actions:
            if event.hidden and not approve_hidden:
                continue
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
        fail_hidden: bool = False,
    ) -> None:
        """Fail all actions in the episode."""
        for event in self.actions:
            if event.hidden and not fail_hidden:
                continue
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
        approve_hidden: bool = False,
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
            event = self.actions[i]
            if event.hidden and not approve_hidden:
                continue
            event.post_review(
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
        fail_hidden: bool = False,
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
            event = self.actions[i]
            if event.hidden and not fail_hidden:
                continue
            event.post_review(
                reviewer=reviewer,
                reviewer_type=reviewer_type,
                approved=False,
            )

        self.save()
