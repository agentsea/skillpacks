from typing import TypeVar, Optional, Generic, Type, Dict, List
from abc import ABC, abstractmethod
import shortuuid
import time
import json

from pydantic import BaseModel
from PIL import Image

from skillpacks.db.models import ReviewRecord, ReviewableRecord
from skillpacks.db.conn import WithDB
from skillpacks.server.models import (
    ReviewerType,
    V1BoundingBox,
    V1BoundingBoxReviewable,
    V1Reviewable,
)
from .review import Review
from .img import convert_images

ReviewableModel = TypeVar(
    "ReviewableModel", bound="BaseModel"
)  # this means the model of the reivewable needs to be valid BaseModel AKA V1BoundingBoxReviewable
ReviewableType = TypeVar(
    "ReviewableType", bound="Reviewable"
)  # means needs to be a valid reviewable


class Reviewable(Generic[ReviewableModel], ABC, WithDB):
    """A reviewable, a thing that needs review (usually human) that isn't an action or task, EX. BoundingBox or Demonstration"""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        reviews: List[Review] = [],
        created: Optional[float] = None,
        updated: Optional[float] = None,
    ) -> None:
        self.id = shortuuid.uuid()
        self.created = created or time.time()
        self.updated = updated
        self.reviews = reviews or []
        self.resource_type = resource_type
        self.resource_id = resource_id

    @classmethod
    @abstractmethod
    def v1_type(cls) -> Type[ReviewableModel]:
        pass

    @abstractmethod
    def to_v1(cls) -> ReviewableModel:
        pass

    @abstractmethod
    def post_review(cls) -> None:
        pass

    @classmethod
    @abstractmethod
    def from_v1(cls, v1: ReviewableModel) -> ReviewableType:
        pass

    def to_v1Reviewable(self) -> V1Reviewable:
        return V1Reviewable(
            type=self.__class__.__name__,
            id=self.id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            reviewable=self.to_v1().model_dump(),
            reviews=[review.to_v1() for review in self.reviews] if self.reviews else [],
            created=self.created,
        )

    def to_record(self) -> ReviewableRecord:
        """Converts the instance to a database record."""

        return ReviewableRecord(
            id=self.id,
            type=self.__class__.__name__,
            reviewable=self.to_v1().model_dump_json(),
            created=self.created,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            # reviews are associated via the relationship, not stored directly, For more info look in the save function
        )

    @classmethod  # this is dependent on the type already being determined and using the correct type from the type Map
    def from_record(cls, record: ReviewableRecord) -> ReviewableType:
        # Deserialize the reviewable JSON to a ReviewableModel (like V1BoundingBoxReviewable)
        reviewable_model = cls.v1_type().model_validate_json(str(record.reviewable))

        # Use the from_v1 method to create the specific ReviewableType (like BoundingBoxReviewable)
        instance = cls.from_v1(reviewable_model)

        # Set additional fields from the record
        instance.id = record.id
        instance.reviews = [
            Review.from_record(review_record) for review_record in record.reviews
        ]
        instance.created = record.created
        instance.resource_type = record.resource_type
        instance.resource_id = record.resource_id

        return instance

    def save(self) -> None:
        """Saves the instance to the database."""
        for db in self.get_db():
            db.merge(self.to_record())
            db.commit()
            # After committing the reviewable, associate the reviews
            if self.reviews:
                for review in self.reviews:
                    if not review.resource_id:
                        review.resource_id = self.id
                    review.save()
                # Refresh the record to get the latest state
                record = (
                    db.query(ReviewableRecord)
                    .filter(ReviewableRecord.id == self.id)
                    .first()
                )

                if not record:
                    raise ValueError(f"ActionRecord with id {self.id} not found")
                # Associate the reviews with the action via the association table
                record.reviews = [
                    db.query(ReviewRecord).filter_by(id=review.id).first()
                    for review in self.reviews
                ]
                db.commit()

    @classmethod
    def _get_reviewable_class_by_type(
        cls, reviewable_type: str
    ) -> Optional[Type["Reviewable"]]:
        """Return the appropriate flag class based on the flag type."""
        return type_map.get(reviewable_type)

    @classmethod
    def find(cls, **kwargs) -> List[ReviewableType]:
        for db in cls.get_db():
            records = (
                db.query(ReviewableRecord)
                .filter_by(**kwargs)
                .order_by(ReviewableRecord.created.desc())
                .all()
            )
            reviewables = []
            for record in records:
                # Dynamically determine the correct class for the reviewable type
                reviewable_class = cls._get_reviewable_class_by_type(str(record.type))
                if reviewable_class:
                    record_instance = reviewable_class.from_record(record)
                    reviewables.append(record_instance)
                else:
                    raise Exception(
                        f"Class for type {record.type} not found, Record: ", record
                    )

            return reviewables
        return []

    @classmethod
    def find_v1(cls, **kwargs) -> List[V1Reviewable]:
        for db in cls.get_db():
            records = (
                db.query(ReviewableRecord)
                .filter_by(**kwargs)
                .order_by(ReviewableRecord.created.desc())
                .all()
            )

            return [
                V1Reviewable(
                    type=str(record.type),
                    id=str(record.id),
                    resource_type=str(record.resource_type),
                    resource_id=str(record.resource_id),
                    reviewable=json.loads(str(record.reviewable)),
                    reviews=[review.to_v1() for review in record.reviews]
                    if record.reviews
                    else [],
                    created=record.created,  # type: ignore
                )
                for record in records
            ]
        return []

    def _save_review(
        self,
        reviewer: str,
        approved: bool,
        reviewer_type: str = ReviewerType.HUMAN.value,
        reason: Optional[str] = None,
        parent_id: Optional[str] = None,
        correction: Optional[BaseModel] = None,
        correction_schema: Optional[
            Type[BaseModel]
        ] = None,  # This is a type, not an instance
    ) -> None:
        review = Review(
            reviewer=reviewer,
            approved=approved,
            reviewer_type=reviewer_type,
            reason=reason,
            parent_id=parent_id,
            resource_type="reviewable",
            resource_id=self.id,
            correction=correction.model_dump_json() if correction else None,
            correction_schema=correction_schema,
        )

        self.reviews.append(review)
        self.save()


class BoundingBoxReviewable(Reviewable[V1BoundingBoxReviewable]):
    """Bounding box reviewable"""

    def __init__(
        self,
        img: str | Image.Image,
        target: str,
        bbox: V1BoundingBox,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs,  # Catch any additional keyword arguments for parent class
    ):
        super().__init__(**kwargs)
        self.img = convert_images([img])[0]
        self.target = target
        self.bbox = bbox
        self.metadata = metadata

    @classmethod
    def v1_type(cls) -> Type[V1BoundingBoxReviewable]:
        return V1BoundingBoxReviewable

    def to_v1(self) -> V1BoundingBoxReviewable:
        return V1BoundingBoxReviewable(
            img=self.img,
            target=self.target,
            bbox=self.bbox,
        )

    def post_review(
        self,
        reviewer: str,
        approved: bool,
        reason: Optional[str] = None,
        reviewer_type: str = ReviewerType.HUMAN.value,
        parent_id: Optional[str] = None,
        correction: Optional[V1BoundingBox] = None,
    ) -> None:
        self._save_review(
            approved=approved,
            reason=reason,
            reviewer=reviewer,
            reviewer_type=reviewer_type,
            parent_id=parent_id,
            correction=correction,
            correction_schema=V1BoundingBox,  # Pass the class type
        )

    @classmethod
    def from_v1(cls, v1: V1BoundingBoxReviewable) -> "BoundingBoxReviewable":
        out = cls.__new__(cls)
        out.img = v1.img
        out.target = v1.target
        out.bbox = v1.bbox
        return out


type_map = {
    "BoundingBoxReviewable": BoundingBoxReviewable,
    # "OtherFlagType": OtherFlagType,  # Map other flag types here
    # Add more mappings as needed
}
