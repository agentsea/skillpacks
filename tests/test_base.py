import pytest
from mllm import Prompt, RoleThread, RoleMessage
from skillpacks import Episode, ActionEvent, V1Action, EnvState
from toolfuse.models import V1ToolRef
from typing import List


def create_episode_with_events(num_events: int = 3) -> Episode:
    thread = RoleThread()
    thread.post(
        "user", "What action should I take?", images=["https://example.com/image.png"]
    )
    response = RoleMessage("assistant", "you should take this action...")
    prompt = Prompt(thread, response)

    episode = Episode()
    for i in range(num_events):
        episode.record(
            EnvState(images=[f"https://example.com/image{i}.png"]),
            V1Action(name=f"action_{i}", parameters={"param": f"value_{i}"}),
            V1ToolRef(module="test_module", type="TestType", version="0.1.0"),
            prompt=prompt.id,
        )
    event = ActionEvent(
        EnvState(images=[f"https://example.com/image99.png"]),
        V1Action(name=f"action_{i}", parameters={"param": f"value_99"}),
        V1ToolRef(module="test_module", type="TestType", version="0.1.0"),
        prompt=prompt,
    )
    episode.record_event(event)
    return episode


def test_all():
    thread = RoleThread()
    thread.post(
        "user",
        "What action should I take to open the browser?",
        images=[
            "https://storage.googleapis.com/guisurfer-assets/Screenshot%202024-05-03%20at%2010.24.32%20AM.png"
        ],
    )
    response = RoleMessage("assistant", "you should take this action...")
    prompt1 = Prompt(thread, response)

    episode = Episode()
    event1 = episode.record(
        EnvState(images=["https://my.img"]),
        V1Action(name="open_browser", parameters={"app": "chrome"}),
        V1ToolRef(module="agentdesk", type="Desktop", version="0.1.2"),
        prompt=prompt1.id,
    )

    prompt2 = Prompt(thread, response)
    event2 = episode.record(
        EnvState(images=["https://my.img"]),
        V1Action(name="open_browser", parameters={"app": "firefox"}),
        V1ToolRef(module="agentdesk", type="Desktop", version="0.1.3"),
        prompt=prompt2.id,
    )

    event1_found = episode.get_event(event1.id)
    assert event1_found.reviews == []

    episode.approve_one(
        event1.id, reviewer="tom@myspace.com", reviewer_type="human", reason="good"
    )

    event1_found = episode.get_event(event1.id)
    assert len(event1_found.reviews) == 1


def test_approve_all():
    episode = create_episode_with_events()
    episode.approve_all(reviewer="test@example.com", reviewer_type="human")

    for event in episode.actions:
        assert event.episode_id == episode.id
        assert len(event.reviews) == 1
        assert event.reviews[0].approved == True
        assert event.reviews[0].reviewer == "test@example.com"
        assert event.reviews[0].reviewer_type == "human"


def test_fail_all():
    episode = create_episode_with_events()
    episode.fail_all(reviewer="test@example.com", reviewer_type="human")

    for event in episode.actions:
        assert event.episode_id == episode.id
        assert len(event.reviews) == 1
        assert event.reviews[0].approved == False
        assert event.reviews[0].reviewer == "test@example.com"
        assert event.reviews[0].reviewer_type == "human"


def test_approve_prior():
    episode = create_episode_with_events(5)
    middle_event_id = episode.actions[2].id

    episode.approve_prior(
        middle_event_id, reviewer="test@example.com", reviewer_type="human"
    )

    for i, event in enumerate(episode.actions):
        if i <= 2:
            assert len(event.reviews) == 1
            assert event.reviews[0].approved == True
        else:
            assert len(event.reviews) == 0


def test_fail_prior():
    episode = create_episode_with_events(5)
    middle_event_id = episode.actions[2].id

    episode.fail_prior(
        middle_event_id, reviewer="test@example.com", reviewer_type="human"
    )

    for i, event in enumerate(episode.actions):
        if i <= 2:
            assert len(event.reviews) == 1
            assert event.reviews[0].approved == False
        else:
            assert len(event.reviews) == 0
