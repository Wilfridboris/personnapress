"""Unit tests for the subscription_cleanup APScheduler job."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.cleanup import (
    _delete_user_data,
    _phase1_warn,
    _phase2_delete,
    subscription_cleanup,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_sub(
    user_id=None,
    status="trial_expired",
    deletion_scheduled_at=None,
    updated_at=None,
):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.user_id = user_id or uuid.uuid4()
    m.status = status
    m.deletion_scheduled_at = deletion_scheduled_at
    m.updated_at = updated_at or _utcnow_naive()
    return m


def _make_user(user_id=None, email="user@example.com"):
    m = MagicMock()
    m.id = user_id or uuid.uuid4()
    m.email = email
    m.hashed_password = "hashed"
    m.google_sub = "google_sub_id"
    m.stripe_customer_id = "cus_123"
    return m


def _make_db_scalars(items: list):
    """Return an AsyncMock db.execute() result whose .scalars().all() yields items."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return AsyncMock(return_value=result)


def _make_db_scalar_one(item):
    """Return an AsyncMock db.execute() result whose .scalar_one_or_none() yields item."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# Phase 1 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase1_sends_warning_email_and_sets_deletion_date():
    user_id = uuid.uuid4()
    sub = _make_sub(
        user_id=user_id,
        deletion_scheduled_at=None,
        updated_at=_utcnow_naive() - timedelta(days=31),
    )
    user = _make_user(user_id=user_id)

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            # First call: fetch qualifying subscriptions
            MagicMock(**{"scalars.return_value.all.return_value": [sub]}),
            # Second call: fetch user by sub.user_id
            MagicMock(**{"scalar_one_or_none.return_value": user}),
        ]
    )

    with patch("app.workers.cleanup.send_deletion_warning_email") as mock_send:
        await _phase1_warn(db)

    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == user.email
    # deletion_date_str should be a non-empty formatted date
    assert len(call_args[1]) > 0

    assert sub.deletion_scheduled_at is not None
    expected_date = datetime.now(timezone.utc) + timedelta(days=7)
    delta = abs((sub.deletion_scheduled_at - expected_date.replace(tzinfo=None)).total_seconds())
    assert delta < 5  # within 5 seconds

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_phase1_skips_recently_expired():
    sub = _make_sub(
        deletion_scheduled_at=None,
        updated_at=_utcnow_naive() - timedelta(days=20),
    )

    db = AsyncMock()
    # The query filters at DB level; simulate no results returned (the DB filter excluded the row)
    db.execute = AsyncMock(
        return_value=MagicMock(**{"scalars.return_value.all.return_value": []})
    )

    with patch("app.workers.cleanup.send_deletion_warning_email") as mock_send:
        await _phase1_warn(db)

    mock_send.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_phase1_continues_on_single_failure():
    """A single-user failure should not stop processing of other users."""
    user_id1 = uuid.uuid4()
    user_id2 = uuid.uuid4()
    sub1 = _make_sub(user_id=user_id1, updated_at=_utcnow_naive() - timedelta(days=31))
    sub2 = _make_sub(user_id=user_id2, updated_at=_utcnow_naive() - timedelta(days=32))
    user1 = _make_user(user_id=user_id1, email="u1@example.com")
    user2 = _make_user(user_id=user_id2, email="u2@example.com")

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(**{"scalars.return_value.all.return_value": [sub1, sub2]}),
            MagicMock(**{"scalar_one_or_none.return_value": user1}),
            MagicMock(**{"scalar_one_or_none.return_value": user2}),
        ]
    )

    call_count = 0

    def _send_side_effect(email, deletion_date):
        nonlocal call_count
        call_count += 1
        if email == user1.email:
            raise RuntimeError("Resend API error")

    with patch("app.workers.cleanup.send_deletion_warning_email", side_effect=_send_side_effect):
        with patch("app.workers.cleanup.sentry_sdk") as mock_sentry:
            await _phase1_warn(db)

    mock_sentry.capture_exception.assert_called_once()
    assert call_count == 2  # both users were attempted


# ---------------------------------------------------------------------------
# Phase 2 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase2_deletes_user_data():
    user_id = uuid.uuid4()
    sub = _make_sub(
        user_id=user_id,
        deletion_scheduled_at=_utcnow_naive() - timedelta(days=1),
    )
    user = _make_user(user_id=user_id)

    db = AsyncMock()
    # Track execute calls for assertions; all delete/flush calls are mocked automatically
    db.execute = AsyncMock(
        return_value=MagicMock(**{"scalars.return_value.all.return_value": [sub]})
    )

    with patch("app.workers.cleanup._delete_user_data", new_callable=AsyncMock) as mock_del, \
         patch("app.workers.cleanup._anonymize_user", new_callable=AsyncMock) as mock_anon, \
         patch("app.workers.cleanup.sentry_sdk") as mock_sentry:
        await _phase2_delete(db)

    mock_del.assert_awaited_once_with(db, user_id)
    mock_anon.assert_awaited_once_with(db, user_id)
    db.commit.assert_awaited_once()
    mock_sentry.capture_message.assert_called_once()


@pytest.mark.asyncio
async def test_phase2_skips_user_with_future_deletion_date():
    """Users with deletion_scheduled_at in the future must not be deleted."""
    db = AsyncMock()
    # DB-level filter excludes future-dated rows; simulate empty result
    db.execute = AsyncMock(
        return_value=MagicMock(**{"scalars.return_value.all.return_value": []})
    )

    with patch("app.workers.cleanup._delete_user_data", new_callable=AsyncMock) as mock_del:
        await _phase2_delete(db)

    mock_del.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_phase2_continues_on_single_failure():
    """An error deleting one user should not stop the rest of the batch."""
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    uid3 = uuid.uuid4()
    sub1 = _make_sub(user_id=uid1, deletion_scheduled_at=_utcnow_naive() - timedelta(days=1))
    sub2 = _make_sub(user_id=uid2, deletion_scheduled_at=_utcnow_naive() - timedelta(days=1))
    sub3 = _make_sub(user_id=uid3, deletion_scheduled_at=_utcnow_naive() - timedelta(days=1))

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(**{"scalars.return_value.all.return_value": [sub1, sub2, sub3]})
    )

    processed = []

    async def _mock_del(db, user_id):
        if user_id == uid2:
            raise RuntimeError("DB error")
        processed.append(user_id)

    with patch("app.workers.cleanup._delete_user_data", side_effect=_mock_del), \
         patch("app.workers.cleanup._anonymize_user", new_callable=AsyncMock), \
         patch("app.workers.cleanup.sentry_sdk") as mock_sentry:
        await _phase2_delete(db)

    assert uid1 in processed
    assert uid3 in processed
    mock_sentry.capture_exception.assert_called_once()


# ---------------------------------------------------------------------------
# Batch limit test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_limit_50():
    """Verify the query is issued with LIMIT 50."""
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(**{"scalars.return_value.all.return_value": []})
    )

    await _phase1_warn(db)

    # Inspect the SQLAlchemy query passed to execute for the LIMIT clause
    call_args = db.execute.call_args_list[0][0][0]
    compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "50" in compiled


# ---------------------------------------------------------------------------
# subscription_cleanup integration (uses async_session_factory)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_subscription_cleanup_calls_both_phases():
    mock_db = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.workers.cleanup.async_session_factory", return_value=mock_ctx), \
         patch("app.workers.cleanup._phase1_warn", new_callable=AsyncMock) as mock_p1, \
         patch("app.workers.cleanup._phase2_delete", new_callable=AsyncMock) as mock_p2:
        await subscription_cleanup()

    mock_p1.assert_awaited_once_with(mock_db)
    mock_p2.assert_awaited_once_with(mock_db)
