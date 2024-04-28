import time

from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB  # If using PostgreSQL

Base = declarative_base()


# def __init__(
#     self,
#     prompt: Prompt,
#     action: V1Action,
#     result: Any,
#     tool: V1ToolRef,
#     namespace: str = "default",
#     metadata: dict = {},


class ActionRecord(Base):
    __tablename__ = "actions"

    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=True)
    namespace = Column(String, default="default")
    prompt_id = Column(String)
    action = Column(Text)
    result = Column(Text)
    tool = Column(Text)
    metadata_ = Column(Text, default=dict)
    approved = Column(Boolean, default=False)
    flagged = Column(Boolean, default=False)
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
