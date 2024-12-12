import json
import time
from typing import List, Optional, Type

import shortuuid
from pydantic import BaseModel

from skillpacks.db.conn import WithDB
from skillpacks.db.models import RatingRecord
from skillpacks.server.models import ReviewerType, V1Rating


class Rating(WithDB):
    """A numerical rating of an agent action or task"""

    def __init__(
        self,
        reviewer: str,
        rating: int,
        resource_type: str,
        rating_upper_bound: int = 5,
        rating_lower_bound: int = 1,
        resource_id: Optional[str] = None,
        with_resources: Optional[List[str]] = [],
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        parent_id: Optional[str] = None,
        correction: Optional[str] = None,
        correction_schema: Optional[Type[BaseModel]] = None,
        created: Optional[float] = None,
        updated: Optional[float] = None,
    ) -> None:
        self.id = str(shortuuid.uuid())
        self.reviewer = reviewer
        self.rating = rating
        if rating > rating_upper_bound or rating < rating_lower_bound:
            raise ValueError(f"Rating: {rating} not compatible with rating_upperbound {rating_upper_bound} and rating_lower_bound {rating_lower_bound}")
        self.rating_upper_bound = rating_upper_bound
        self.rating_lower_bound = rating_lower_bound
        self.reviewer_type = reviewer_type
        self.reason = reason
        self.parent_id = parent_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.with_resources = with_resources
        self.correction = correction
        self.correction_schema = (
            correction_schema.model_json_schema() if correction_schema else None
        )
        self.created = created or time.time()
        self.updated = updated

    def to_v1(self) -> V1Rating:
        return V1Rating(
            id=self.id,
            reviewer=self.reviewer,
            rating=self.rating,
            rating_upper_bound=self.rating_upper_bound,
            rating_lower_bound=self.rating_lower_bound,
            reviewer_type=self.reviewer_type,
            reason=self.reason,
            parent_id=self.parent_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            with_resources=self.with_resources,
            correction=self.correction,
            correction_schema=self.correction_schema,
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_v1(cls, v1: V1Rating) -> "Rating":
        rating = cls.__new__(cls)
        rating.id = v1.id
        rating.reviewer = v1.reviewer
        rating.rating = v1.rating
        rating.rating_upper_bound=v1.rating_upper_bound
        rating.rating_lower_bound=v1.rating_lower_bound
        rating.reviewer_type = v1.reviewer_type
        rating.reason = v1.reason
        rating.parent_id = v1.parent_id
        rating.resource_type = v1.resource_type
        rating.resource_id = v1.resource_id
        rating.with_resources = v1.with_resources
        rating.correction = v1.correction
        rating.correction_schema = v1.correction_schema
        rating.created = v1.created
        rating.updated = v1.updated
        return rating

    def save(self) -> None:
        """Saves the rating to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

    def delete(self) -> None:
        """Deletes the rating from the database."""
        for db in self.get_db():
            record = db.query(RatingRecord).filter(RatingRecord.id == self.id).first()
            if record:
                db.delete(record)
                db.commit()
            else:
                raise ValueError("Rating not found")

    def to_record(self) -> RatingRecord:
        """Converts the rating to a database record."""
        return RatingRecord(
            id=self.id,
            rating=self.rating,
            reviewer=self.reviewer,
            reviewer_type=self.reviewer_type,
            rating_upper_bound=self.rating_upper_bound,
            rating_lower_bound=self.rating_lower_bound,
            reason=self.reason,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            with_resources=json.dumps(self.with_resources),
            parent_id=self.parent_id,
            correction=self.correction,
            correction_schema=json.dumps(self.correction_schema)
            if self.correction_schema
            else None,
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_record(cls, record: RatingRecord) -> "Rating":
        """Creates a rating instance from a database record."""
        rating = cls.__new__(cls)
        rating.id = record.id
        rating.reviewer = record.reviewer
        rating.reviewer_type = record.reviewer_type
        rating.rating = record.rating
        rating.rating_upper_bound=record.rating_upper_bound,
        rating.rating_lower_bound=record.rating_lower_bound,
        rating.reason = record.reason
        rating.parent_id = record.parent_id
        rating.resource_type = record.resource_type
        rating.resource_id = record.resource_id
        rating.with_resources = (
            json.loads(record.with_resources) if record.with_resources else []  # type: ignore
        )
        rating.correction = record.correction
        rating.correction_schema = (
            json.loads(record.correction_schema) if record.correction_schema else None
        )
        rating.created = record.created
        rating.updated = record.updated
        return rating

    @classmethod
    def find(cls, **kwargs) -> List["Rating"]:
        """Finds ratings in the database based on provided filters."""
        for db in cls.get_db():
            records = db.query(RatingRecord).filter_by(**kwargs).all()
            return [cls.from_record(record) for record in records]
        raise ValueError("No database session available")
