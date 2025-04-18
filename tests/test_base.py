import json
import time
from typing import List

import pytest
from mllm import Prompt, RoleMessage, RoleThread
from toolfuse.models import V1ToolRef

from skillpacks import ActionEvent, EnvState, Episode, V1Action
from skillpacks.action_opts import ActionOpt
from skillpacks.chat import ChatRequest, ChatResponse, Choice, MessageItem, V1ChatEvent
from skillpacks.chat import Prompt as OrignPrompt
from skillpacks.rating import Rating
from skillpacks.server.models import V1ActionEvent


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
        V1Action(name=f"action_{i}", parameters={"param": f"value_99"}),  # type: ignore
        V1ToolRef(module="test_module", type="TestType", version="0.1.0"),
        prompt=prompt,
    )
    episode.record_event(event)
    return episode


def create_episode_with_actions(num_actions: int = 3) -> Episode:
    """
    Helper function to create an episode with a specified number of actions.
    """
    thread = RoleThread()
    thread.post(
        "user", "What action should I take?", images=["https://example.com/image.png"]
    )
    response = RoleMessage("assistant", "You should take this action...")
    prompt = Prompt(thread, response)

    episode = Episode()
    for i in range(num_actions):
        episode.record(
            EnvState(images=[f"https://example.com/image{i}.png"]),
            V1Action(name=f"action_{i}", parameters={"param": f"value_{i}"}),
            V1ToolRef(module="test_module", type="TestType", version="0.1.0"),
            prompt=prompt.id,
        )
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

    prompt2 = V1ChatEvent(
        request=ChatRequest(
            prompt=OrignPrompt(
                messages=[
                    MessageItem(
                        role="user",
                        content="What action should I take to open the browser?",
                    )
                ]
            )
        ),
        response=ChatResponse(
            request_id="request_id",
            choices=[Choice(index=0, text="you should take this action...")],
        ),
    )
    event2 = episode.record(
        EnvState(images=["https://my.img"]),
        V1Action(name="open_browser", parameters={"app": "firefox"}),
        V1ToolRef(module="agentdesk", type="Desktop", version="0.1.3"),
        prompt=prompt2,
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


def test_from_v1_and_save():
    # Create a sample V1ActionEvent JSON
    v1_action_event_data = {
        "id": "action-event-001",
        "state": {
            "images": ["https://example.com/image1.png"],
            "coordinates": [10, 20],
            "text": "Sample environment state",
        },
        "action": {
            "name": "click_button",
            "parameters": {"button": "submit"},
        },
        "result": {"success": True},
        "end_state": {
            "images": ["https://example.com/image2.png"],
            "text": "Post-action environment state",
        },
        "tool": {
            "module": "test_module",
            "type": "TestTool",
            "version": "0.1.0",
        },
        "namespace": "default",
        "reviews": [],
        "reviewables": [],
        "flagged": False,
        "model": None,
        "action_opts": None,
        "agent_id": "agent-123",
        "created": time.time(),
        "ended": time.time(),
        "started": time.time(),
        "metadata": {},
        "episode_id": "episode-001",
        "hidden": False,
    }

    # Convert the dictionary to a V1ActionEvent model
    v1_action_event = V1ActionEvent(**v1_action_event_data)

    # Use from_v1 method to create an ActionEvent instance
    action_event = ActionEvent.from_v1(v1_action_event)

    # Save the action event to the database (mocked DB for the test)
    action_event.save()
    found_events = ActionEvent.find(id=action_event.id)
    assert len(found_events) > 0, "Failed to retrieve the action event using find."

    # Get the first result from the find method
    found_event = found_events[0]

    # Convert the fetched ActionEvent instance back to JSON using to_v1 and model_dump_json
    found_v1_action_event = found_event.to_v1()
    assert found_v1_action_event == action_event.to_v1()


def test_delete_all_actions():
    # Create an episode with some events
    episode = create_episode_with_events(num_events=3)
    initial_action_count = len(episode.actions)
    assert (
        initial_action_count == 4
    )  # 3 events + 1 extra event in create_episode_with_events
    episode.approve_all(reviewer="test@example.com", reviewer_type="human")
    # print([action for action in episode.to_v1().actions])
    # Store action IDs for verification after deletion
    action_ids = [action.id for action in episode.actions]
    # Check that the actions are in the database
    for action_id in action_ids:
        found_actions = ActionEvent.find(id=action_id)
        print([vars(action) for action in found_actions])
    # Delete all actions from the episode
    episode.delete_all_actions()

    # Assert that the in-memory actions list is empty
    assert len(episode.actions) == 0, "Episode actions list was not cleared"

    # Check that the actions are deleted from the database
    for action_id in action_ids:
        found_actions = ActionEvent.find(id=action_id)
        assert (
            len(found_actions) == 0
        ), f"Action {action_id} was not deleted from the database"


def test_delete_all_actions_with_reviews_and_annotations():
    # Create an episode with events
    episode = create_episode_with_events(num_events=3)
    initial_action_count = len(episode.actions)
    assert (
        initial_action_count == 4
    )  # 3 events + 1 extra event in create_episode_with_events

    # Add reviews from multiple reviewers to each action
    for action in episode.actions:
        action.post_review(
            reviewer="user1@example.com",
            approved=True,
            reviewer_type="user",
            reason="Looks good",
        )
        action.post_review(
            reviewer="user2@example.com",
            approved=False,
            reviewer_type="user",
            reason="Needs improvement",
        )

        # Add annotations to each action
        action.post_reviewable(
            type="AnnotationReviewable",
            key="annotation_key",
            value="annotation_value",
            annotator="user1@example.com",
        )
        action.post_reviewable(
            type="AnnotationReviewable",
            key="annotation_key_2",
            value="annotation_value_2",
            annotator="user2@example.com",
        )

    # Verify that reviews and annotations have been added to the actions
    for action in episode.actions:
        assert len(action.reviews) == 2  # Two reviews per action
        assert len(action.reviewables) == 2  # Two annotations per action

    # Store action IDs for verification after deletion
    action_ids = [action.id for action in episode.actions]

    # Check that actions, reviews, and reviewables are in the database before deletion
    for action_id in action_ids:
        found_actions = ActionEvent.find(id=action_id)
        assert (
            len(found_actions) == 1
        ), f"Action {action_id} was not found in the database"

        found_action = found_actions[0]
        assert (
            len(found_action.reviews) == 2
        ), f"Reviews for action {action_id} are missing or incorrect"
        assert (
            len(found_action.reviewables) == 2
        ), f"Annotations for action {action_id} are missing or incorrect"

    # Delete all actions from the episode
    episode.delete_all_actions()

    # Assert that the in-memory actions list is empty
    assert len(episode.actions) == 0, "Episode actions list was not cleared"

    # Check that the actions are deleted from the database
    for action_id in action_ids:
        found_actions = ActionEvent.find(id=action_id)
        assert (
            len(found_actions) == 0
        ), f"Action {action_id} was not deleted from the database"

        # Also check that the reviews and annotations are deleted
        for action in found_actions:
            assert (
                len(action.reviews) == 0
            ), f"Reviews for action {action.id} were not deleted"
            assert (
                len(action.reviewables) == 0
            ), f"Annotations for action {action.id} were not deleted"


def test_action_event_with_opts_and_ratings():
    # Create ActionEvent with ActionOpts
    state = EnvState(text="Initial state of the environment")
    tool = V1ToolRef(module="tool_module", type="tool_type", version="1.0")

    owner_id = "owner123"

    action = V1Action(name="test_action", parameters={"param1": "value1"})
    action_event = ActionEvent(
        state=state,
        action=action,
        tool=tool,
        namespace="default",
        owner_id=owner_id,
    )

    action_event.add_actionOpt(
        action=V1Action(name="opt1", parameters={"key1": "val1"})
    )
    action_event.add_actionOpt(
        action=V1Action(name="opt2", parameters={"key2": "val2"})
    )

    # Step 3: Fetch the ActionEvent using the find method with owner_id and verify ActionOpts load correctly
    found_actions = ActionEvent.find(id=action_event.id)
    assert len(found_actions) == 1

    found_action_event = found_actions[0]
    assert found_action_event.id == action_event.id
    assert len(found_action_event.action_opts) == 2
    print("ActionEvent and ActionOpts saved and loaded correctly.")

    # Step 4: Use ActionOpt find method to retrieve ActionOpts from the database by action_id
    found_action_opts = ActionOpt.find(action_id=action_event.id)
    assert len(found_action_opts) == 2
    print("ActionOpts found in the database.")

    # Step 5: Add Ratings to the ActionOpts
    rating1 = Rating(
        reviewer="user1",
        rating=5,
        resource_type="action_opt",
        resource_id=found_action_opts[0].id,
        reason="Looks good",
    )

    rating2 = Rating(
        reviewer="user2",
        rating=4,
        resource_type="action_opt",
        resource_id=found_action_opts[1].id,
        reason="Needs improvement",
    )

    # Add ratings to the ActionOpts
    found_action_opts[0].ratings.append(rating1)
    found_action_opts[1].ratings.append(rating2)

    # Step 6: Save ActionOpts with Ratings
    for action_opt in found_action_opts:
        action_opt.save()

    print("Ratings added and saved correctly to ActionOpts.")

    # Step 7: Use ActionOpt find method again to verify ActionOpts and Ratings load correctly
    found_action_opts_with_ratings = ActionOpt.find(action_id=action_event.id)
    assert len(found_action_opts_with_ratings[0].ratings) == 1
    assert found_action_opts_with_ratings[0].ratings[0].reviewer == "user1"
    assert found_action_opts_with_ratings[1].ratings[0].reviewer == "user2"
    print("ActionOpts and Ratings loaded correctly.")

    # Step 8: Use ActionEvent find method to verify Action, ActionOpts, and Ratings all load correctly
    final_found_actions = ActionEvent.find(owner_id=owner_id)
    assert len(final_found_actions) == 1

    final_action_event = final_found_actions[0]
    assert len(final_action_event.action_opts) == 2

    opt1 = final_action_event.action_opts[0]
    opt2 = final_action_event.action_opts[1]

    assert len(opt1.ratings) == 1
    assert opt1.ratings[0].reviewer == "user1"
    assert opt1.ratings[0].reason == "Looks good"

    assert len(opt2.ratings) == 1
    assert opt2.ratings[0].reviewer == "user2"
    assert opt2.ratings[0].reason == "Needs improvement"

    print("Final check: Action, ActionOpts, and Ratings all loaded correctly.")


def test_review_replacement_functions():
    """
    Tests the review methods to ensure that reviews from the same reviewer
    are updated instead of duplicated.
    """
    # Step 1: Create an episode with multiple actions
    episode = create_episode_with_actions(num_actions=3)  # Creates 3 actions
    assert len(episode.actions) == 3, "Episode should have 3 actions"

    # Define reviewers
    reviewers = [
        {"reviewer": "user1@example.com", "reviewer_type": "user"},
        {"reviewer": "user2@example.com", "reviewer_type": "user"},
    ]

    # Step 2: Perform approve_one and fail_one for each reviewer on each action
    for action in episode.actions:
        for reviewer in reviewers:
            # Alternate between approve and fail for demonstration
            if reviewer["reviewer"] == "user1@example.com":
                episode.approve_one(
                    event_id=action.id,
                    reviewer=reviewer["reviewer"],
                    reviewer_type=reviewer["reviewer_type"],
                    reason=f"{reviewer['reviewer']} approves action {action.id}",
                )
            else:
                episode.fail_one(
                    event_id=action.id,
                    reviewer=reviewer["reviewer"],
                    reviewer_type=reviewer["reviewer_type"],
                    reason=f"{reviewer['reviewer']} fails action {action.id}",
                    correction=V1Action(
                        name="click", parameters={"x": 590, "y": 120, "button": "left"}
                    ),
                )

    # Step 3: Verify initial reviews
    for action in episode.actions:
        for reviewer in reviewers:
            matching_reviews = [
                review
                for review in action.reviews
                if review.reviewer == reviewer["reviewer"]
                and review.reviewer_type == reviewer["reviewer_type"]
            ]
            assert (
                len(matching_reviews) == 1
            ), f"Action {action.id} should have exactly one review from {reviewer['reviewer']}"
            if reviewer["reviewer"] == "user1@example.com":
                assert (
                    matching_reviews[0].approved == True
                ), f"Review by {reviewer['reviewer']} should be approved"
                assert (
                    matching_reviews[0].reason
                    == f"{reviewer['reviewer']} approves action {action.id}"
                )
            else:
                assert (
                    matching_reviews[0].approved == False
                ), f"Review by {reviewer['reviewer']} should be failed"
                assert (
                    matching_reviews[0].reason
                    == f"{reviewer['reviewer']} fails action {action.id}"
                )

    # Step 4: Perform approve_all for both reviewers
    for reviewer in reviewers:
        episode.approve_all(
            reviewer=reviewer["reviewer"],
            reviewer_type=reviewer["reviewer_type"],
            approve_hidden=False,  # Assuming no hidden actions
        )

    # Step 4.5: Verify that reviews are updated, not duplicated
    for action in episode.actions:
        for reviewer in reviewers:
            matching_reviews = [
                review
                for review in action.reviews
                if review.reviewer == reviewer["reviewer"]
                and review.reviewer_type == reviewer["reviewer_type"]
            ]
            assert (
                len(matching_reviews) == 1
            ), f"Action {action.id} should have exactly one review from {reviewer['reviewer']}"
            # After fail_all, the latest status should be failed
            assert (
                matching_reviews[0].approved
            ), f"Review by {reviewer['reviewer']} should be failed after fail_all"

    # Step 5: Perform fail_all for both reviewers
    for reviewer in reviewers:
        episode.fail_all(
            reviewer=reviewer["reviewer"],
            reviewer_type=reviewer["reviewer_type"],
            fail_hidden=False,  # Assuming no hidden actions
        )

    # Step 6: Verify that reviews are updated, not duplicated
    for action in episode.actions:
        for reviewer in reviewers:
            matching_reviews = [
                review
                for review in action.reviews
                if review.reviewer == reviewer["reviewer"]
                and review.reviewer_type == reviewer["reviewer_type"]
            ]
            assert (
                len(matching_reviews) == 1
            ), f"Action {action.id} should have exactly one review from {reviewer['reviewer']}"
            # After fail_all, the latest status should be failed
            assert (
                not matching_reviews[0].approved
            ), f"Review by {reviewer['reviewer']} should be failed after fail_all"

    # Step 7: Perform approve_prior on the third action for both reviewers
    third_action = episode.actions[2]
    for reviewer in reviewers:
        episode.approve_prior(
            event_id=third_action.id,
            reviewer=reviewer["reviewer"],
            reviewer_type=reviewer["reviewer_type"],
            approve_hidden=False,
        )

    # Step 8: Perform fail_prior on the second action for both reviewers (so approving only )
    second_action = episode.actions[1]
    # first_action = episode.actions[0]
    for reviewer in reviewers:
        episode.fail_prior(
            event_id=second_action.id,
            reviewer=reviewer["reviewer"],
            reviewer_type=reviewer["reviewer_type"],
            fail_hidden=False,
        )

    # Step 9: Verify that reviews are updated correctly
    for index, action in enumerate(episode.actions):
        for reviewer in reviewers:
            matching_reviews = [
                review
                for review in action.reviews
                if review.reviewer == reviewer["reviewer"]
                and review.reviewer_type == reviewer["reviewer_type"]
            ]
            assert (
                len(matching_reviews) == 1
            ), f"Action {action.id} should have exactly one review from {reviewer['reviewer']}"

            # Determine expected approval status based on the latest operation
            if index == 0:
                expected_approved = False
            elif index == 1:
                expected_approved = False
            else:
                expected_approved = True

            assert (
                matching_reviews[0].approved == expected_approved
            ), f"Review by {reviewer['reviewer']} for action {action.id} index: {index}  should be {'approved' if expected_approved else 'failed'}"

    # Step 10: Ensure no duplicate reviews exist
    for action in episode.actions:
        unique_reviewers = set(
            (review.reviewer, review.reviewer_type) for review in action.reviews
        )
        assert len(unique_reviewers) == len(
            action.reviews
        ), f"Action {action.id} has duplicate reviews"

    print("All review replacement functions tested successfully.")
