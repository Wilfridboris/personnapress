"""Tests that article hook failure does not fail the publish job."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_campaign(campaign_id=None, client_id=None):
    c = MagicMock()
    c.id = campaign_id or uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.blog_html = "<h1>Title</h1><p>Body</p>"
    c.brain_dump = "Some brain dump"
    c.voice_score = None
    c.image_url = None
    c.status = "published"
    return c


async def test_article_hook_failure_does_not_fail_publish_job():
    """If article service raises, the publish job must still complete successfully."""
    from app.workers.publish import run_publish

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign(campaign_id=campaign_id)

    with (
        patch("app.workers.publish.get_session_context") as mock_ctx,
        patch("app.workers.publish.update_job", AsyncMock()),
        patch("app.workers.publish.dispatch_publish", AsyncMock(return_value={"wordpress": "success"})),
        patch("app.workers.publish.update_campaign_status", AsyncMock()),
        patch("app.workers.publish.update_campaign_scheduled_at", AsyncMock()),
        patch("app.workers.publish.get_campaign", AsyncMock(return_value=campaign)),
        patch(
            "app.workers.publish.create_or_update_article_from_campaign",
            AsyncMock(side_effect=RuntimeError("DB exploded")),
        ),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        # Must not raise even though article service failed
        # If this completes without raising, the hook is correctly swallowed
        await run_publish(job_id, campaign_id)


async def test_article_hook_failure_does_not_fail_github_direct_commit():
    """Article hook failure on GitHub direct-commit path must not raise."""
    from app.workers.publish import publish_github_job

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    campaign = _make_campaign(campaign_id=campaign_id)
    campaign.github_pr_url = None

    creds = {
        "installation_token": "tok",
        "expires_at": "2099-01-01T00:00:00Z",
        "repo_full_name": "owner/repo",
    }
    import json
    from app.core.security import encrypt_credential

    conn = MagicMock()
    conn.platform = "github_pages"
    conn.encrypted_credentials = encrypt_credential(json.dumps(creds))

    with (
        patch("app.workers.publish.get_session_context") as mock_ctx,
        patch("app.workers.publish.update_job", AsyncMock()),
        patch("app.workers.publish.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.workers.publish.get_connections_for_client", AsyncMock(return_value=[conn])),
        patch("app.workers.publish._refresh_token_if_needed", AsyncMock(return_value=creds)),
        patch(
            "app.workers.publish.generate_github_post_file",
            AsyncMock(return_value=("_posts/post.md", "content", "commit msg", "Title")),
        ),
        patch("app.workers.publish.github_integration.create_file_commit", AsyncMock(return_value="abc123")),
        patch("app.workers.publish.update_campaign_status", AsyncMock()),
        patch(
            "app.workers.publish.create_or_update_article_from_campaign",
            AsyncMock(side_effect=RuntimeError("Article DB error")),
        ),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        # Must not raise
        await publish_github_job(job_id, campaign_id, mode="direct")
