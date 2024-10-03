# from mllm import Prompt, RoleThread, RoleMessage
# from toolfuse.models import V1ToolRef

import pytest
from skillpacks.server.models import V1BoundingBox, V1BoundingBoxReviewable
from skillpacks.db.models import ReviewableRecord
from skillpacks import Reviewable, Review, BoundingBoxReviewable


@pytest.fixture
def bounding_box_reviewable():
    """Fixture to create a BoundingBoxReviewable instance."""
    bbox = V1BoundingBox(x0=10, x1=100, y0=20, y1=200)
    return BoundingBoxReviewable(resource_type="action", resource_id="actionID123", img="https://example.com/img.png", target="Object A", bbox=bbox)

def test_bounding_box_reviewable_creation(bounding_box_reviewable):
    """Test that a BoundingBoxReviewable instance is created correctly."""
    assert bounding_box_reviewable.img == "https://example.com/img.png"
    assert bounding_box_reviewable.target == "Object A"
    assert isinstance(bounding_box_reviewable.bbox, V1BoundingBox)
    assert isinstance(bounding_box_reviewable, BoundingBoxReviewable)

def test_bounding_box_reviewable_save(bounding_box_reviewable):
    """Test saving a BoundingBoxReviewable instance to the database."""
    # Save the reviewable to the test database
    bounding_box_reviewable.save()

    # Verify that it has been saved correctly
    for db in bounding_box_reviewable.get_db():
        reviewable_record = db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        assert reviewable_record is not None
        assert reviewable_record.type == "BoundingBoxReviewable"

def test_find_and_save_bounding_box_reviewable(bounding_box_reviewable):
    """Test finding the saved BoundingBoxReviewable from the database."""
    # Save the reviewable to the database
    bounding_box_reviewable.save()

    # Retrieve it using the dynamic find method
    found_reviewables = Reviewable.find(id=bounding_box_reviewable.id)
    assert len(found_reviewables) == 1
    assert isinstance(found_reviewables[0], BoundingBoxReviewable)
    assert found_reviewables[0].id == bounding_box_reviewable.id

def test_bounding_box_reviewable_with_reviews(bounding_box_reviewable):
    """Test saving a BoundingBoxReviewable instance with reviews."""
    bbox = V1BoundingBox(x0=15, x1=150, y0=23, y1=190)
    review1 = Review(resource_type="reviewable", reviewer="John", approved=True, reviewer_type="human")
    review2 = Review(resource_type="reviewable", reviewer="Jane", approved=False, reviewer_type="human", correction=bbox.model_dump_json())
    bounding_box_reviewable.reviews = [review1, review2]

    # Save the reviewable along with its reviews
    bounding_box_reviewable.save()

    # Retrieve and verify the reviews
    for db in bounding_box_reviewable.get_db():
        reviewable_record = db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        assert len(reviewable_record.reviews) == 2

def test_bounding_box_reviewable_with_post_reviews(bounding_box_reviewable):
    """Test saving a BoundingBoxReviewable instance with reviews."""
    # Save the reviewable before its review
    bounding_box_reviewable.save()
    bbox = V1BoundingBox(x0=15, x1=150, y0=23, y1=190)
    bounding_box_reviewable.post_review( reviewer="Jane", approved=False, reviewer_type="human", correction=bbox)
    bounding_box_reviewable.post_review( reviewer="John", approved=True, reviewer_type="human")
    # Retrieve and verify the reviews
    for db in bounding_box_reviewable.get_db():
        reviewable_record = db.query(ReviewableRecord).filter_by(id=bounding_box_reviewable.id).first()
        assert len(reviewable_record.reviews) == 2

def test_find_v1_reviewable(bounding_box_reviewable):
    """Test finding and converting Reviewable instances to V1 format."""
    bounding_box_reviewable.save()
    
    # Perform the find operation and check V1 conversion
    v1_reviewables = Reviewable.find_v1(id=bounding_box_reviewable.id)
    assert len(v1_reviewables) == 1
    v1_data = v1_reviewables[0]
    assert v1_data.reviewable["img"] == bounding_box_reviewable.img
    assert v1_data.reviewable["bbox"]["x0"] == 10