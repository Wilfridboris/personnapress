import fnmatch

from app.integrations.github import get_directory_contents, get_repo_root_contents

# Default publish paths per framework
FRAMEWORK_PUBLISH_PATHS: dict[str, str] = {
    "jekyll": "_posts/",
    "astro": "src/content/blog/",
    "hugo": "content/posts/",
    "eleventy": "src/posts/",
    "docusaurus": "blog/",
    "mkdocs": "docs/",
    "nextjs": "posts/",
    "plain_static": "docs/",
    "unknown": "",
}

SELECTABLE_FRAMEWORKS = [f for f in FRAMEWORK_PUBLISH_PATHS if f != "unknown"]


def _find(names: set[str], *patterns: str) -> str | None:
    """Return the first name from `names` matching any of the glob patterns, or None."""
    for name in names:
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                return name
    return None


def _high(framework: str, publish_path: str, signals: list[str]) -> dict:
    return {
        "detected_framework": framework,
        "publish_path": publish_path,
        "confidence": "high",
        "signals": signals,
        "candidates": [],
    }


async def detect_framework(installation_token: str, repo_full_name: str) -> dict:
    """
    Scan repo root via GitHub Contents API and identify the blog framework.

    Returns dict with: detected_framework, publish_path, confidence, signals, candidates.
    Priority order: Jekyll → Astro → Hugo → Eleventy → Docusaurus → MkDocs → Next.js → Plain static → Unknown.
    """
    root_items = await get_repo_root_contents(installation_token, repo_full_name)
    root_names: set[str] = {item["name"] for item in root_items}

    candidates: list[dict] = []

    # 1. Jekyll — _config.yml + _posts/
    jekyll_cfg = _find(root_names, "_config.yml", "_config.yaml")
    if jekyll_cfg:
        posts_dir = await get_directory_contents(installation_token, repo_full_name, "_posts")
        if posts_dir:
            return _high("jekyll", "_posts/", [jekyll_cfg, "_posts/"])
        candidates.append({"framework": "jekyll", "publish_path": "_posts/", "signals": [jekyll_cfg]})

    # 2. Astro — astro.config.* + src/content/
    astro_cfg = _find(root_names, "astro.config.*")
    if astro_cfg:
        src_content = await get_directory_contents(installation_token, repo_full_name, "src/content")
        if src_content:
            return _high("astro", "src/content/blog/", [astro_cfg, "src/content/"])
        candidates.append({"framework": "astro", "publish_path": "src/content/blog/", "signals": [astro_cfg]})

    # 3. Hugo — hugo.toml|yaml|yml|json + content/
    hugo_cfg = _find(root_names, "hugo.toml", "hugo.yaml", "hugo.yml", "hugo.json")
    if hugo_cfg:
        content_dir = await get_directory_contents(installation_token, repo_full_name, "content")
        if content_dir:
            return _high("hugo", "content/posts/", [hugo_cfg, "content/"])
        candidates.append({"framework": "hugo", "publish_path": "content/posts/", "signals": [hugo_cfg]})

    # 4. Eleventy — .eleventy.js|.cjs (single-signal, no directory check)
    eleventy_cfg = _find(root_names, ".eleventy.js", ".eleventy.cjs")
    if eleventy_cfg:
        return _high("eleventy", "src/posts/", [eleventy_cfg])

    # 5. Docusaurus — docusaurus.config.* + blog/
    docu_cfg = _find(root_names, "docusaurus.config.*")
    if docu_cfg:
        blog_dir = await get_directory_contents(installation_token, repo_full_name, "blog")
        if blog_dir:
            return _high("docusaurus", "blog/", [docu_cfg, "blog/"])
        candidates.append({"framework": "docusaurus", "publish_path": "blog/", "signals": [docu_cfg]})

    # 6. MkDocs — mkdocs.yml + docs/
    if "mkdocs.yml" in root_names:
        docs_dir = await get_directory_contents(installation_token, repo_full_name, "docs")
        if docs_dir:
            return _high("mkdocs", "docs/", ["mkdocs.yml", "docs/"])
        candidates.append({"framework": "mkdocs", "publish_path": "docs/", "signals": ["mkdocs.yml"]})

    # 7. Next.js — next.config.* + posts/ or content/
    nextjs_cfg = _find(root_names, "next.config.*")
    if nextjs_cfg:
        posts_dir = await get_directory_contents(installation_token, repo_full_name, "posts")
        content_dir = await get_directory_contents(installation_token, repo_full_name, "content")
        if posts_dir or content_dir:
            publish_path = "posts/" if posts_dir else "content/"
            return _high("nextjs", publish_path, [nextjs_cfg, publish_path])
        candidates.append({"framework": "nextjs", "publish_path": "posts/", "signals": [nextjs_cfg]})

    # 8. Plain static — index.html or .nojekyll
    plain_signal = _find(root_names, "index.html", ".nojekyll")
    if plain_signal:
        docs_dir = await get_directory_contents(installation_token, repo_full_name, "docs")
        publish_path = "docs/" if docs_dir else "/"
        return _high("plain_static", publish_path, [plain_signal])

    # Resolve based on candidates collected
    if not candidates:
        return {
            "detected_framework": "unknown",
            "publish_path": "",
            "confidence": "low",
            "signals": [],
            "candidates": [],
        }

    if len(candidates) == 1:
        c = candidates[0]
        return {
            "detected_framework": c["framework"],
            "publish_path": c["publish_path"],
            "confidence": "medium",
            "signals": c["signals"],
            "candidates": [],
        }

    # Ambiguous: 2–3 plausible frameworks
    return {
        "detected_framework": candidates[0]["framework"],
        "publish_path": candidates[0]["publish_path"],
        "confidence": "low",
        "signals": [],
        "candidates": candidates[:3],
    }
