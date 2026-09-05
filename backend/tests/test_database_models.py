from app.db.base import Base
from app.models import Artwork, Episode, PublishRun, Season, Show, User


def test_model_classes_are_importable() -> None:
    assert Base is not None
    assert User.__tablename__ == "users"
    assert Show.__tablename__ == "shows"
    assert Season.__tablename__ == "seasons"
    assert Episode.__tablename__ == "episodes"
    assert Artwork.__tablename__ == "artworks"
    assert PublishRun.__tablename__ == "publish_runs"


def test_unique_constraint_is_defined_for_content_group_and_language() -> None:
    episode_constraints = Episode.__table__.constraints
    assert any(
        getattr(constraint, "name", "") == "uq_episode_content_group_language"
        for constraint in episode_constraints
    )
