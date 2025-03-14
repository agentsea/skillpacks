import json
import time
from typing import List, Optional, Type

import shortuuid
from pydantic import BaseModel

from skillpacks.db.conn import WithDB
from skillpacks.db.models import ReviewRecord
from skillpacks.server.models import ReviewerType, V1Review
from enum import Enum

class Resource(Enum):
    TASK = "task"
    Action = "action"

class Review(WithDB):
    """A review of an agent action or task"""

    def __init__(
        self,
        reviewer: str,
        approved: bool,
        resource_type: str,
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
        self.approved = approved
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

    def to_v1(self) -> V1Review:
        correction = self.correction
        # Check if correction is a string that can be parsed as JSON
        if isinstance(self.correction, str):
            try:
                parsed_correction = json.loads(self.correction)
                if isinstance(parsed_correction, dict):
                    correction = parsed_correction
            except json.JSONDecodeError:
                # If parsing fails, retain the original string
                pass

        return V1Review(
            id=self.id,
            reviewer=self.reviewer,
            approved=self.approved,
            reviewer_type=self.reviewer_type,
            reason=self.reason,
            parent_id=self.parent_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            with_resources=self.with_resources,
            correction=correction,
            correction_schema=self.correction_schema,
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_v1(cls, v1: V1Review) -> "Review":
        review = cls.__new__(cls)
        review.id = v1.id
        review.reviewer = v1.reviewer
        review.approved = v1.approved
        review.reviewer_type = v1.reviewer_type
        review.reason = v1.reason
        review.parent_id = v1.parent_id
        review.resource_type = v1.resource_type
        review.resource_id = v1.resource_id
        review.with_resources = v1.with_resources
        review.correction = v1.correction
        review.correction_schema = v1.correction_schema
        review.created = v1.created
        review.updated = v1.updated
        return review

    def save(self) -> None:
        """Saves the review to the database."""
        for db in self.get_db():
            record = self.to_record()
            db.merge(record)
            db.commit()

    def delete(self) -> None:
        """Deletes the review from the database."""
        for db in self.get_db():
            record = db.query(ReviewRecord).filter(ReviewRecord.id == self.id).first()
            if record:
                db.delete(record)
                db.commit()
            else:
                raise ValueError("Review not found")

    def to_record(self) -> ReviewRecord:
        """Converts the review to a database record."""

        correction_str = None
        if self.correction is not None:
            if isinstance(self.correction, str):
                correction_str = self.correction
            else:
                # Attempt to JSON-serialize
                correction_str = json.dumps(self.correction)

        return ReviewRecord(
            id=self.id,
            approved=self.approved,
            reviewer=self.reviewer,
            reviewer_type=self.reviewer_type,
            reason=self.reason,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            with_resources=json.dumps(self.with_resources),
            parent_id=self.parent_id,
            correction=correction_str,
            correction_schema=json.dumps(self.correction_schema)
            if self.correction_schema
            else None,
            created=self.created,
            updated=self.updated,
        )

    @classmethod
    def from_record(cls, record: ReviewRecord) -> "Review":
        """Creates a review instance from a database record."""
        review = cls.__new__(cls)
        review.id = record.id
        review.reviewer = record.reviewer
        review.reviewer_type = record.reviewer_type
        review.approved = record.approved
        review.reason = record.reason
        review.parent_id = record.parent_id
        review.resource_type = record.resource_type
        review.resource_id = record.resource_id
        review.with_resources = (
            json.loads(record.with_resources) if record.with_resources else []  # type: ignore
        )
        # Attempt to parse correction as JSON
        review.correction = None
        if record.correction is not None:
            try:
                review.correction = json.loads(record.correction) # type: ignore
            except (ValueError, TypeError):
                # If it's not valid JSON, just store the raw string
                review.correction = record.correction
        review.correction_schema = (
            json.loads(record.correction_schema) if record.correction_schema else None # type: ignore
        )
        review.created = record.created
        review.updated = record.updated
        return review

    @classmethod
    def find(cls, **kwargs) -> List["Review"]:
        """Finds reviews in the database based on provided filters."""
        for db in cls.get_db():
            records = db.query(ReviewRecord).filter_by(**kwargs).all()
            return [cls.from_record(record) for record in records]
        raise ValueError("No database session available")

    @classmethod
    def find_many(cls,
        resource_ids: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        review_ids: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None,
        approved: Optional[bool] = None,
    ) -> List["Review"]:
        """Finds review requirements in the database based on provided filters."""
        # TODO require a filter?
        for db in cls.get_db():
            query = db.query(ReviewRecord)
            if resource_type:
                query = query.filter(ReviewRecord.resource_type == resource_type)
            if resource_ids:
                query = query.filter(ReviewRecord.resource_id.in_(resource_ids))
            if review_ids:
                query = query.filter(ReviewRecord.id.in_(review_ids))
            if reviewers:
                query = query.filter(ReviewRecord.reviewer.in_(reviewers))
            if approved is not None:
                query = query.filter(ReviewRecord.approved == approved)
            records = db.query(ReviewRecord).order_by(ReviewRecord.created.desc()).all()
            return [cls.from_record(record) for record in records]
        raise ValueError("No database session available")