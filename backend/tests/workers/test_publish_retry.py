"""Tests for run_publish_retry success-logic with skipped/already_published results."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_job(error_details_dict: dict) -> MagicMock:
    job = MagicMock()
    job.error_details = json.dumps(error_details_dict)
    return job


async def test_run_publish_retry_already_published_in_existing_does_not_block_success():
    """already_published in existing results must not prevent a successful retry."""
    from app.workers.publish_retry import run_publish_retry

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = _make_job({"instagram": "already_published"})

    mock_update_campaign_status = AsyncMock()
    mock_update_job = AsyncMock()

    with (
        patch("app.workers.publish_retry.get_session_context") as mock_ctx,
        patch("app.workers.publish_retry.get_job", AsyncMock(return_value=job)),
        patch("app.workers.publish_retry.dispatch_publish_for_platform", AsyncMock(return_value={"wordpress": "success"})),
        patch("app.workers.publish_retry.update_campaign_status", mock_update_campaign_status),
        patch("app.workers.publish_retry.update_job", mock_update_job),
        patch("app.workers.publish_retry.get_campaign", AsyncMock(return_value=None)),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        await run_publish_retry(job_id, campaign_id, "wordpress")

    mock_update_campaign_status.assert_called_with(db, campaign_id, "published")
    complete_call = next(
        (c for c in mock_update_job.call_args_list if c.kwargs.get("status") == "complete"),
        None,
    )
    assert complete_call is not None


async def test_run_publish_retry_skipped_in_existing_does_not_block_success():
    """skipped in existing results must not prevent a successful retry."""
    from app.workers.publish_retry import run_publish_retry

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = _make_job({"instagram": "skipped"})

    mock_update_campaign_status = AsyncMock()

    with (
        patch("app.workers.publish_retry.get_session_context") as mock_ctx,
        patch("app.workers.publish_retry.get_job", AsyncMock(return_value=job)),
        patch("app.workers.publish_retry.dispatch_publish_for_platform", AsyncMock(return_value={"wordpress": "success"})),
        patch("app.workers.publish_retry.update_campaign_status", mock_update_campaign_status),
        patch("app.workers.publish_retry.update_job", AsyncMock()),
        patch("app.workers.publish_retry.get_campaign", AsyncMock(return_value=None)),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        await run_publish_retry(job_id, campaign_id, "wordpress")

    mock_update_campaign_status.assert_called_with(db, campaign_id, "published")


async def test_run_publish_retry_all_skipped_stays_failed():
    """If new result is only skipped (and nothing previously succeeded), stay failed."""
    from app.workers.publish_retry import run_publish_retry

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = _make_job({})

    mock_update_campaign_status = AsyncMock()
    mock_update_job = AsyncMock()

    with (
        patch("app.workers.publish_retry.get_session_context") as mock_ctx,
        patch("app.workers.publish_retry.get_job", AsyncMock(return_value=job)),
        patch("app.workers.publish_retry.dispatch_publish_for_platform", AsyncMock(return_value={"instagram": "skipped"})),
        patch("app.workers.publish_retry.update_campaign_status", mock_update_campaign_status),
        patch("app.workers.publish_retry.update_job", mock_update_job),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        await run_publish_retry(job_id, campaign_id, "instagram")

    mock_update_campaign_status.assert_called_with(db, campaign_id, "failed")
    failed_call = next(
        (c for c in mock_update_job.call_args_list if c.kwargs.get("status") == "failed"),
        None,
    )
    assert failed_call is not None


async def test_run_publish_retry_real_failure_stays_failed():
    """A real platform error string must still result in failed status."""
    from app.workers.publish_retry import run_publish_retry

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = _make_job({"instagram": "Instagram returned 400"})

    mock_update_campaign_status = AsyncMock()

    with (
        patch("app.workers.publish_retry.get_session_context") as mock_ctx,
        patch("app.workers.publish_retry.get_job", AsyncMock(return_value=job)),
        patch("app.workers.publish_retry.dispatch_publish_for_platform", AsyncMock(return_value={"instagram": "Instagram returned 400"})),
        patch("app.workers.publish_retry.update_campaign_status", mock_update_campaign_status),
        patch("app.workers.publish_retry.update_job", AsyncMock()),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        await run_publish_retry(job_id, campaign_id, "instagram")

    mock_update_campaign_status.assert_called_with(db, campaign_id, "failed")


async def test_run_publish_retry_success_clears_error_details():
    """On success, update_job is called with error_details=None to clear it."""
    from app.workers.publish_retry import run_publish_retry

    campaign_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job = _make_job({"wordpress": "WordPress returned 401"})

    mock_update_job = AsyncMock()

    with (
        patch("app.workers.publish_retry.get_session_context") as mock_ctx,
        patch("app.workers.publish_retry.get_job", AsyncMock(return_value=job)),
        patch("app.workers.publish_retry.dispatch_publish_for_platform", AsyncMock(return_value={"wordpress": "success"})),
        patch("app.workers.publish_retry.update_campaign_status", AsyncMock()),
        patch("app.workers.publish_retry.update_job", mock_update_job),
        patch("app.workers.publish_retry.get_campaign", AsyncMock(return_value=None)),
    ):
        db = AsyncMock()
        db.__aenter__ = AsyncMock(return_value=db)
        db.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.return_value = db

        await run_publish_retry(job_id, campaign_id, "wordpress")

    complete_call = next(
        (c for c in mock_update_job.call_args_list if c.kwargs.get("status") == "complete"),
        None,
    )
    assert complete_call is not None
    assert complete_call.kwargs.get("error_details") is None
