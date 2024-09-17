import time

from sqlalchemy import Column, String, ForeignKey, Text, Boolean, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


action_reviews = Table(
    "action_reviews",
    Base.metadata,
    Column("action_id", String, ForeignKey("actions.id")),
    Column("review_id", String, ForeignKey("reviews.id")),
)


# Database Models
class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True)
    reviewer = Column(String, nullable=False)
    approved = Column(Boolean, nullable=False)
    reviewer_type = Column(String, default="human")
    reason = Column(Text, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    created = Column(Float, default=time.time)
    updated = Column(Float, nullable=True)
    parent_id = Column(String, ForeignKey("reviews.id"), nullable=True)


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

    flagged = Column(Boolean, default=False)
    model = Column(String, default=None)
    agent_id = Column(String, default=None)
    created = Column(Float, default=time.time)

    episode_id = Column(String, ForeignKey("episodes.id"), nullable=True)
    episode = relationship("EpisodeRecord", back_populates="actions")

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
    actions = relationship(
        "ActionRecord", order_by=ActionRecord.id, back_populates="episode"
    )

    actions = relationship(
        "ActionRecord",
        order_by=ActionRecord.id,
        back_populates="episode",
        cascade="all, delete-orphan",
    )
