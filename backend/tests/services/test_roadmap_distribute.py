"""Unit tests for distribute_schedule pure function (Story 20-3, Task 1)."""
import uuid
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.services.roadmap import (
    _campaign_platform,
    _prioritize_image_targets,
    distribute_schedule,
)


def _campaign(
    blog_html=None,
    linkedin_post=None,
    x_post=None,
    instagram_caption=None,
    facebook_post=None,
):
    c = SimpleNamespace(
        id=uuid.uuid4(),
        blog_html=blog_html,
        linkedin_post=linkedin_post,
        x_post=x_post,
        instagram_caption=instagram_caption,
        facebook_post=facebook_post,
    )
    return c


MONDAY = date(2026, 7, 27)  # A known Monday


# ---------------------------------------------------------------------------
# Basic single-platform cases
# ---------------------------------------------------------------------------

def test_single_x_post_scheduled_monday_0800():
    x = _campaign(x_post="hello x")
    result = distribute_schedule([x], MONDAY)
    assert x.id in result
    dt = result[x.id]
    assert dt.weekday() == 0  # Monday
    assert dt.hour == 8


def test_single_linkedin_post_scheduled_monday_0900():
    li = _campaign(linkedin_post="hello linkedin")
    result = distribute_schedule([li], MONDAY)
    dt = result[li.id]
    assert dt.weekday() == 0
    assert dt.hour == 9


def test_single_blog_full_scheduled_monday_0900():
    blog = _campaign(blog_html="<h1>Title</h1>", linkedin_post="share", x_post="tweet")
    result = distribute_schedule([blog], MONDAY)
    dt = result[blog.id]
    assert dt.weekday() == 0
    assert dt.hour == 9


# ---------------------------------------------------------------------------
# X cycling times: 08, 12, 17
# ---------------------------------------------------------------------------

def test_x_posts_cycle_through_times():
    x1 = _campaign(x_post="x1")
    x2 = _campaign(x_post="x2")
    x3 = _campaign(x_post="x3")
    result = distribute_schedule([x1, x2, x3], MONDAY)
    hours = [result[c.id].hour for c in [x1, x2, x3]]
    assert hours == [8, 12, 17]


def test_x_posts_cycle_wraps_after_17():
    posts = [_campaign(x_post=f"x{i}") for i in range(4)]
    result = distribute_schedule(posts, MONDAY)
    hours = [result[c.id].hour for c in posts]
    assert hours == [8, 12, 17, 8]


# ---------------------------------------------------------------------------
# Mon-Fri only when total <= 5
# ---------------------------------------------------------------------------

def test_five_posts_use_mon_fri_only():
    posts = [_campaign(x_post=f"x{i}") for i in range(5)]
    result = distribute_schedule(posts, MONDAY)
    weekdays = {result[c.id].weekday() for c in posts}
    assert max(weekdays) <= 4  # 0=Mon, 4=Fri, no Sat(5) or Sun(6)


def test_six_posts_include_weekend():
    posts = [_campaign(x_post=f"x{i}") for i in range(6)]
    result = distribute_schedule(posts, MONDAY)
    weekdays = {result[c.id].weekday() for c in posts}
    assert max(weekdays) >= 5  # Sat or Sun used


# ---------------------------------------------------------------------------
# Mixed platforms: platform ordering and deterministic assignment
# ---------------------------------------------------------------------------

def test_mixed_platforms_distributed_by_day():
    blog = _campaign(blog_html="<h1>Blog</h1>")
    li = _campaign(linkedin_post="LinkedIn post")
    x = _campaign(x_post="X post")
    result = distribute_schedule([blog, li, x], MONDAY)
    # All three should go on Monday (round 0)
    days = {result[c.id].date() for c in [blog, li, x]}
    assert len(days) == 1  # all on same day
    assert list(days)[0].weekday() == 0  # Monday


def test_platform_order_blog_first_then_linkedin_then_x():
    blog = _campaign(blog_html="<h1>B</h1>")
    li = _campaign(linkedin_post="L")
    x = _campaign(x_post="X")
    result = distribute_schedule([blog, li, x], MONDAY)
    # blog_full and linkedin both get 09:00; x gets 08:00
    assert result[blog.id].hour == 9
    assert result[li.id].hour == 9
    assert result[x.id].hour == 8


def test_multi_day_distribution():
    li1 = _campaign(linkedin_post="li1")
    li2 = _campaign(linkedin_post="li2")
    x1 = _campaign(x_post="x1")
    x2 = _campaign(x_post="x2")
    result = distribute_schedule([li1, li2, x1, x2], MONDAY)
    # Round 0: li1 -> Mon, x1 -> Mon
    # Round 1: li2 -> Tue, x2 -> Tue
    assert result[li1.id].weekday() == 0  # Mon
    assert result[li2.id].weekday() == 1  # Tue
    assert result[x1.id].weekday() == 0   # Mon
    assert result[x2.id].weekday() == 1   # Tue
    # X cycling: Mon=08:00, Tue=12:00
    assert result[x1.id].hour == 8
    assert result[x2.id].hour == 12


# ---------------------------------------------------------------------------
# Same-platform stagger on same day (second pass)
# ---------------------------------------------------------------------------

def test_same_platform_same_day_stagger():
    # 8 x posts but 7 days: post 8 wraps to day 0 (Mon) alongside post 1
    posts = [_campaign(x_post=f"x{i}") for i in range(8)]
    result = distribute_schedule(posts, MONDAY)
    # post 0 -> Mon 08:00; post 7 -> Mon again (08:00 + 3h = 11:00)
    assert result[posts[0].id].weekday() == 0
    assert result[posts[0].id].hour == 8
    assert result[posts[7].id].weekday() == 0
    assert result[posts[7].id].hour == 11  # 08:00 + 3h stagger


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_empty_campaigns_returns_empty_dict():
    result = distribute_schedule([], MONDAY)
    assert result == {}


# ---------------------------------------------------------------------------
# Week start date applied correctly
# ---------------------------------------------------------------------------

def test_week_start_date_shifts_all_days():
    next_week_monday = date(2026, 8, 3)
    x = _campaign(x_post="x")
    result = distribute_schedule([x], next_week_monday)
    assert result[x.id].date() == next_week_monday


# ---------------------------------------------------------------------------
# Determinism: same input always produces same output
# ---------------------------------------------------------------------------

def test_distribute_is_deterministic():
    posts = [_campaign(x_post=f"x{i}") for i in range(5)]
    r1 = distribute_schedule(posts, MONDAY)
    r2 = distribute_schedule(posts, MONDAY)
    for c in posts:
        assert r1[c.id] == r2[c.id]


# ---------------------------------------------------------------------------
# Platform classification for Meta lanes
# ---------------------------------------------------------------------------

def test_campaign_platform_classifies_instagram_and_facebook():
    ig = SimpleNamespace(blog_html=None, linkedin_post=None, instagram_caption="cap", facebook_post=None)
    fb = SimpleNamespace(blog_html=None, linkedin_post=None, instagram_caption=None, facebook_post="post")
    assert _campaign_platform(ig) == "instagram"
    assert _campaign_platform(fb) == "facebook"


# ---------------------------------------------------------------------------
# Meta lanes get their per-lane base hour (Instagram 11:00, Facebook 14:00)
# ---------------------------------------------------------------------------

def test_single_instagram_post_scheduled_at_1100():
    ig = _campaign(instagram_caption="cap")
    result = distribute_schedule([ig], MONDAY)
    assert result[ig.id] == datetime(MONDAY.year, MONDAY.month, MONDAY.day, 11, 0, 0)


def test_single_facebook_post_scheduled_at_1400():
    fb = _campaign(facebook_post="post")
    result = distribute_schedule([fb], MONDAY)
    assert result[fb.id] == datetime(MONDAY.year, MONDAY.month, MONDAY.day, 14, 0, 0)


def test_mixed_lanes_land_on_expected_hours_same_day():
    blog = _campaign(blog_html="<h1>t</h1>")
    li = _campaign(linkedin_post="li")
    ig = _campaign(instagram_caption="cap")
    fb = _campaign(facebook_post="post")
    x = _campaign(x_post="x")
    result = distribute_schedule([blog, li, ig, fb, x], MONDAY)
    # First round assigns one post per lane to Monday at its base hour (X cycles from 08:00).
    assert result[blog.id].hour == 9
    assert result[li.id].hour == 9
    assert result[ig.id].hour == 11
    assert result[fb.id].hour == 14
    assert result[x.id].hour == 8
    for c in (blog, li, ig, fb, x):
        assert result[c.id].date() == MONDAY


# ---------------------------------------------------------------------------
# Image assignment priority: Instagram wins scarce quota (I/O matrix)
# ---------------------------------------------------------------------------

def test_prioritize_image_targets_puts_instagram_first():
    blog_id, x_id, ig_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    campaign_ids = [blog_id, x_id, ig_id]  # Instagram generated last
    title_hints = ["Blog", "X post 1", "Instagram post 1"]
    instagram_targets = [(ig_id, "Instagram post 1")]

    queue = _prioritize_image_targets(campaign_ids, title_hints, instagram_targets)

    # Instagram is first despite being generated last; no duplicates; all present.
    assert queue[0] == (ig_id, "Instagram post 1")
    assert [cid for cid, _ in queue] == [ig_id, blog_id, x_id]


def test_prioritize_image_targets_no_instagram_keeps_order():
    blog_id, x_id = uuid.uuid4(), uuid.uuid4()
    queue = _prioritize_image_targets([blog_id, x_id], ["Blog", "X post 1"], [])
    assert [cid for cid, _ in queue] == [blog_id, x_id]
