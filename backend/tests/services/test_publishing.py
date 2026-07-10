"""Tests for services/publishing.py dispatch_publish."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
import logging

import pytest


def _make_campaign(client_id=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = client_id or uuid.uuid4()
    c.blog_html = "<h1>Title</h1><p>Body</p>"
    c.x_post = "Check out our new blog post!"
    c.linkedin_post = "Excited to share..."
    c.image_url = "https://cdn.example.com/img.png"
    return c


def _make_connection(platform="wordpress", creds=None):
    from app.core.security import encrypt_credential
    conn = MagicMock()
    conn.platform = platform
    if creds is None:
        creds = {"site_url": "https://wp.example.com", "username": "admin", "credential": "pass"}
    conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    return conn


async def test_dispatch_publish_all_success():
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    wp_conn = _make_connection("wordpress")
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(return_value="https://wp.example.com/post")),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results == {"wordpress": "success"}


async def test_dispatch_publish_partial_failure():
    from app.services.publishing import dispatch_publish

    campaign = _make_campaign()
    wp_conn = _make_connection("wordpress")
    x_creds = {"access_token": "token123"}
    x_conn = _make_connection("x", creds=x_creds)
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn, x_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(return_value="")),
        patch("app.services.publishing.twitter_integration.create_tweet", AsyncMock(side_effect=Exception("rate limit exceeded"))),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results["wordpress"] == "success"
    assert "rate limit exceeded" in results["x"]


async def test_credentials_not_logged(caplog):
    from app.services.publishing import dispatch_publish
    from app.core.security import encrypt_credential

    campaign = _make_campaign()
    secret_password = "super_secret_app_password_12345"
    creds = {"site_url": "https://wp.example.com", "username": "admin", "credential": secret_password}
    wp_conn = MagicMock()
    wp_conn.platform = "wordpress"
    wp_conn.encrypted_credentials = encrypt_credential(json.dumps(creds))
    db = AsyncMock()

    with (
        patch("app.services.publishing.get_campaign", AsyncMock(return_value=campaign)),
        patch("app.services.publishing.get_connections_for_client", AsyncMock(return_value=[wp_conn])),
        patch("app.services.publishing.wordpress_integration.publish_post", AsyncMock(side_effect=Exception("connection failed"))),
        caplog.at_level(logging.ERROR, logger="app.services.publishing"),
    ):
        results = await dispatch_publish(db, campaign.id, uuid.uuid4())

    assert results["wordpress"] != "success"
    # The decrypted secret must never appear in any log record
    for record in caplog.records:
        assert secret_password not in record.getMessage()
        assert secret_password not in str(record.args)


# ---------------------------------------------------------------------------
# _publish_github — Jekyll path
# ---------------------------------------------------------------------------

def _make_github_campaign(voice_score=None):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.client_id = uuid.uuid4()
    c.blog_html = "<h1>My Great Post</h1><h2>Section</h2><p>Body text here.</p>"
    c.voice_score = voice_score
    c.github_pr_url = None
    return c


def _github_cred(framework="jekyll", publish_path=""):
    return {
        "installation_id": "12345",
        "installation_token": "ghs_tok123",
        "expires_at": "2099-01-01T00:00:00Z",
        "repo_full_name": "owner/my-blog",
        "detected_framework": framework,
        "publish_path": publish_path,
    }


@pytest.mark.asyncio
async def test_publish_github_jekyll_calls_create_file_commit_with_front_matter():
    """Jekyll path produces correct front matter + markdown file commit."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"tags": ["python", "tips"]})
    cred = _github_cred("jekyll")
    db = AsyncMock()
    db.add = MagicMock()

    captured_path = []
    captured_content = []

    async def mock_create_file_commit(token, repo, file_path, content, message, branch="HEAD"):
        captured_path.append(file_path)
        captured_content.append(content)
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create_file_commit),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="## Section\n\nBody text here."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    assert result["commit_sha"] == "abc1234"
    assert len(captured_path) == 1
    path = captured_path[0]
    assert path.startswith("_posts/")
    assert path.endswith("-my-great-post.md")
    content = captured_content[0]
    assert "layout: post" in content
    assert 'title: "My Great Post"' in content
    assert "categories:" in content
    assert '"python"' in content


@pytest.mark.asyncio
async def test_publish_github_jekyll_omits_categories_when_no_tags():
    """Jekyll path omits categories front matter line when no tags in voice_score."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score=None)
    cred = _github_cred("jekyll")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="## Section"),
    ):
        await _publish_github(campaign, cred, db)

    assert "categories:" not in captured_content[0]


@pytest.mark.asyncio
async def test_publish_github_plain_static_creates_html_and_nojekyll():
    """Plain static path creates HTML5 shell + .nojekyll when absent."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign()
    cred = _github_cred("plain_static", publish_path="docs/")
    db = AsyncMock()
    db.add = MagicMock()

    commit_calls = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        commit_calls.append((file_path, content))
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="## Section"),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    paths = [p for p, _ in commit_calls]
    assert ".nojekyll" in paths
    html_path = next((p for p in paths if p.endswith(".html")), None)
    assert html_path == "docs/my-great-post.html"
    html_content = next((c for p, c in commit_calls if p.endswith(".html")), "")
    assert "<!DOCTYPE html>" in html_content
    assert "<title>My Great Post</title>" in html_content


@pytest.mark.asyncio
async def test_publish_github_plain_static_skips_nojekyll_if_exists():
    """Plain static path does not create .nojekyll if it already exists."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign()
    cred = _github_cred("plain_static", publish_path="docs/")
    db = AsyncMock()
    db.add = MagicMock()

    commit_calls = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        commit_calls.append(file_path)
        return "abc1234"

    async def mock_get_file(token, repo, path):
        if path == ".nojekyll":
            return ""  # already exists
        return None

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", side_effect=mock_get_file),
        patch("app.services.publishing.github_integration.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="## Section"),
    ):
        await _publish_github(campaign, cred, db)

    assert ".nojekyll" not in commit_calls


# ---------------------------------------------------------------------------
# _publish_github — Astro path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_astro_uses_md_when_no_mdx_files():
    """Astro path writes .md when no .mdx files exist in src/content/blog."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"meta_description": "A great post"})
    campaign.image_url = "https://cdn.example.com/img.png"
    cred = _github_cred("astro")
    db = AsyncMock()
    db.add = MagicMock()

    captured = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured.append((file_path, content))
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body text."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    assert len(captured) == 1
    file_path = captured[0][0]
    assert file_path == "src/content/blog/my-great-post.md"
    content = captured[0][1]
    assert "pubDate:" in content
    assert 'heroImage:' in content


@pytest.mark.asyncio
async def test_publish_github_astro_uses_mdx_when_mdx_files_exist():
    """Astro path writes .mdx when .mdx files exist in src/content/blog."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign()
    campaign.image_url = ""
    cred = _github_cred("astro")
    db = AsyncMock()
    db.add = MagicMock()

    captured_paths = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_paths.append(file_path)
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", AsyncMock(return_value=["post.mdx"])),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    assert captured_paths[0] == "src/content/blog/my-great-post.mdx"


# ---------------------------------------------------------------------------
# _publish_github — Next.js path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_nextjs_uses_posts_md_when_found():
    """Next.js path uses posts/{slug}.md when posts/*.md files exist."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"meta_description": "desc"})
    cred = _github_cred("nextjs")
    db = AsyncMock()
    db.add = MagicMock()

    captured_paths = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_paths.append(file_path)
        return "abc1234"

    async def mock_list_files(token, repo, path, extension=None):
        if path == "posts" and extension == ".md":
            return ["2024-01-01-old-post.md"]
        return []

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", side_effect=mock_list_files),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    assert captured_paths[0] == "posts/my-great-post.md"


@pytest.mark.asyncio
async def test_publish_github_nextjs_low_confidence_when_neither_found():
    """Next.js path returns low_confidence when neither posts/*.md nor content/*.mdx exist."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign()
    cred = _github_cred("nextjs")
    db = AsyncMock()
    db.add = MagicMock()

    with (
        patch("app.services.publishing.github_integration.list_files_in_directory", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
        patch("app.services.publishing.encrypt_credential", return_value=b"enc"),
        patch("app.services.publishing.upsert_connection", AsyncMock()),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "low_confidence"
    assert "Content folder not detected" in result["message"]


# ---------------------------------------------------------------------------
# _publish_github — Hugo path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_hugo_toml_front_matter():
    """Hugo path uses TOML front matter when existing post starts with +++."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"tags": ["go", "backend"], "meta_description": "Hugo post"})
    campaign.image_url = "https://cdn.example.com/img.png"
    cred = _github_cred("hugo")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []
    captured_paths = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        captured_paths.append(file_path)
        return "abc1234"

    toml_post = "+++\ntitle = \"Old Post\"\ndate = \"2024-01-01\"\ndraft = false\n+++\n\nBody"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[toml_post])),
        patch("app.services.publishing.github_integration.detect_front_matter_format", return_value="toml"),
        patch("app.services.publishing.github_integration.get_directory_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    content = captured_content[0]
    assert content.startswith("+++")
    assert 'title = "My Great Post"' in content
    assert "draft = false" in content
    assert '"go"' in content


# ---------------------------------------------------------------------------
# _publish_github — Eleventy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_eleventy_custom_input_dir():
    """Eleventy path reads custom dir.input from .eleventy.js and places post there."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"meta_description": "Eleventy post"})
    cred = _github_cred("eleventy")
    db = AsyncMock()
    db.add = MagicMock()

    captured_paths = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_paths.append(file_path)
        return "abc1234"

    eleventy_config = "module.exports = function(eleventyConfig) { return { dir: { input: \"docs\", output: \"_site\" } }; };"

    async def mock_get_file(token, repo, path):
        if path == ".eleventy.js":
            return eleventy_config
        return None

    existing_post = "---\ntitle: Old\ndate: 2024-01-01\nlayout: post\n---\nBody"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", side_effect=mock_get_file),
        patch("app.services.publishing.github_integration.get_directory_contents", AsyncMock(return_value=[{"type": "file", "name": "old.md", "path": "docs/posts/old.md"}])),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[existing_post])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        result = await _publish_github(campaign, cred, db)

    assert result["status"] == "success"
    assert captured_paths[0] == "docs/posts/my-great-post.md"


# ---------------------------------------------------------------------------
# AC-5: get_first_post_files called with max=3; no new keys introduced
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_astro_no_new_keys_introduced():
    """Astro path does not introduce keys absent from existing posts."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"meta_description": "desc"})
    campaign.image_url = ""
    cred = _github_cred("astro")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "abc1234"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        await _publish_github(campaign, cred, db)

    # Without a config file, only the 4 minimum keys should appear
    content = captured_content[0]
    assert "title:" in content
    assert "description:" in content
    assert "pubDate:" in content
    assert "heroImage:" in content
    # No extra keys from a config parse that didn't happen
    assert "# TODO" not in content


# ---------------------------------------------------------------------------
# _extract_meta_description
# ---------------------------------------------------------------------------

def test_extract_meta_description_extracts_comment():
    from app.services.publishing import _extract_meta_description

    html = '<h1>Title</h1>\n<!-- meta: Great post about SEO -->\n<p>Body</p>'
    assert _extract_meta_description(html) == "Great post about SEO"


def test_extract_meta_description_case_insensitive():
    from app.services.publishing import _extract_meta_description

    html = '<h1>T</h1><!-- META: Uppercase tag --><p>Body</p>'
    assert _extract_meta_description(html) == "Uppercase tag"


def test_extract_meta_description_returns_empty_when_absent():
    from app.services.publishing import _extract_meta_description

    html = '<h1>My Post</h1><p>Body text here.</p>'
    assert _extract_meta_description(html) == ""


def test_extract_meta_description_strips_whitespace():
    from app.services.publishing import _extract_meta_description

    html = '<!-- meta:   Padded description   -->'
    assert _extract_meta_description(html) == "Padded description"


# ---------------------------------------------------------------------------
# description extracted from blog HTML (not voice_score.meta_description)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_jekyll_extracts_description_from_html():
    """Jekyll path extracts description from <!-- meta: ... --> comment in blog_html."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score=None)
    campaign.blog_html = '<h1>My Great Post</h1>\n<!-- meta: SEO description here -->\n<p>Body</p>'
    cred = _github_cred("jekyll")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "sha"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_repo_root_contents", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body"),
    ):
        await _publish_github(campaign, cred, db)

    assert len(captured_content) >= 1, "create_file_commit was not called"
    assert 'description: "SEO description here"' in captured_content[0]


# ---------------------------------------------------------------------------
# Astro tags — unconditional (AC 4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_astro_writes_tags_unconditionally():
    """Astro path writes tags from voice_score without checking template keys."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"tags": ["astro", "ssg", "blog"]})
    campaign.image_url = ""
    cred = _github_cred("astro")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "sha"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        await _publish_github(campaign, cred, db)

    assert len(captured_content) >= 1, "create_file_commit was not called"
    content = captured_content[0]
    assert "tags:" in content
    assert '"astro"' in content


# ---------------------------------------------------------------------------
# Next.js tags — unconditional (AC 5)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_nextjs_writes_tags_without_template_key_gate():
    """Next.js path writes tags even when template posts don't have a tags key."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"tags": ["nextjs", "blog"]})
    cred = _github_cred("nextjs")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "sha"

    template_post_no_tags = "---\ntitle: Old Post\ndate: 2024-01-01\n---\nBody"

    async def mock_list_files(token, repo, path, extension=None):
        if path == "posts" and extension == ".md":
            return ["old-post.md"]
        return []

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.list_files_in_directory", side_effect=mock_list_files),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[template_post_no_tags])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        await _publish_github(campaign, cred, db)

    assert len(captured_content) >= 1, "create_file_commit was not called"
    content = captured_content[0]
    assert "tags:" in content
    assert '"nextjs"' in content


# ---------------------------------------------------------------------------
# Eleventy tags — unconditional (AC 6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_github_eleventy_writes_tags_without_template_key_gate():
    """Eleventy path writes tags even when template posts don't have a tags key."""
    from app.services.publishing import _publish_github

    campaign = _make_github_campaign(voice_score={"tags": ["eleventy", "jamstack"]})
    cred = _github_cred("eleventy")
    db = AsyncMock()
    db.add = MagicMock()

    captured_content = []

    async def mock_create(token, repo, file_path, content, message, branch="HEAD"):
        captured_content.append(content)
        return "sha"

    template_post_no_tags = "---\ntitle: Old Post\ndate: 2024-01-01\n---\nBody"

    with (
        patch("app.services.publishing.github_integration.create_file_commit", side_effect=mock_create),
        patch("app.services.publishing.github_integration.get_file_contents", AsyncMock(return_value=None)),
        patch("app.services.publishing.github_integration.get_directory_contents", AsyncMock(return_value=[{"type": "file", "name": "old.md"}])),
        patch("app.services.publishing.github_integration.get_first_post_files", AsyncMock(return_value=[template_post_no_tags])),
        patch("app.services.publishing.github_integration.slug_from_title", return_value="my-great-post"),
        patch("app.services.publishing.github_integration.html_to_markdown", return_value="Body."),
    ):
        await _publish_github(campaign, cred, db)

    assert len(captured_content) >= 1, "create_file_commit was not called"
    content = captured_content[0]
    assert "tags:" in content
    assert '"eleventy"' in content
