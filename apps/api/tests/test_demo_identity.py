from uuid import UUID

from app.domain.demo_identity import demo_id
from app.services.project_reads import LOCAL_DEMO_ACTOR_ID


def test_product_rename_preserves_installed_project_and_actor_identity():
    assert demo_id("project") == UUID("b0b0fead-d9da-54f3-9fd2-aac6e7ab1a0d")
    assert demo_id("sarah") == UUID("892b7c18-5b23-526f-a899-757d871d7a06")
    assert LOCAL_DEMO_ACTOR_ID == demo_id("sarah")
