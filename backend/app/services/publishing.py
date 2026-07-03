"""
Publishing service — the ONLY place that calls decrypt_credential().
Dispatches publish tasks to each connected platform integration.
"""

import asyncio
import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_credential
from app.core.exceptions import PlatformError
from app.db.repositories.campaigns import get_campaign
from app.db.repositories.platform_connections import get_connection_for_platform, get_connections_for_client
from app.integrations import linkedin as linkedin_integration
from app.integrations import twitter as twitter_integration
from app.integrations import webflow as webflow_integration
from app.integrations import wordpress as wordpress_integration

logger = logging.getLogger(__name__)


async def dispatch_publish_for_platform(
    db: AsyncSession,
    campaign_id: UUID,
    platform: str,
) -> dict:
    """
    Retry publishing for a single platform.
    Returns per-platform result dict with "success" or a formatted error string.
    ONLY this function (and dispatch_publish) may call decrypt_credential().
    """
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        return {platform: f"campaign {campaign_id} not found"}
    connection = await get_connection_for_platform(db, campaign.client_id, platform)
    if not connection:
        return {platform: "no platform connection found"}
    try:
        creds_json = decrypt_credential(connection.encrypted_credentials)
        creds = json.loads(creds_json)
        if platform == "wordpress":
            await wordpress_integration.publish_post(creds, campaign)
        elif platform == "webflow":
            await webflow_integration.publish_post(creds, campaign)
        elif platform == "x":
            await twitter_integration.create_tweet(creds["access_token"], campaign.x_post or "")
        elif platform == "linkedin":
            await linkedin_integration.create_ugc_post(
                creds["access_token"],
                campaign.blog_html or "",
                campaign.linkedin_post or "",
            )
        return {platform: "success"}
    except PlatformError as pe:
        error_msg = f"{pe.platform.capitalize()} returned {pe.status_code} — {pe.message}"
        logger.error(
            "Retry publish failed platform=%s campaign=%s: %s",
            platform,
            campaign_id,
            error_msg,
        )
        return {platform: error_msg}
    except Exception as exc:
        logger.error(
            "Retry publish failed platform=%s campaign=%s: %s",
            platform,
            campaign_id,
            exc,
            exc_info=True,
        )
        return {platform: f"Unexpected error — {str(exc)[:100]}"}


async def dispatch_publish(db: AsyncSession, campaign_id: UUID, job_id: UUID) -> dict:
    """
    Publish to all connected platforms. Returns per-platform results dict.
    ONLY this function may call decrypt_credential().
    Decrypted credentials never leave this function's scope and are never logged.
    """
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        logger.error("dispatch_publish: campaign %s not found", campaign_id)
        return {"error": f"campaign {campaign_id} not found"}
    connections = await get_connections_for_client(db, campaign.client_id)
    results: dict[str, str] = {}
    last_x_publish_time = 0.0
    last_linkedin_publish_time = 0.0

    for conn in connections:
        platform = conn.platform if isinstance(conn.platform, str) else conn.platform.value
        try:
            creds_json = decrypt_credential(conn.encrypted_credentials)
            creds = json.loads(creds_json)

            if platform == "wordpress":
                await wordpress_integration.publish_post(creds, campaign)

            elif platform == "webflow":
                await webflow_integration.publish_post(creds, campaign)

            elif platform == "x":
                now = asyncio.get_running_loop().time()
                if last_x_publish_time and now - last_x_publish_time < 2.0:
                    await asyncio.sleep(2.0 - (now - last_x_publish_time))
                await twitter_integration.create_tweet(
                    creds["access_token"], campaign.x_post or ""
                )
                last_x_publish_time = asyncio.get_running_loop().time()

            elif platform == "linkedin":
                now = asyncio.get_running_loop().time()
                if last_linkedin_publish_time and now - last_linkedin_publish_time < 5.0:
                    await asyncio.sleep(5.0 - (now - last_linkedin_publish_time))
                await linkedin_integration.create_ugc_post(
                    creds["access_token"],
                    campaign.blog_html or "",
                    campaign.linkedin_post or "",
                )
                last_linkedin_publish_time = asyncio.get_running_loop().time()

            results[platform] = "success"

        except Exception as exc:
            logger.error(
                "Publish failed for platform=%s campaign=%s: %s",
                platform,
                campaign_id,
                exc,
                exc_info=True,
            )
            results[platform] = str(exc)

    return results
