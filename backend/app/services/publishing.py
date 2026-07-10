"""
Publishing service — the ONLY place that calls decrypt_credential().
Dispatches publish tasks to each connected platform integration.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_credential, encrypt_credential
from app.core.exceptions import PlatformError
from app.db.repositories.campaigns import get_campaign
from app.db.repositories.platform_connections import get_connection_for_platform, get_connections_for_client, upsert_connection
from bs4 import BeautifulSoup
from app.integrations import github as github_integration
from app.integrations import linkedin as linkedin_integration
from app.integrations import twitter as twitter_integration
from app.integrations import webflow as webflow_integration
from app.integrations import wordpress as wordpress_integration
from app.integrations import wordpress_com as wordpress_com_integration

logger = logging.getLogger(__name__)


async def _refresh_token_if_needed(cred: dict, db: AsyncSession, client_id: UUID) -> dict:
    """Refresh the GitHub installation token if within 5 minutes of expiry."""
    expires_at = cred.get("expires_at", "")
    needs_refresh = True
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            needs_refresh = datetime.now(timezone.utc) >= expiry - timedelta(minutes=5)
        except ValueError:
            pass
    if needs_refresh:
        installation_id = cred.get("installation_id")
        if not installation_id:
            raise PlatformError("github", 0, "GitHub connection missing installation_id")
        token_data = await github_integration.get_installation_token(installation_id)
        cred["installation_token"] = token_data["token"]
        cred["expires_at"] = token_data["expires_at"]
        encrypted = encrypt_credential(json.dumps(cred))
        await upsert_connection(db, client_id, "github_pages", encrypted)
    return cred


async def _publish_github(campaign, cred: dict, db: AsyncSession) -> dict:
    """Publish campaign blog post to a Jekyll or plain-static GitHub Pages repo."""
    # Refresh token if needed (token must not outlive this function)
    cred = await _refresh_token_if_needed(cred, db, campaign.client_id)
    installation_token: str = cred["installation_token"]

    repo_full_name: str = cred.get("repo_full_name", "")
    if not repo_full_name:
        raise PlatformError("github", 0, "No repository selected")

    detected_framework: str = cred.get("detected_framework", "")
    publish_path: str = cred.get("publish_path", "")

    blog_html: str = campaign.blog_html or ""

    # Extract title from H1
    soup = BeautifulSoup(blog_html, "html.parser")
    h1_tag = soup.find("h1")
    title: str = h1_tag.get_text(strip=True) if h1_tag else "Untitled"
    slug: str = github_integration.slug_from_title(title)
    now_utc = datetime.now(timezone.utc)
    today: str = now_utc.strftime("%Y-%m-%d")
    publish_datetime: str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    if detected_framework == "jekyll":
        body_md = github_integration.html_to_markdown(blog_html)

        # Build categories from voice_score tags
        categories_line = ""
        if campaign.voice_score and campaign.voice_score.get("tags"):
            tags = campaign.voice_score["tags"]
            if isinstance(tags, list) and tags:
                categories_value = ", ".join(f'"{t.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"' for t in tags)
                categories_line = f"categories: [{categories_value}]\n"

        # meta description from voice_score or empty
        description = ""
        if campaign.voice_score:
            description = campaign.voice_score.get("meta_description", "") or ""

        title_yaml = title.replace("\\", "\\\\").replace('"', '\\"')
        description_yaml = description.replace("\\", "\\\\").replace('"', '\\"')

        front_matter = (
            "---\n"
            f"layout: post\n"
            f"title: \"{title_yaml}\"\n"
            f"date: {publish_datetime}\n"
            f"description: \"{description_yaml}\"\n"
            f"{categories_line}"
            "---\n\n"
        )
        file_content = front_matter + body_md
        file_path = f"_posts/{today}-{slug}.md"
        commit_message = f"Add blog post: {title}"

    elif detected_framework == "plain_static":
        # Detect existing stylesheet from index.html
        style_link = ""
        index_html = await github_integration.get_file_contents(installation_token, repo_full_name, "index.html")
        if index_html:
            idx_soup = BeautifulSoup(index_html, "html.parser")
            link_tag = idx_soup.find("link", rel=lambda r: r and "stylesheet" in r)
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                style_link = f'  <link rel="stylesheet" href="{href}">\n'

        safe_body = str(soup)
        html5_shell = (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"  <title>{title}</title>\n"
            f"{style_link}"
            "</head>\n"
            "<body>\n"
            f"{safe_body}\n"
            "</body>\n"
            "</html>\n"
        )

        # Determine publish path
        if not publish_path:
            root_items = await github_integration.get_repo_root_contents(installation_token, repo_full_name)
            root_names = {item["name"] for item in root_items}
            publish_path = "docs/" if "docs" in root_names else ""

        base = publish_path.rstrip("/")
        file_path = f"{base}/{slug}.html" if base else f"{slug}.html"
        commit_message = f"Add blog post: {title}"

        # Create .nojekyll at repo root if it doesn't exist
        nojekyll = await github_integration.get_file_contents(installation_token, repo_full_name, ".nojekyll")
        if nojekyll is None:
            await github_integration.create_file_commit(
                installation_token, repo_full_name, ".nojekyll", "", "Add .nojekyll"
            )

        file_content = html5_shell

    else:
        raise PlatformError("github", 0, f"Unsupported framework for GitHub publish: {detected_framework}")

    commit_sha = await github_integration.create_file_commit(
        installation_token, repo_full_name, file_path, file_content, commit_message
    )

    # Set github_pr_url to None for direct commit (PR url used by Story 8.7)
    campaign.github_pr_url = None
    db.add(campaign)

    return {"status": "success", "commit_sha": commit_sha}


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
        elif platform == "wordpress-com":
            await wordpress_com_integration.publish_post(creds, campaign)
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
        elif platform == "github_pages":
            await _publish_github(campaign, creds, db)
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
    # If both self-hosted and WordPress.com connections exist, prefer self-hosted (mirrors UI precedence)
    platform_names = {(c.platform if isinstance(c.platform, str) else c.platform.value) for c in connections}
    if "wordpress" in platform_names and "wordpress-com" in platform_names:
        connections = [c for c in connections if (c.platform if isinstance(c.platform, str) else c.platform.value) != "wordpress-com"]
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

            elif platform == "wordpress-com":
                await wordpress_com_integration.publish_post(creds, campaign)

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

            elif platform == "github_pages":
                await _publish_github(campaign, creds, db)

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
