import json
import time
from typing import List, Optional, Type
from mllm import Prompt
import shortuuid
from pydantic import BaseModel
from .review import Review
from skillpacks.db.conn import WithDB
from skillpacks.db.models import ActionOptRecord, ReviewRecord
from .server.models import (
    V1Action,
    V1ActionOpt,
)

class ActionOpt(WithDB):
    """A review of an agent action or task"""

    def __init__(
        self,
        action: V1Action,
        prompt: Optional[Prompt] = None,
        reviews: Optional[List[Review]] = None,
        action_id: Optional[str] = None,
        created: Optional[float] = None,
        updated: Optional[float] = None,
    ) -> None:
        self.id = str(shortuuid.uuid())
        self.prompt = prompt
        self.action = action
        self.reviews = reviews or []
        self.action_id = action_id  # Link to the ActionRecord's ID
        self.created = created or time.time()
        self.updated = updated or time.time()

    def to_v1(self) -> V1ActionOpt:
        return V1ActionOpt(
            id=self.id,
            prompt=self.prompt.to_v1() if self.prompt else None,
            action=self.action,
            reviews=[review.to_v1() for review in self.reviews] if self.reviews else [],
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_v1(cls, v1: V1ActionOpt) -> "ActionOpt":
        actionOpt = cls.__new__(cls)
        actionOpt.id = v1.id
        actionOpt.action = v1.action
        actionOpt.prompt = (
                    Prompt.from_v1(v1.prompt) if v1.prompt else None
                )  # Replace Prompt with your actual class
        actionOpt.reviews = (
                    [Review.from_v1(review_v1) for review_v1 in v1.reviews]
                    if v1.reviews
                    else []
                )
        actionOpt.created = v1.created
        actionOpt.updated = v1.updated
        return actionOpt

    def save(self) -> None:
        """Saves the review to the database."""
        for db in self.get_db():
            record = self.to_record()
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
                    db.query(ActionOptRecord).filter(ActionOptRecord.id == self.id).first()
                )

                if not record:
                    raise ValueError(f"ActionRecord with id {self.id} not found")
                # Associate the reviews with the action via the association table
                record.reviews = [
                    db.query(ReviewRecord).filter_by(id=review.id).first()
                    for review in self.reviews
                ]
            db.commit()


    def delete(self) -> None:
        """Deletes the review from the database."""
        for db in self.get_db():
            record = db.query(ActionOptRecord).filter(ActionOptRecord.id == self.id).first()
            if record:
                db.delete(record)
                db.commit()
            else:
                raise ValueError("Review not found")

    def to_record(self) -> ActionOptRecord:
        """Converts the review to a database record."""
        prompt_id = None
        if self.prompt:
            prompt_id = self.prompt.id

        return ActionOptRecord(
            id=self.id,
            prompt_id=prompt_id,
            action=self.action.model_dump_json(),
            action_id=self.action_id,
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_record(cls, record: ActionOptRecord) -> "ActionOpt":
        """Creates a review instance from a database record."""
        actionOpt = cls.__new__(cls)
        actionOpt.id = record.id
        reviews = [
            Review.from_record(review_record) for review_record in record.reviews
        ]
        actionOpt.action = V1Action.model_validate_json(record.action)  # type: ignore
        actionOpt.prompt = (
                    Prompt.find(id=record.prompt_id)[0] if record.prompt_id else None  # type: ignore
                )  # Replace Prompt with your actual class
        actionOpt.reviews = reviews
        actionOpt.action_id = record.action_id
        actionOpt.created = record.created
        actionOpt.updated = record.updated
        return actionOpt

    @classmethod
    def find(cls, **kwargs) -> List["ActionOpt"]:
        """Finds reviews in the database based on provided filters."""
        for db in cls.get_db():
            records = db.query(ActionOptRecord).filter_by(**kwargs).all()
            return [cls.from_record(record) for record in records]
        raise ValueError("No database session available")
