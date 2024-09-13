from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from mllm import Prompt

from skillpacks.server.models import (
    V1ActionEvent,
    V1ActionEvents,
    V1CreateActionEvent,
    V1UserProfile,
)
from skillpacks.base import ActionEvent
from skillpacks.auth.transport import get_current_user
from skillpacks.review import Review


router = APIRouter()


@router.post("/v1/actions", response_model=V1ActionEvent)
async def create_action_event(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)],
    data: V1CreateActionEvent,
):
    event = ActionEvent(
        state=data.state,
        action=data.action,
        tool=data.tool,
        result=data.result,
        prompt=Prompt.from_v1(data.prompt) if data.prompt else None,
        namespace=data.namespace,
        metadata=data.metadata,
        reviews=[Review.from_v1(review) for review in data.reviews],
        flagged=data.flagged,
        owner_id=current_user.email,
    )
    event.save()
    return event.to_v1()


@router.get("/v1/actions/{id}", response_model=V1ActionEvent)
async def get_action_event(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)], id: str
):
    events = ActionEvent.find(id=id, owner_id=current_user.email)
    if not events:
        raise HTTPException(status_code=404, detail="Action event not found")
    return events[0].to_v1()


@router.get("/v1/actions", response_model=V1ActionEvent)
async def get_action_events(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)],
):
    events = ActionEvent.find(owner_id=current_user.email)
    if not events:
        raise HTTPException(status_code=404, detail="Action event not found")
    return V1ActionEvents(events=[event.to_v1() for event in events])


@router.delete("/v1/actions/{id}")
async def delete_action_event(
    current_user: Annotated[V1UserProfile, Depends(get_current_user)], id: str
):
    events = ActionEvent.find(id=id, owner_id=current_user.email)
    if not events:
        raise HTTPException(status_code=404, detail="Action event not found")
    event = events[0]
    event.delete()
    return {"message": "Action event deleted successfully"}
