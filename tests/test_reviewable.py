import pytest
from skillpacks.server.models import V1BoundingBox, V1Action, V1BoundingBoxReviewable
from skillpacks.db.models import ReviewableRecord, ActionRecord
from skillpacks import Reviewable, Review, BoundingBoxReviewable, ActionEvent, EnvState
from toolfuse.models import V1ToolRef

@pytest.fixture
def bounding_box_reviewable():
    """Fixture to create a BoundingBoxReviewable instance."""
    bbox = V1BoundingBox(x0=10, x1=100, y0=20, y1=200)
    return BoundingBoxReviewable(
        resource_type="action",
        resource_id="actionID123",
        img="https://example.com/img.png",
        target="Object A",
        bbox=bbox,
    )


def test_bounding_box_reviewable_creation(bounding_box_reviewable: BoundingBoxReviewable):
    """Test that a BoundingBoxReviewable instance is created correctly."""
    assert bounding_box_reviewable.img == "https://example.com/img.png"
    assert bounding_box_reviewable.target == "Object A"
    assert isinstance(bounding_box_reviewable.bbox, V1BoundingBox)
    assert isinstance(bounding_box_reviewable, BoundingBoxReviewable)


def test_bounding_box_reviewable_save(bounding_box_reviewable: BoundingBoxReviewable):
    """Test saving a BoundingBoxReviewable instance to the database."""
    # Save the reviewable to the test database
    bounding_box_reviewable.save()

    # Verify that it has been saved correctly
    for db in bounding_box_reviewable.get_db():
        reviewable_record = (
            db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        )
        assert reviewable_record is not None
        assert reviewable_record.type == "BoundingBoxReviewable" # type: ignore


def test_find_and_save_bounding_box_reviewable(bounding_box_reviewable: BoundingBoxReviewable):
    """Test finding the saved BoundingBoxReviewable from the database."""
    # Save the reviewable to the database
    bounding_box_reviewable.save()

    # Retrieve it using the dynamic find method
    found_reviewables = Reviewable.find(id=bounding_box_reviewable.id)
    assert len(found_reviewables) == 1
    assert isinstance(found_reviewables[0], BoundingBoxReviewable)
    assert found_reviewables[0].id == bounding_box_reviewable.id


def test_bounding_box_reviewable_with_reviews(bounding_box_reviewable: BoundingBoxReviewable):
    """Test saving a BoundingBoxReviewable instance with reviews."""
    bbox = V1BoundingBox(x0=15, x1=150, y0=23, y1=190)
    review1 = Review(
        resource_type="reviewable",
        reviewer="John",
        approved=True,
        reviewer_type="human",
    )
    review2 = Review(
        resource_type="reviewable",
        reviewer="Jane",
        approved=False,
        reviewer_type="human",
        correction=bbox.model_dump_json(),
    )
    bounding_box_reviewable.reviews = [review1, review2]

    # Save the reviewable along with its reviews
    bounding_box_reviewable.save()

    # Retrieve and verify the reviews
    for db in bounding_box_reviewable.get_db():
        reviewable_record = (
            db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        )
        assert reviewable_record is not None, "Reviewable record not found in the database"
        assert len(reviewable_record.reviews) == 2


def test_bounding_box_reviewable_with_post_reviews(bounding_box_reviewable: BoundingBoxReviewable):
    """Test saving a BoundingBoxReviewable instance with reviews."""
    # Save the reviewable before its review
    bounding_box_reviewable.save()
    bbox = V1BoundingBox(x0=15, x1=150, y0=23, y1=190)
    bounding_box_reviewable.post_review(
        reviewer="Jane", approved=False, reviewer_type="human", correction=bbox
    )
    bounding_box_reviewable.post_review(
        reviewer="John", approved=True, reviewer_type="human"
    )
    # Retrieve and verify the reviews
    for db in bounding_box_reviewable.get_db():
        reviewable_record = (
            db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        )
        assert reviewable_record is not None, "Reviewable record not found in the database"
        assert len(reviewable_record.reviews) == 2


def test_find_v1_reviewable(bounding_box_reviewable: BoundingBoxReviewable):
    """Test finding and converting Reviewable instances to V1 format."""
    bounding_box_reviewable.save()

    # Perform the find operation and check V1 conversion
    v1_reviewables = Reviewable.find_v1(id=bounding_box_reviewable.id)
    assert len(v1_reviewables) == 1
    v1_data = v1_reviewables[0]
    assert v1_data.reviewable["img"] == bounding_box_reviewable.img
    assert v1_data.reviewable["bbox"]["x0"] == 10

def test_post_reviewable_and_add_reviews():
    """Test the post_reviewable function and adding reviews using Reviewable methods."""

    # Create an action
    env_state = EnvState(
        images=["https://example.com/image1.png", "https://example.com/image2.png"],
        text="Initial environment state"
    )
    action = V1Action(
        name="type_text",
        parameters={
            "text": "puppies\n"
        }
    )
    tool = V1ToolRef(
        module="surfpizza.tool",
        type="SemanticDesktop",
        version="0.1.0",
        package=None
    )

    action_event = ActionEvent(
        state=env_state,
        action=action,
        tool=tool,
        namespace="default"
    )

    # Use post_reviewable function to add a BoundingBoxReviewable
    bbox = V1BoundingBox(x0=10, x1=100, y0=20, y1=200)
    action_event.post_reviewable(
        type="BoundingBoxReviewable",
        img="https://example.com/img.png",
        target="Object A",
        bbox=bbox,
    )

    # Add reviews to the reviewable
    # Retrieve the added reviewable
    reviewable = action_event.reviewables[0]
    
    # Post two reviews using the post_review method from the Reviewable class
    bbox_correction = V1BoundingBox(x0=15, x1=150, y0=25, y1=205)
    reviewable.post_review(
        reviewer="Reviewer1", approved=True, reviewer_type="human"
    )
    reviewable.post_review(
        reviewer="Reviewer2", approved=False, reviewer_type="human", correction=bbox_correction
    )

    # Save the action and associated reviewables and reviews
    action_event.save()

    # Verify that the action, reviewable, and reviews were saved correctly
    for db in action_event.get_db():
        # Verify action
        action_record = db.query(ActionRecord).filter_by(id=action_event.id).first()
        assert action_record is not None
        assert len(action_record.reviewables) == 1  # One reviewable added

        # Load ActionEvent from record and verify
        loaded_action_event = ActionEvent.from_record(action_record)
        assert len(loaded_action_event.reviewables) == 1  # One reviewable added
        assert len(loaded_action_event.reviewables[0].reviews) == 2  # Two reviews added to reviewable

        # Verify that the reviewable is an instance of BoundingBoxReviewable and the correct schema
        reviewable_record = loaded_action_event.reviewables[0]
        assert V1BoundingBoxReviewable.model_validate(reviewable_record.to_v1().model_dump())

        # Verify reviews for the reviewable
        reviews = reviewable_record.reviews
        assert reviews[0].reviewer == "Reviewer1"
        assert reviews[0].approved is True
        assert reviews[1].reviewer == "Reviewer2"
        assert reviews[1].approved is False
        assert reviews[1].correction is not None  # Correction added

    # Verify using the to_v1 method
    v1_action_event = action_event.to_v1()
    assert v1_action_event is not None
    assert v1_action_event.reviewables[0].type == "BoundingBoxReviewable"
    assert len(v1_action_event.reviewables[0].reviews) == 2  # Verify 2 reviews in V1 format

    # Verify using the from_v1 method
    loaded_action_event_from_v1 = ActionEvent.from_v1(v1_action_event)
    assert loaded_action_event_from_v1 is not None
    assert len(loaded_action_event_from_v1.reviewables) == 1  # One reviewable added
    assert len(loaded_action_event_from_v1.reviewables[0].reviews) == 2  # Two reviews added