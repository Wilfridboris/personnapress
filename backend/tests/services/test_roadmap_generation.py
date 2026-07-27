"""Tests for services/roadmap.py — generate_roadmap orchestrator (Story 20-1)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.db.repositories.models import CampaignStatus, RoadmapStatus


def _make_roadmap(
    roadmap_id=None,
    skip_blog=False,
    generate_images=False,
    brain_dump="Test brain dump content",
):
    r = MagicMock()
    r.id = roadmap_id or uuid.uuid4()
    r.user_id = uuid.uuid4()
    r.client_id = uuid.uuid4()
    r.brain_dump = brain_dump
    r.skip_blog = skip_blog
    r.generate_images = generate_images
    r.status = RoadmapStatus.pending
    r.error_message = None
    r.updated_at = None
    return r


def _make_client(roadmap_config=None):
    c = MagicMock()
    c.user_id = uuid.uuid4()
    c.brand_voice_profile = {"tone": ["professional"]}
    c.roadmap_config = roadmap_config or {}
    return c


def _make_campaign(roadmap_id=None):
    camp = MagicMock()
    camp.id = uuid.uuid4()
    camp.roadmap_id = roadmap_id
    camp.blog_html = "<h1>Test Blog</h1><p>Content</p>"
    camp.x_post = None
    camp.linkedin_post = None
    return camp


def _make_db(roadmap, client, campaign):
    db = AsyncMock()

    roadmap_result = MagicMock()
    roadmap_result.scalar_one_or_none.return_value = roadmap

    client_result = MagicMock()
    client_result.scalar_one_or_none.return_value = client

    # refresh reloads campaign
    async def _refresh(obj):
        if hasattr(obj, "id") and hasattr(obj, "roadmap_id"):
            obj.blog_html = campaign.blog_html

    db.refresh = AsyncMock(side_effect=_refresh)

    # Execute returns different results based on call order
    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return roadmap_result
        return client_result

    db.execute = AsyncMock(side_effect=_execute)
    return db


async def test_generate_roadmap_creates_blog_and_social_campaigns():
    """Blog + 1 X + 1 LinkedIn slot: 3 campaigns created, roadmaps_used NOT changed (checked before)."""
    roadmap = _make_roadmap()
    client = _make_client(roadmap_config={"linkedin_count": 1, "twitter_count": 1, "blog_enabled": True, "images_enabled": False})
    blog_campaign = _make_campaign(roadmap_id=roadmap.id)

    db = AsyncMock()

    # Simulate execute calls returning roadmap then client then any subsequent
    execute_results = []

    roadmap_result = MagicMock()
    roadmap_result.scalar_one_or_none.return_value = roadmap

    client_result = MagicMock()
    client_result.scalar_one_or_none.return_value = client

    blog_camp_result = MagicMock()
    blog_camp_result.scalar_one_or_none.return_value = blog_campaign

    responses = iter([roadmap_result, client_result, blog_camp_result])

    async def _execute(stmt):
        try:
            return next(responses)
        except StopIteration:
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            r.scalars.return_value.first.return_value = None
            return r

    db.execute = AsyncMock(side_effect=_execute)

    async def _refresh(obj):
        if hasattr(obj, "blog_html"):
            obj.blog_html = "<h1>Test Blog</h1>"

    db.refresh = AsyncMock(side_effect=_refresh)

    created_campaigns = []

    def _add(obj):
        created_campaigns.append(obj)

    db.add = MagicMock(side_effect=_add)

    roadmap_ids_used = []

    with patch("app.services.roadmap.check_image_limit_batch", new_callable=AsyncMock) as mock_batch, \
         patch("app.services.roadmap.generation_service.generate_social_only", new_callable=AsyncMock) as mock_social, \
         patch("app.services.roadmap.image_service.generate_image_for_roadmap_campaign", new_callable=AsyncMock) as mock_img, \
         patch("app.services.roadmap.run_generation_pipeline", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.roadmap.create_job", new_callable=AsyncMock) as mock_job:

        mock_batch.return_value = (0, 3)  # no images allowed
        mock_job.return_value = MagicMock(id=uuid.uuid4())

        from app.services.roadmap import generate_roadmap
        await generate_roadmap(roadmap.id, db)

    # roadmap status should be 'ready'
    assert roadmap.status == RoadmapStatus.ready

    # generate_social_only called twice (1 x + 1 linkedin)
    assert mock_social.call_count == 2
    x_call = mock_social.call_args_list[0]
    assert x_call.args[2] == "x"
    li_call = mock_social.call_args_list[1]
    assert li_call.args[2] == "linkedin"

    # run_generation_pipeline called once for blog
    assert mock_gen.call_count == 1

    # no images since images_enabled=False/allowed=0
    mock_img.assert_not_called()


async def test_generate_roadmap_increments_roadmaps_used_once():
    """roadmaps_used is incremented by check_roadmap_limit in the router (once), not N times here."""
    roadmap = _make_roadmap(skip_blog=False)
    client = _make_client(roadmap_config={"linkedin_count": 0, "twitter_count": 0, "blog_enabled": True, "images_enabled": False})
    blog_campaign = _make_campaign(roadmap_id=roadmap.id)

    db = AsyncMock()

    roadmap_result = MagicMock()
    roadmap_result.scalar_one_or_none.return_value = roadmap

    client_result = MagicMock()
    client_result.scalar_one_or_none.return_value = client

    blog_camp_result = MagicMock()
    blog_camp_result.scalar_one_or_none.return_value = blog_campaign

    responses = iter([roadmap_result, client_result, blog_camp_result])

    async def _execute(stmt):
        try:
            return next(responses)
        except StopIteration:
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            r.scalars.return_value.first.return_value = None
            return r

    db.execute = AsyncMock(side_effect=_execute)

    async def _refresh(obj):
        if hasattr(obj, "blog_html"):
            obj.blog_html = "<h1>Test</h1>"

    db.refresh = AsyncMock(side_effect=_refresh)
    db.add = MagicMock()

    with patch("app.services.roadmap.check_image_limit_batch", new_callable=AsyncMock, return_value=(0, 1)), \
         patch("app.services.roadmap.run_generation_pipeline", new_callable=AsyncMock), \
         patch("app.services.roadmap.create_job", new_callable=AsyncMock, return_value=MagicMock(id=uuid.uuid4())):

        from app.services.roadmap import generate_roadmap
        await generate_roadmap(roadmap.id, db)

    # check_roadmap_limit is called in the router, NOT inside generate_roadmap
    # so roadmaps_used should NOT be touched here
    assert roadmap.status == RoadmapStatus.ready


async def test_generate_roadmap_sets_failed_on_exception():
    """Unrecoverable error sets roadmap.status=failed."""
    # skip_blog=True avoids blog slot so execute calls are predictable
    roadmap = _make_roadmap(skip_blog=True)
    client = _make_client(roadmap_config={"twitter_count": 1, "linkedin_count": 0, "blog_enabled": False, "images_enabled": False})

    db = AsyncMock()

    roadmap_result = MagicMock()
    roadmap_result.scalar_one_or_none.return_value = roadmap

    client_result = MagicMock()
    client_result.scalar_one_or_none.return_value = client

    # Second pass for the failed-state reload
    roadmap_result2 = MagicMock()
    roadmap_result2.scalar_one_or_none.return_value = roadmap

    responses = iter([roadmap_result, client_result, roadmap_result2])

    async def _execute(stmt):
        try:
            return next(responses)
        except StopIteration:
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            return r

    db.execute = AsyncMock(side_effect=_execute)
    db.add = MagicMock()

    with patch("app.services.roadmap.check_image_limit_batch", new_callable=AsyncMock, return_value=(0, 0)), \
         patch("app.services.roadmap.generation_service.generate_social_only", new_callable=AsyncMock, side_effect=RuntimeError("Gemini unavailable")):

        from app.services.roadmap import generate_roadmap
        await generate_roadmap(roadmap.id, db)

    assert roadmap.status == RoadmapStatus.failed
    assert "Gemini unavailable" in (roadmap.error_message or "")
