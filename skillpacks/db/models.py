import time

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB  # If using PostgreSQL

Base = declarative_base()


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
    approved = Column(Boolean, nullable=True)
    flagged = Column(Boolean, default=False)
    model = Column(String, default=None)
    agent_id = Column(String, default=None)
    created = Column(Float, default=time.time)

    episode_id = Column(String, ForeignKey("episodes.id"), nullable=True)
    episode = relationship("EpisodeRecord", back_populates="actions")


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
