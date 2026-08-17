---
title: 'Fix: Scheduled Publish Jobs Lost on Server Restart'
type: 'bugfix'
created: '2026-08-17'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** Scheduled publish jobs silently disappear when the backend is restarted (e.g., deployed) within 1 second after the scheduled time passes. APScheduler's default `misfire_grace_time` is 1 second; any restart longer than that causes the recovered job to be silently dropped, so the campaign stays stuck as "Scheduled" and is never published.

**Approach:** Add `misfire_grace_time=3600` to the `scheduler.add_job` calls for `run_publish` in the schedule endpoint and the reschedule fallback — matching the pattern already used on the headless schedule endpoint.

## Suggested Review Order

- [`backend/app/routers/publishing.py:1469`](../../backend/app/routers/publishing.py) — schedule endpoint `add_job` (misfire fix applied)
- [`backend/app/routers/publishing.py:1589`](../../backend/app/routers/publishing.py) — reschedule fallback `add_job` (misfire fix applied)
- [`backend/app/routers/publishing.py:1779`](../../backend/app/routers/publishing.py) — headless schedule `add_job` (already had grace time; confirms the pattern)
- [`backend/app/scheduler/scheduler.py`](../../backend/app/scheduler/scheduler.py) — scheduler timezone="UTC"; no global misfire default set
- [`backend/app/workers/publish.py:114`](../../backend/app/workers/publish.py) — `run_publish` signature (args received as strings from APScheduler)

## Spec Change Log

