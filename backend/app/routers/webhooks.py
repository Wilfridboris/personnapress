import hashlib
import hmac
import json
import logging

import stripe as stripe_sdk
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.connection import get_session
from app.db.repositories.campaigns import update_campaign_status
from app.db.repositories.models import Campaign
from app.services.subscription_service import handle_stripe_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)

# Ensure stripe_client initializes the SDK key
import app.integrations.stripe_client  # noqa: F401


def _verify_github_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_sdk.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe_sdk.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as exc:
        logger.error("Webhook processing error: %s", exc)
        raise HTTPException(status_code=400, detail="Webhook processing failed")

    await handle_stripe_webhook(dict(event), db)
    return {"received": True}


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("x-hub-signature-256", "")
    event_type = request.headers.get("x-github-event", "")

    secret = settings.GITHUB_APP_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="GitHub webhook secret not configured")
    if not _verify_github_signature(payload, sig_header, secret):
        raise HTTPException(status_code=400, detail="Invalid GitHub signature")

    if event_type != "pull_request":
        return {"received": True}

    try:
        body = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = body.get("action")
    merged = body.get("pull_request", {}).get("merged", False)
    if action != "closed" or not merged:
        return {"received": True}

    pr_html_url = body.get("pull_request", {}).get("html_url", "")
    if not pr_html_url:
        return {"received": True}

    result = await db.execute(
        select(Campaign).where(Campaign.github_pr_url == pr_html_url)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        return {"received": True}

    if campaign.status == "approved":
        await update_campaign_status(db, campaign.id, "published")
        await db.commit()
        logger.info("Campaign %s published via GitHub PR merge: %s", campaign.id, pr_html_url)

    return {"received": True}
