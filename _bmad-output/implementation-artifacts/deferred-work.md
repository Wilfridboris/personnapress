# Deferred Work

## Deferred from: code review of 2-6-voice-profile-refresh (2026-07-01)

- **D1 (Low)**: No recovery path from stuck in-progress state when `client.brand_voice_profile` is null after `router.refresh()` resolves — possible if read replica lags or model serialization error. Needs timeout/fallback transition to `"failed"` state.
- **D2 (Medium)**: No rate-limiting or quota guard on `POST /clients/{id}/ingest` — authenticated owner can spam the endpoint creating unbounded job records. Architectural concern; address at infra or middleware layer.
