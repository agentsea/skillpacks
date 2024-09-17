from typing import Optional, List
import shortuuid
import time

from skillpacks.db.models import ReviewRecord
from skillpacks.db.conn import WithDB
from skillpacks.server.models import ReviewerType, V1Review


class Review(WithDB):
    """A review of an agent action or task"""

    def __init__(
        self,
        reviewer: str,
        approved: bool,
        resource_type: str,
        resource_id: str,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        parent_id: Optional[str] = None,
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
        self.created = created or time.time()
        self.updated = updated

    def to_v1(self) -> V1Review:
        return V1Review(
            id=self.id,
            reviewer=self.reviewer,
            approved=self.approved,
            reviewer_type=self.reviewer_type,
            reason=self.reason,
            parent_id=self.parent_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
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
        return ReviewRecord(
            id=self.id,
            approved=self.approved,
            reviewer=self.reviewer,
            reviewer_type=self.reviewer_type,
            reason=self.reason,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            parent_id=self.parent_id,
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
