import time
from typing import List, Optional
from mllm import Prompt
import shortuuid
from skillpacks.rating import Rating
from skillpacks.db.conn import WithDB
from skillpacks.db.models import ActionOptRecord, RatingRecord
from .server.models import (
    V1Action,
    V1ActionOpt,
)

class ActionOpt(WithDB):
    """A option to an agent action or task"""

    def __init__(
        self,
        action: V1Action,
        prompt: Optional[Prompt] = None,
        ratings: Optional[List[Rating]] = None,
        action_id: Optional[str] = None,
        created: Optional[float] = None,
        updated: Optional[float] = None,
    ) -> None:
        self.id = str(shortuuid.uuid())
        self.prompt = prompt
        self.action = action
        self.ratings = ratings or []
        self.action_id = action_id  # Link to the ActionRecord's ID
        self.created = created or time.time()
        self.updated = updated or time.time()

    def to_v1(self) -> V1ActionOpt:
        return V1ActionOpt(
            id=self.id,
            prompt=self.prompt.to_v1() if self.prompt else None,
            action=self.action,
            ratings=[rating.to_v1() for rating in self.ratings] if self.ratings else [],
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
        actionOpt.ratings = (
                    [Rating.from_v1(rating_v1) for rating_v1 in v1.ratings]
                    if v1.ratings
                    else []
                )
        actionOpt.created = v1.created
        actionOpt.updated = v1.updated
        return actionOpt

    def save(self) -> None:
        """Saves the action opt to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

        # After committing the action opt, associate the ratings
            if self.ratings:
                for rating in self.ratings:
                    if not rating.resource_id:
                        rating.resource_id = self.id
                    rating.save()
                # Refresh the record to get the latest state
                record = (
                    db.query(ActionOptRecord).filter(ActionOptRecord.id == self.id).first()
                )

                if not record:
                    raise ValueError(f"ActionRecord with id {self.id} not found")
                # Associate the ratings with the action via the association table
                record.ratings = [
                    db.query(RatingRecord).filter_by(id=rating.id).first()
                    for rating in self.ratings
                ]
            db.commit()


    def delete(self) -> None:
        """Deletes the Action Opt from the database."""
        for db in self.get_db():
            record = db.query(ActionOptRecord).filter(ActionOptRecord.id == self.id).first()
            if record:
                db.delete(record)
                db.commit()
            else:
                raise ValueError("Rating not found")

    def to_record(self) -> ActionOptRecord:
        """Converts the Action Opt to a database record."""
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
        """Creates a Action Opt instance from a database record."""
        actionOpt = cls.__new__(cls)
        actionOpt.id = record.id
        ratings = [
            Rating.from_record(rating_record) for rating_record in record.ratings
        ]
        actionOpt.action = V1Action.model_validate_json(record.action)  # type: ignore
        actionOpt.prompt = (
                    Prompt.find(id=record.prompt_id)[0] if record.prompt_id else None  # type: ignore
                )  # Replace Prompt with your actual class
        actionOpt.ratings = ratings
        actionOpt.action_id = record.action_id
        actionOpt.created = record.created
        actionOpt.updated = record.updated
        return actionOpt

    @classmethod
    def find(cls, **kwargs) -> List["ActionOpt"]:
        """Finds Action Opts in the database based on provided filters."""
        for db in cls.get_db():
            records = db.query(ActionOptRecord).filter_by(**kwargs).all()
            return [cls.from_record(record) for record in records]
        raise ValueError("No database session available")
