from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from mllm import Prompt

from skillpacks.server.models import (
    V1Episode,
    V1CreateActionEvent,
    V1Episodes,
    V1UserProfile,
)
from skillpacks.base import Episode, ActionEvent
from skillpacks.auth.transport import get_current_user

router = APIRouter()


@router.post("/v1/episodes", response_model=V1Episode)
async def create_episode(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)], data: V1Episode
):
    episode = Episode.from_v1(data)
    episode.owner_id = current_user.email
    episode.save()
    return episode.to_v1()


@router.get("/v1/episodes/{id}", response_model=V1Episode)
async def get_episode(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)], id: str
):
    episodes = Episode.find(id=id, owner_id=current_user.email)
    if not episodes:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episodes[0].to_v1()


@router.post("/v1/episodes/{id}/events", response_model=V1Episode)
async def record_event(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)],
    id: str,
    data: V1CreateActionEvent,
):
    episodes = Episode.find(id=id, owner_id=current_user.email)
    if not episodes:
        raise HTTPException(status_code=404, detail="Episode not found")
    episode = episodes[0]

    event = ActionEvent(
        prompt=Prompt.from_v1(data.prompt),
        action=data.action,
        tool=data.tool,
        result=data.result,
        namespace=data.namespace,
        metadata=data.metadata,
        approved=data.approved,
        flagged=data.flagged,
        owner_id=current_user.email,
    )
    event.save()

    episode.record_event(event)
    episode.save()
    return episode.to_v1()


@router.get("/v1/episodes", response_model=V1Episodes)
async def get_episodes(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)],
):
    episodes = Episode.find(owner_id=current_user.email)
    if not episodes:
        raise HTTPException(status_code=404, detail="Action event not found")
    return V1Episodes(episodes=[event.to_v1() for event in episodes])


@router.delete("/v1/episodes/{id}")
async def delete_episode(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)], id: str
):
    episodes = Episode.find(id=id, owner_id=current_user.email)
    if not episodes:
        raise HTTPException(status_code=404, detail="Episode not found")
    episode = episodes[0]
    episode.delete()
    return {"message": "Episode deleted successfully"}
