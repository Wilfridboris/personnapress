# Deferred Work

## Deferred from: code review of 3-6-image-generation-quality (2026-07-08)

- Blog title with apostrophe/single-quote formats awkwardly inside wrapping quotes in `_build_image_prompt` (`backend/app/services/image.py:49`) — pre-existing in both old and new prompt formats
- No dimension validation for out-of-range width/height values passed to FLUX 1.1 Pro API (`backend/app/integrations/replicate.py`) — pre-existing, API will reject invalid values at runtime
- `brand_voice_profile` truthy check passes for non-dict types; `.get()` would raise AttributeError if DB returns a JSON scalar (`backend/app/services/image.py:33`) — pre-existing
- Empty/whitespace-only blog title edge case: H1 containing only HTML tags not covered by tests — pre-existing (caller has `or "Untitled"` fallback)
- `tone_list[:2]` on a non-list value (e.g. comma-separated string from DB) returns characters not tones (`backend/app/services/image.py:43`) — pre-existing
- `_build_image_prompt` tested via direct private import rather than through the public service API surface (`backend/tests/services/test_image.py`) — pre-existing test pattern
