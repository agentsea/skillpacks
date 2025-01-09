import time

from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

action_reviews = Table(
    "action_reviews",
    Base.metadata,
    Column("action_id", String, ForeignKey("actions.id")),
    Column("review_id", String, ForeignKey("reviews.id")),
)

action_opt_ratings = Table(
    "action_opt_ratings",
    Base.metadata,
    Column("action_id", String, ForeignKey("action_opts.id")),
    Column("rating_id", String, ForeignKey("ratings.id")),
)

reviewable_reviews = Table(
    "reviewable_reviews",
    Base.metadata,
    Column("reviewable_id", String, ForeignKey("reviewables.id")),
    Column("review_id", String, ForeignKey("reviews.id")),
)

action_reviewables = Table(
    "action_reviewables",
    Base.metadata,
    Column("action_id", String, ForeignKey("actions.id")),
    Column("reviewable_id", String, ForeignKey("reviewables.id", ondelete="cascade")),
)


# Database Models
class ReviewableRecord(Base):
    __tablename__ = "reviewables"

    id = Column(String, primary_key=True)
    type = Column(String)
    reviewable = Column(Text)
    created = Column(Float, default=time.time)
    updated = Column(Float, default=time.time)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    reviews = relationship(
        "ReviewRecord",
        secondary=reviewable_reviews,  # TODO find other way than association table
        lazy="select",  # or 'select', depending on your preference
        cascade="all, delete-orphan"
    )


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)
    reviewer = Column(String, nullable=False)
    approved = Column(Boolean, nullable=False)
    reviewer_type = Column(String, default="human")
    reason = Column(Text, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    with_resources = Column(String, nullable=True)
    correction = Column(String, nullable=True)
    correction_schema = Column(String, nullable=True)
    created = Column(Float, default=time.time)
    updated = Column(Float, nullable=True)
    parent_id = Column(String, ForeignKey("reviews.id"), nullable=True)

class RatingRecord(Base):
    __tablename__ = "ratings"

    id = Column(String, primary_key=True)
    reviewer = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    rating_upper_bound = Column(Integer, nullable=False)
    rating_lower_bound = Column(Integer, nullable=False)
    reviewer_type = Column(String, default="human")
    reason = Column(Text, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    with_resources = Column(String, nullable=True)
    correction = Column(String, nullable=True)
    correction_schema = Column(String, nullable=True)
    created = Column(Float, default=time.time)
    updated = Column(Float, nullable=True)
    parent_id = Column(String, ForeignKey("ratings.id"), nullable=True)

class ActionOptRecord(Base):
    __tablename__ = "action_opts"
    id = Column(String, primary_key=True)
    action = Column(Text)
    prompt_id = Column(String, nullable=True)
    created = Column(Float, default=time.time)
    updated = Column(Float, nullable=True)
    ratings = relationship(
        "RatingRecord",
        secondary=action_opt_ratings,
        lazy="dynamic",  # or 'select', depending on your preference
        # cascade="all, delete", try this later
    )
    action_id = Column(String, ForeignKey("actions.id"))

    # Many-to-one relationship with ActionRecord
    action_record = relationship("ActionRecord", back_populates="action_opts")

class ActionRecord(Base):
    __tablename__ = "actions"

    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=True)
    namespace = Column(String, default="default")
    prompt_id = Column(String, nullable=True)
    state = Column(Text)
    action = Column(Text)
    result = Column(Text)
    end_state = Column(Text, nullable=True)
    tool = Column(Text)
    metadata_ = Column(Text, default=dict)
    event_order = Column(Integer, nullable=True)
    flagged = Column(Boolean, default=False)
    model = Column(String, default=None)
    agent_id = Column(String, default=None)
    created = Column(Float, default=time.time)
    started = Column(Float, default=time.time)
    ended = Column(Float, default=time.time)
    hidden = Column(Boolean, default=False)
    # One-to-many relationship with ActionOptRecord
    action_opts = relationship("ActionOptRecord", back_populates="action_record")
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=True)
    episode = relationship("EpisodeRecord", back_populates="actions")
    reviewables = relationship(
        "ReviewableRecord",
        secondary=action_reviewables,
        lazy="select",
        # TODO test if we can cascade action deletions to reviewables through the secondary table. If so this will yield a performance improvement
    )
    reviews = relationship(
        "ReviewRecord",
        secondary=action_reviews,
        lazy="dynamic",  # or 'select', depending on your preference
    )


class EpisodeRecord(Base):
    __tablename__ = "episodes"

    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=True)
    tags = Column(Text, default=list)
    labels = Column(Text, default=list)
    created = Column(Float, default=time.time)
    updated = Column(Float, default=time.time)
    device = Column(String, nullable=True)  # Added device column
    device_type = Column(String, nullable=True)  # Added device_type column

    actions = relationship(
        "ActionRecord",
        order_by=ActionRecord.created,
        back_populates="episode",
        cascade="all, delete-orphan",
    )
