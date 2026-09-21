---
title: 'Switch default image model to Nano Banana 2'
type: 'chore'
created: '2026-09-20'
status: 'done'
route: 'one-shot'
---

# Switch default image model to Nano Banana 2

## Intent

**Problem:** Image generation defaulted to `google/nano-banana-pro` (Gemini 3 Pro Image), the premium high-cost model, driving up per-image spend.

**Approach:** Switch the default `IMAGE_MODEL` to `google/nano-banana-2` (Gemini 3.1 Flash Image), a cheaper Flash-tier Replicate model. Its Replicate input schema is identical to Nano Banana Pro (`prompt`, `aspect_ratio: "1:1"`, `output_format: "png"`), so it flows through the existing non-FLUX branch in `replicate.py` with no integration code change. Verified against Replicate's model schema. Cost per image drops from roughly $0.12-$0.15 (Pro tier) to ~$0.04 or less (Flash tier).

## Suggested Review Order

- Default model change - the single line that flips the shipped default.
  [`config.py:40`](../../backend/app/core/config.py#L40)

- The non-FLUX call branch that Nano Banana 2 routes through; payload unchanged and schema-verified.
  [`replicate.py:53`](../../backend/app/integrations/replicate.py#L53)

- Parametrized test now asserts nano-banana-2 uses the 1:1 non-FLUX payload.
  [`test_replicate.py:23`](../../backend/tests/integrations/test_replicate.py#L23)

- Example + runtime env documentation of the new default and the cost/quality tradeoff.
  [`.env.example:56`](../../backend/.env.example#L56)
