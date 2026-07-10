import base64
import re
import time

from bs4 import BeautifulSoup

import httpx
import jwt
from markdownify import markdownify as _md

from app.core.config import settings
from app.core.exceptions import PlatformError

_GITHUB_API_VERSION = "2026-03-10"

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": _GITHUB_API_VERSION,
}


def slug_from_title(title: str) -> str:
    """Convert a post title to a URL-safe slug (max 60 chars)."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].rstrip("-") or "untitled"


def html_to_markdown(html: str) -> str:
    """Convert blog HTML to Markdown with H1 stripped from body."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        h1.decompose()
    clean_html = str(soup)
    return _md(clean_html, heading_style="ATX", newline_style="backslash").strip()


def generate_app_jwt() -> str:
    """Sign a short-lived JWT for GitHub App authentication (RS256, 9-minute validity)."""
    if not settings.GITHUB_APP_PRIVATE_KEY:
        raise PlatformError("github", 0, "GITHUB_APP_PRIVATE_KEY is not configured")
    now = int(time.time())
    payload = {
        "iss": settings.GITHUB_APP_CLIENT_ID,
        "iat": now - 60,   # 60 s in past to tolerate clock skew (GitHub requirement)
        "exp": now + 540,  # 9 minutes (max is 10)
    }
    private_key = settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: str) -> dict:
    """Exchange installation ID for a short-lived token. Returns {"token": ..., "expires_at": ...}."""
    app_jwt = generate_app_jwt()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {app_jwt}"},
        )
    if resp.status_code != 201:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    data = resp.json()
    token = data.get("token")
    expires_at = data.get("expires_at")
    if not token or not expires_at:
        raise PlatformError("github", 201, "Missing token or expires_at in GitHub response")
    return {"token": token, "expires_at": expires_at}


async def get_installation_repositories(installation_token: str) -> list[dict]:
    """List repositories accessible to the installation. Returns list of {full_name, private}."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.github.com/installation/repositories",
            params={"per_page": 100},
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    return [
        {"full_name": r["full_name"], "private": r["private"]}
        for r in resp.json().get("repositories", [])
    ]


async def get_repo_root_contents(installation_token: str, repo_full_name: str) -> list[dict]:
    """Fetch root-level file listing. Returns list of {name, type, path} dicts."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, "contents API error")
    data = resp.json()
    if not isinstance(data, list):
        return []
    return [{"name": item.get("name", ""), "type": item.get("type", "file"), "path": item.get("path", "")} for item in data if item.get("name")]


async def get_directory_contents(installation_token: str, repo_full_name: str, path: str) -> list[dict]:
    """Fetch directory listing. Returns [] if path doesn't exist (404) or is not a directory."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{path}",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, "contents API error")
    data = resp.json()
    return data if isinstance(data, list) else []


async def get_file_contents(installation_token: str, repo_full_name: str, file_path: str) -> str | None:
    """Return decoded file content or None if the file does not exist (404)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    data = resp.json()
    encoded = data.get("content", "")
    return base64.b64decode(encoded.replace("\n", "")).decode("utf-8", errors="replace")


async def get_default_branch(installation_token: str, repo_full_name: str) -> str:
    """Return the repository default branch name."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    return resp.json().get("default_branch", "main")


async def list_files_in_directory(
    installation_token: str,
    repo_full_name: str,
    path: str,
    extension: str | None = None,
) -> list[str]:
    """Return file names in a directory, optionally filtered by extension. Returns [] on 404."""
    items = await get_directory_contents(installation_token, repo_full_name, path)
    names = [
        item.get("name", "")
        for item in items
        if item.get("type") == "file" and item.get("name")
    ]
    if extension:
        names = [n for n in names if n.endswith(extension)]
    return names


async def get_first_post_files(
    installation_token: str,
    repo_full_name: str,
    path: str,
    max: int = 3,
) -> list[str]:
    """Return decoded content of up to `max` files from the given directory."""
    items = await get_directory_contents(installation_token, repo_full_name, path)
    file_paths = [
        item.get("path", "")
        for item in items
        if item.get("type") == "file" and item.get("path")
    ][:max]
    contents = []
    for fp in file_paths:
        content = await get_file_contents(installation_token, repo_full_name, fp)
        if content is not None:
            contents.append(content)
    return contents


def detect_front_matter_format(content: str) -> str:
    """Return 'toml' if front matter starts with +++, else 'yaml'."""
    if content.lstrip().startswith("+++"):
        return "toml"
    return "yaml"


async def get_branch_sha(installation_token: str, repo: str, branch: str) -> str:
    """Return the SHA of the branch tip."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
        )
    if resp.status_code != 200:
        raise PlatformError("github", resp.status_code, resp.text[:300])
    sha = resp.json().get("object", {}).get("sha")
    if not sha:
        raise PlatformError("github", 200, "Branch SHA missing from GitHub response")
    return sha


async def create_branch(installation_token: str, repo: str, branch_name: str, from_sha: str) -> None:
    """Create a new branch from the given commit SHA. Idempotent — no-ops if branch already exists."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/git/refs",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
            json={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
        )
    if resp.status_code == 422 and "already exists" in resp.text:
        return
    if resp.status_code not in (200, 201):
        raise PlatformError("github", resp.status_code, resp.text[:300])


async def create_pull_request(
    installation_token: str,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
) -> str:
    """Create a PR and return its html_url."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/pulls",
            headers={**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"},
            json={"title": title, "head": head, "base": base, "body": body},
        )
    if resp.status_code not in (200, 201):
        raise PlatformError("github", resp.status_code, resp.text[:300])
    html_url = resp.json().get("html_url")
    if not html_url:
        raise PlatformError("github", resp.status_code, "PR html_url missing from GitHub response")
    return html_url


async def create_file_commit(
    installation_token: str,
    repo_full_name: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str = "HEAD",
) -> str:
    """Create or update a file via the GitHub Contents API. Returns the 7-char short commit SHA."""
    headers = {**GITHUB_HEADERS, "Authorization": f"Bearer {installation_token}"}
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

    body: dict = {
        "message": commit_message,
        "content": encoded_content,
    }
    if branch != "HEAD":
        body["branch"] = branch

    # Check if file exists to get its SHA (required for updates)
    async with httpx.AsyncClient(timeout=15.0) as client:
        check_resp = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
            headers=headers,
        )
        if check_resp.status_code == 200:
            existing_sha = check_resp.json().get("sha")
            if existing_sha:
                body["sha"] = existing_sha
        elif check_resp.status_code != 404:
            raise PlatformError("github", check_resp.status_code, check_resp.text[:300])

        resp = await client.put(
            f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}",
            headers=headers,
            json=body,
        )

    if resp.status_code not in (200, 201):
        raise PlatformError("github", resp.status_code, resp.text[:300])

    commit_sha = resp.json().get("commit", {}).get("sha", "")
    return commit_sha[:7] if commit_sha else ""
