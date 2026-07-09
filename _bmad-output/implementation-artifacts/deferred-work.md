# Deferred Work

## Deferred from: deploy.sh status/log fix (2026-07-08)

- `systemctl is-active` validates systemd process state only, not application-level readiness (e.g., HTTP server fully bound). If the service type is `oneshot` or startup is async, the check may pass before traffic can be served — `deploy.sh:32`.
- `git pull origin main` has no non-fast-forward protection: if main was force-pushed, the pull fails mid-deploy leaving new pip deps installed but migration not run — pre-existing in `deploy.sh`.
- No rollback on `alembic upgrade head` failure: failed migration leaves the DB in a partially upgraded state with no automated revert — pre-existing in `deploy.sh`.

## Deferred from: code review of 3-7-seo-aware-content-generation (2026-07-09)

- `tone_score`/`cadence_score`/`jargon_violations` in `check_fidelity()` accept floats (not strictly int) — only the new `seo_h2_count` field enforces strict int; pre-existing validation gap in `backend/app/integrations/gemini.py`
- `_FIDELITY_PROMPT` asks Gemini to count `<h2>` tags in the blog HTML — LLMs are unreliable HTML parsers; deterministic counting from the actual HTML (already done in `generate_blog`) would be more accurate; pre-existing design decision in `backend/app/integrations/gemini.py`

## Deferred from: code review of 3-6-image-generation-quality (2026-07-08)

- Blog title with apostrophe/single-quote formats awkwardly inside wrapping quotes in `_build_image_prompt` (`backend/app/services/image.py:49`) — pre-existing in both old and new prompt formats
- No dimension validation for out-of-range width/height values passed to FLUX 1.1 Pro API (`backend/app/integrations/replicate.py`) — pre-existing, API will reject invalid values at runtime
- `brand_voice_profile` truthy check passes for non-dict types; `.get()` would raise AttributeError if DB returns a JSON scalar (`backend/app/services/image.py:33`) — pre-existing
- Empty/whitespace-only blog title edge case: H1 containing only HTML tags not covered by tests — pre-existing (caller has `or "Untitled"` fallback)
- `tone_list[:2]` on a non-list value (e.g. comma-separated string from DB) returns characters not tones (`backend/app/services/image.py:43`) — pre-existing
- `_build_image_prompt` tested via direct private import rather than through the public service API surface (`backend/tests/services/test_image.py`) — pre-existing test pattern
