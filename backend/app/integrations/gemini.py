"""Gemini LLM integration.

Called ONLY from services/ingestion.py and services/generation.py (AR-19).
Do not call this module directly from routers or workers.
"""

import json
import logging
import re

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

_MODEL = settings.GEMINI_MODEL
logger.info("Gemini model: %s", _MODEL)

_BVP_PROMPT_TEMPLATE = """Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema. No markdown code blocks, no explanation. Raw JSON only.

{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"],
  "target_audience": "<one sentence describing who this brand writes for, inferred from the content, or null if unclear>",

  "pronoun_preference": "<first_person | second_person | mixed>",
  "formality_scale": <integer 1-5, where 1 = very casual and 5 = very formal>,
  "humor_style": "<none | dry | playful | self_deprecating>",
  "vocabulary_complexity": "<plain | mixed | technical>",

  "example_style": "<analogy | data | story | direct>",
  "specificity_preference": "<concrete_numbers | vague_quantifiers | mixed>",
  "opening_pattern": "<question | bold_claim | anecdote | stat | problem>",
  "closing_pattern": "<cta | question | summary | one_liner | none>",
  "header_style": "<question | command | statement | mixed>",
  "post_structure_template": "<free text, e.g. hook -- pain -- insight -- example -- CTA>",

  "signature_phrases": ["5 to 10 short phrases pulled verbatim from the samples"],
  "voice_anchor_sentences": ["3 to 5 complete sentences pulled verbatim that best represent the voice"],
  "anti_pattern_example": "<one sentence this writer would never produce>"
}}

Field definitions:
- pronoun_preference: how the author typically refers to themselves (first_person), the reader (second_person), or both (mixed)
- formality_scale: 1 (very casual, contractions and slang) to 5 (very formal, no contractions, academic register)
- humor_style: none if absent, or the predominant style of humor detected
- vocabulary_complexity: plain (everyday words), mixed, or technical (domain-specific terminology)
- example_style: the most common way this author illustrates a point
- specificity_preference: whether the author uses concrete data and numbers or vague quantifiers
- opening_pattern: how the author typically begins a post or article
- closing_pattern: how the author typically ends a post or article
- header_style: the pattern used for section headings
- post_structure_template: the typical skeleton for a post, described as a flow in plain text
- signature_phrases: repeated or distinctive short phrases pulled verbatim; aim for 5-10 items
- voice_anchor_sentences: 3 to 5 verbatim sentences that best capture the voice
- anti_pattern_example: one sentence that sounds nothing like this writer

TEXT TO ANALYZE:
{text}"""


_QUALITATIVE_DEFAULTS: dict = {
    "pronoun_preference": "mixed",
    "formality_scale": 3,
    "humor_style": "none",
    "vocabulary_complexity": "plain",
    "example_style": "direct",
    "specificity_preference": "mixed",
    "opening_pattern": "bold_claim",
    "closing_pattern": "none",
    "header_style": "statement",
    "post_structure_template": "",
    "signature_phrases": [],
    "voice_anchor_sentences": [],
    "anti_pattern_example": "",
}

_VOICE_BRIEF_PROMPT = """You are analyzing a Brand Voice Profile JSON and writing a third-person voice brief.

BRAND VOICE PROFILE:
{bvp_json}

Write a plain prose paragraph of 150-250 words describing how this person writes.
Cover: pronoun choice, formality, sentence rhythm, how they open and close posts,
how they use examples, their vocabulary complexity, and what makes their writing distinctive.
Do NOT use JSON, field names, or bullet points. Write in flowing prose.
Do NOT use em-dashes. Use plain dashes (--) or restructure the sentence instead.
Return ONLY the paragraph. No heading, no explanation."""


def _thinking_config(thinking_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_tokens)
    )


async def synthesize_voice_brief(bvp: dict, thinking_tokens: int = 256) -> str:
    prompt = _VOICE_BRIEF_PROMPT.format(bvp_json=json.dumps(bvp, indent=2))
    try:
        response = await _client.aio.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=_thinking_config(thinking_tokens),
        )
        text = response.text.strip()
        return text if text else ""
    except Exception:
        logger.exception("Voice brief synthesis failed")
        return ""


async def extract_brand_voice(text: str, thinking_tokens: int = 1024) -> dict:
    prompt = _BVP_PROMPT_TEMPLATE.format(text=text[:50_000])

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        parts = raw.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        raw = inner.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

    if not isinstance(data.get("tone"), list):
        raise ValueError("Gemini BVP missing or invalid 'tone' field")
    if not isinstance(data.get("cadence"), dict):
        raise ValueError("Gemini BVP missing or invalid 'cadence' field")
    if not isinstance(data.get("banned_jargon"), list):
        raise ValueError("Gemini BVP missing or invalid 'banned_jargon' field")

    # Soft check: target_audience is optional
    if "target_audience" not in data:
        data["target_audience"] = None
    elif data["target_audience"] is not None and not isinstance(data["target_audience"], str):
        data["target_audience"] = None  # coerce invalid type to None silently

    for key, default in _QUALITATIVE_DEFAULTS.items():
        if key not in data or data[key] is None:
            data[key] = default

    # Synthesize from qualitative fields only; ingestion.py re-synthesizes after
    # merging computed stylometric fields and existing BVP arrays (AC 3 / AC 8).
    data["voice_brief"] = await synthesize_voice_brief(data)

    return data


_DEFAULT_VOICE = (
    "professional, clear, and authoritative tone; moderate cadence; avoid jargon"
)


def _build_voice_injection(bvp: dict) -> str:
    """Build Part A + Part B voice injection string for blog generation prompts.

    Returns empty string when voice_brief is absent (legacy BVP fallback path).
    All strings use double hyphens (--) not em-dashes.
    """
    voice_brief = bvp.get("voice_brief") or ""
    if not voice_brief:
        return ""

    list_pref = bvp.get("list_preference", "")
    list_rule = (
        "Use NO bullet lists unless a list is the only clear way to present the information"
        if list_pref == "rarely"
        else "Lists may appear where natural"
    )

    pronoun = bvp.get("pronoun_preference") or "mixed"
    spec_pref = bvp.get("specificity_preference") or "mixed"
    spec_rule = (
        "All quantifiable claims MUST use specific numbers, not vague phrases like 'many' or 'a lot'"
        if spec_pref == "concrete_numbers"
        else "Use the level of specificity that fits each claim"
    )

    header_style = bvp.get("header_style", "")
    header_rule = ""
    if header_style and header_style != "mixed":
        header_rule = f"\n- H2 and H3 headers should be phrased as {header_style}s"

    closing_pat = bvp.get("closing_pattern") or ""
    closing_rule = ""
    if closing_pat:
        closing_rule = f"\n- Conclusion should follow a {closing_pat} closing pattern"

    return (
        f"{voice_brief}\n\n"
        "VOICE APPLICATION RULES (apply within the SEO structure -- do not override structure):\n"
        "- SEO structure is mandatory: H1, meta description, H2/H3 headings, body, conclusion, "
        "800-1500 words are non-negotiable\n"
        f"- {list_rule}\n"
        "- Opening pattern applies to the FIRST BODY PARAGRAPH, not the H1 or meta description\n"
        f"- Pronoun preference applies consistently throughout: {pronoun}\n"
        f"- {spec_rule}"
        f"{header_rule}"
        f"{closing_rule}"
    )


def _meta_voice_note(bvp: dict) -> str:
    """Return the condensed voice note for the meta description instruction.

    Returns empty string when voice_brief is absent.
    The note is the first complete sentence of voice_brief, capped at 50 words.
    """
    brief = (bvp or {}).get("voice_brief") or ""
    if not brief:
        return ""
    first_sentence = brief.split(".")[0].strip()
    words = first_sentence.split()[:50]
    if not words:
        return ""
    return " -- write it in this voice: " + " ".join(words)


_BLOG_PROMPT = """You are a direct, expert blog writer. Write a blog post that sounds like a human expert, not an AI assistant.

BRAND VOICE PROFILE:
{voice_section}

BRAIN DUMP (author's raw ideas: build the blog around the core argument, but RETAIN all first-person experiences, specific numbers, dates, named tools, or unique outcomes. These are E-E-A-T and Information Gain signals; do not generalize or anonymize them):
{brain_dump}

{seo_target_section}
{audience_section}

MANDATORY STRUCTURE (HTML only, no markdown; follow this EXACTLY):
<h1>[Keyword-first title, specific and direct]</h1>
<!-- meta: [One sentence meta description, max 150 chars, ends with action phrase{meta_voice_note}] -->
<!-- excerpt: [One engaging editorial hook, max 240 chars, conversational -- open with a provocative question, a surprising fact, or an intriguing observation; NOT a summary or restatement of the title] -->
<div class="tldr"><p><strong>TL;DR:</strong> [2-3 bold sentences that directly answer the post's core question. Specific. No filler.]</p></div>
<p>[BLUF intro paragraph: Start with a specific fact, number, or bold claim. Never start with "In today's..." or similar openers. State the core takeaway in the first sentence.]</p>
<h2>[Main topic, actionable heading]</h2>
[GEO RULE: If this H2 implies a direct question (How to, Why, What is, When should you): open with a direct 1–3 sentence answer paragraph (max ~60 words) BEFORE the H3 (this is the AI Overview citation extract). If the H2 is built around examples, comparisons, step-by-step processes, or data: skip the answer block and lead straight into the H3. Never force an answer block where it does not arise naturally.]
<h3>[Sub-topic]</h3>
<p>...</p>
[Write 3 to 4 main content H2 sections. VARY THE STRUCTURE of each section -- do not repeat the same H2 to H3 to paragraph pattern every time. Choose a different structural approach for each section. Options: (a) open with a <ol> numbered process (no H3 needed); (b) open with a bold single-sentence claim in <p><strong>...</strong></p> before the first H3; (c) use H3 subheadings with 2-3 short paragraphs each; (d) write as flowing paragraphs with no H3 at all. Never use the same structure twice in a row across the 3-4 sections.]
<h2>Frequently Asked Questions</h2>
<dl class="faq">
  <dt>[Question 1 related to the post topic]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 2]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 3]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
</dl>
<h2>[Conclusion heading chosen to fit this specific article and voice -- e.g. "What to Do Next", "My Recommendation", "The Bottom Line on [Topic]", or any heading that fits naturally. Never use "Key Takeaways" or "In Conclusion".]</h2>
<p>[Closing paragraph: lead with the single most important action the reader should take. No section recap. End with forward momentum, not a summary.]</p>

REQUIREMENTS:
- Target 900-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: {cadence_instruction}
- Never use these jargon terms: {banned_jargon_list}
- If the Brain Dump says "I found X", "I tested X", or "I built X": use first-person voice in the post. Never convert "I found conversion increased 40%" into "conversion rates can increase up to 40%". The author's direct experience is the E-E-A-T signal.
- If the Brain Dump contains proprietary data, A/B test results, client outcomes, or specific findings not commonly known: surface these in the opening of the relevant H2 section. Do not bury unique data behind generic context-setting paragraphs.
- Sentence length must vary dramatically within each paragraph. Mix short punches (3-8 words) with longer explanatory sentences (20+ words) in the same paragraph. Uniform sentence rhythm -- every sentence near the same length -- is the clearest measurable AI writing signal. Aim for a range of at least 12 words between your shortest and longest sentence within any given paragraph.
- Vary how paragraphs begin. Not every paragraph should open with its topic sentence. Some may open with a specific example, a concrete number, a named tool or outcome, or a conjunction (But, So, Because, And) when continuing a thought directly from the prior sentence. Aim for at least two paragraphs in the article that begin with a conjunction.
- Before writing the FAQ section: identify the most likely follow-up question a reader still has after finishing the body. If it is not answered, add it as an additional FAQ entry. A reader who searched for your focus keyword should not need to open another tab. Never write "for more information, see..." -- answer it here.
- Never write "many", "several", "some", "most", "often", "significant", "considerable", or "various" without attaching a specific number, timeframe, or qualifier from the brain dump. If the brain dump does not supply the data: either omit the claim entirely or hedge it explicitly ("in my experience", "from what I've seen", "your results may vary depending on").
- Contractions: if the brand tone list includes "casual", "friendly", "conversational", or "approachable" -- use contractions naturally throughout (don't, can't, I've, you'll, it's). If the tone list includes "formal", "professional", "authoritative", or "corporate" -- avoid contractions entirely.
- When making a claim not directly supported by specific data in the brain dump: use first-person hedging ("in my experience", "from what I've seen", "based on the above") rather than stating it as universal fact. Never assert something is always true when the brain dump only documents a single case.
- Output ONLY valid HTML tags. NEVER use markdown syntax like **bold**, *italic*, ##, ###
- Bold text must use <strong>, italics must use <em>

BANNED OPENERS, never start any paragraph or sentence with these phrases:
- "In today's fast-paced world"
- "In today's digital landscape"
- "As we all know"
- "It's no secret that"
- "The [anything] landscape is evolving"
- "Standing out requires more than"
- "Now more than ever"

BANNED WORDS, do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor), em-dash, it's worth noting, it's important to, plays a crucial role, serves as a reminder, Key Takeaways (as heading), in conclusion, in essence, moving forward, game-changer, leveraging, at the end of the day, the reality is, needless to say

Every sentence must earn its place. If a sentence does not give the reader new information or a specific action, cut it.
"""

_FIDELITY_PROMPT = """Evaluate the following blog post against the Brand Voice Profile AND for SEO quality.

BRAND VOICE PROFILE:
{bvp_json}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned BVP terms found>,
  "seo_bluf_present": <boolean: true if the first <p> tag starts with a specific fact, stat, or direct claim, NOT a general statement like "The landscape is..."; false otherwise>,
  "seo_h2_count": <integer: count of <h2> tags in the blog HTML>,
  "seo_faq_present": <boolean: true if a FAQ section with at least 3 Q&A pairs (as <dl> or similar) is present>,
  "seo_fluff_detected": <boolean: true if any banned opener phrase like "In today's fast-paced world", "As we all know", "It's no secret that" appears anywhere in the content>,
  "tags": [<list of 3-5 concise lowercase SEO tags relevant to this specific post, e.g. ["brand voice", "content marketing", "ai tools"]>]
}}
{expanded_scoring_section}"""

_SOCIAL_PROMPT = """Based on the brain dump and brand voice, write two social media posts.

BRAND VOICE PROFILE:
{bvp_json}
{linkedin_voice_section}
BRAIN DUMP:
{brain_dump}

BLOG TITLE:
{blog_title}

Return ONLY a valid JSON object (no markdown):
{{
  "x_post": "<X post text, max 280 characters, tease the blog without duplicating it>",
  "linkedin_post": "<LinkedIn post, 500-1300 characters, use blank lines for paragraph breaks. Must open with a first-person hook tied to the brain dump's key insight. Acceptable openers: 'I just discovered...', 'Last week I...', 'After testing X, I found...'. Tease the specific outcome from the brain dump, not the general topic.>"
}}
"""


def _build_seo_section(
    target_keyword: str | None,
    target_audience: str | None,
    secondary_keywords: str | None = None,
) -> tuple[str, str]:
    if target_keyword:
        seo_section = f"""SEO TARGET:
- Primary keyword: {target_keyword}
- Include this exact phrase or a close variant in: the H1 title, the first 100 words, at least one H2 heading, and the conclusion paragraph.
- Write to rank for this specific search query. Assume the reader typed this exact phrase into Google."""
    else:
        seo_section = """SEARCH INTENT FOCUS (no keyword provided):
Extract the single most specific, actionable angle from the Brain Dump. Pick ONE target reader type: not "developers AND marketers", not "apps AND SaaS". Choose one. Write exclusively for that angle. State your choice in the H1 and commit to it through every section. If the brain dump is broad, pick the most specific, technical angle."""

    if secondary_keywords:
        seo_section += f"""

SUPPORTING KEYWORDS (mention each at most once, naturally):
{secondary_keywords}
- Place each term at most once within the first 500 words, only inside a sentence that already calls for it."""

    audience_section = ""
    if target_audience:
        audience_section = f"""TARGET AUDIENCE:
- {target_audience}
- Write exclusively for this audience. Do not broaden the scope. If a reference or tool would be unfamiliar to this audience, explain it in one clause or omit it."""

    return seo_section, audience_section


def _strip_fences(raw: str) -> str:
    fence_start = raw.find("```")
    if fence_start == -1:
        return raw
    lines = raw[fence_start:].split("\n")
    start = 1
    end = len(lines)
    if lines and lines[-1].strip() == "```":
        end -= 1
    return "\n".join(lines[start:end]).strip()


def _md_to_html(html: str) -> str:
    """Fix markdown syntax that Gemini leaks inside otherwise-valid HTML."""
    # **bold** → <strong>bold</strong>
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html, flags=re.DOTALL)
    # *italic* → <em>italic</em> (single asterisks not part of **)
    html = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", html, flags=re.DOTALL)
    # ## Heading / ### Heading at the start of a line (if Gemini emits bare markdown headings)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    return html


async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
    target_keyword: str | None = None,
    target_audience: str | None = None,
    secondary_keywords: str | None = None,
) -> str:
    if brand_voice_profile:
        tone_list = ", ".join(str(t) for t in brand_voice_profile.get("tone", []))
        cadence = brand_voice_profile.get("cadence") or {}
        avg_sentence_length = cadence.get("avg_sentence_length") or 15
        variation_pattern = str(cadence.get("variation_pattern") or "").strip()
        paragraph_structure = str(cadence.get("paragraph_structure") or "").strip()
        cadence_parts = [f"avg sentence length {avg_sentence_length} words"]
        if variation_pattern:
            cadence_parts.append(f'sentence variation: "{variation_pattern}"')
        if paragraph_structure:
            cadence_parts.append(f'paragraph structure: "{paragraph_structure}"')
        cadence_instruction = "; ".join(cadence_parts)
        if variation_pattern or paragraph_structure:
            cadence_instruction += ". Apply all of these patterns literally in the prose."
        banned_jargon_list = ", ".join(str(j) for j in brand_voice_profile.get("banned_jargon", []))
        # Use voice injection when voice_brief is present; fall back to JSON for legacy BVPs
        if brand_voice_profile.get("voice_brief"):
            voice_section = _build_voice_injection(brand_voice_profile)
        else:
            voice_section = json.dumps(brand_voice_profile)
    else:
        voice_section = _DEFAULT_VOICE
        tone_list = "professional, clear, authoritative"
        cadence_instruction = "avg sentence length 15 words"
        banned_jargon_list = "none specified"

    meta_voice_note = _meta_voice_note(brand_voice_profile or {})

    seo_target_section, audience_section = _build_seo_section(target_keyword, target_audience, secondary_keywords)

    prompt = _BLOG_PROMPT.format(
        voice_section=voice_section,
        meta_voice_note=meta_voice_note,
        brain_dump=brain_dump,
        tone_list=tone_list,
        cadence_instruction=cadence_instruction,
        banned_jargon_list=banned_jargon_list,
        seo_target_section=seo_target_section,
        audience_section=audience_section,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    result = _md_to_html(_strip_fences(response.text.strip()))

    # Post-processing validation pass
    if "<h1" not in result.lower():
        logger.warning("generate_blog: Gemini output missing H1 tag")
    h2_count = result.lower().count("<h2")
    if h2_count < 2:
        logger.warning("generate_blog: Gemini output has fewer than 2 H2 tags (%d found)", h2_count)
    if '<div class="tldr">' not in result:
        h1_close = result.lower().find("</h1>")
        if h1_close != -1:
            insert_pos = h1_close + len("</h1>")
            result = (
                result[:insert_pos]
                + '<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>'
                + result[insert_pos:]
            )
        else:
            # H1 also absent: prepend TL;DR so the block is never omitted
            result = (
                '<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>'
                + result
            )

    return result


_FIDELITY_THINKING_TOKENS = 256


async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = _FIDELITY_THINKING_TOKENS,
) -> dict:
    if brand_voice_profile is None:
        return {
            "tone_score": 10,
            "cadence_score": 10,
            "jargon_violations": 0,
            "seo_bluf_present": True,
            "seo_h2_count": 3,
            "seo_faq_present": True,
            "seo_fluff_detected": False,
            "tags": [],
        }

    # Build expanded scoring instructions for new BVP fields (advisory -- no pass/fail impact)
    bvp = brand_voice_profile
    expanded_parts: list[str] = []
    if bvp.get("pronoun_preference"):
        pronoun = bvp["pronoun_preference"]
        expanded_parts.append(
            f'  "pronoun_score": <integer 0-10, how consistently does the post use {pronoun} pronouns?>'
        )
    if bvp.get("specificity_preference"):
        spec_pref = bvp["specificity_preference"]
        expanded_parts.append(
            f'  "specificity_score": <integer 0-10, how well does the post match the "{spec_pref}" specificity preference?>'
        )
    if bvp.get("closing_pattern"):
        closing = bvp["closing_pattern"]
        expanded_parts.append(
            f'  "closing_match": <boolean, does the conclusion match the expected "{closing}" closing pattern?>'
        )

    if expanded_parts:
        expanded_scoring_section = (
            "\nAlso add these advisory fields to the JSON object above:\n"
            + "\n".join(expanded_parts)
        )
    else:
        expanded_scoring_section = ""

    prompt = _FIDELITY_PROMPT.format(
        bvp_json=json.dumps(brand_voice_profile),
        blog_html=blog_html,
        expanded_scoring_section=expanded_scoring_section,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("check_fidelity: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"check_fidelity: Gemini returned invalid JSON: {exc}") from exc

    for key in ("tone_score", "cadence_score", "jargon_violations"):
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")
        if not isinstance(data[key], (int, float)):
            raise ValueError(
                f"check_fidelity: '{key}' must be numeric, got {type(data[key]).__name__}"
            )

    seo_bool_keys = ("seo_bluf_present", "seo_faq_present", "seo_fluff_detected")
    for key in seo_bool_keys:
        if key not in data:
            raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")
        if not isinstance(data[key], bool):
            raise ValueError(
                f"check_fidelity: '{key}' must be bool, got {type(data[key]).__name__}"
            )
    if "seo_h2_count" not in data:
        raise ValueError("check_fidelity: missing key 'seo_h2_count' in Gemini response")
    if not isinstance(data["seo_h2_count"], int) or isinstance(data["seo_h2_count"], bool):
        raise ValueError(
            f"check_fidelity: 'seo_h2_count' must be int, got {type(data['seo_h2_count']).__name__}"
        )

    if "tags" in data:
        if not isinstance(data["tags"], list):
            logger.warning("check_fidelity: 'tags' is not a list (got %s), coercing to []", type(data["tags"]).__name__)
            data["tags"] = []
        else:
            data["tags"] = [
                re.sub(r"[\r\n]", " ", t).strip()
                for t in data["tags"]
                if isinstance(t, str)
            ][:5]

    # Advisory fields: store if present, no validation failure if missing or wrong type.
    # These do NOT affect the pass/fail badge (tone >= 7, cadence >= 6, jargon_violations == 0 unchanged).
    for advisory_key in ("pronoun_score", "specificity_score"):
        if advisory_key in data and not isinstance(data[advisory_key], (int, float)):
            data[advisory_key] = None  # coerce invalid type silently
    if "closing_match" in data and not isinstance(data["closing_match"], bool):
        data["closing_match"] = None  # coerce invalid type silently

    return data


async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,
) -> dict:
    # Build bvp_json for the BRAND VOICE PROFILE section.
    # voice_brief is excluded from bvp_json (X post must not receive it per AC 9).
    # A separate linkedin_voice_section injects Part A (prose only) for LinkedIn.
    if brand_voice_profile:
        bvp_without_voice = {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
        bvp_json = json.dumps(bvp_without_voice)
    else:
        bvp_json = _DEFAULT_VOICE

    voice_brief = (brand_voice_profile or {}).get("voice_brief") or ""
    if voice_brief:
        linkedin_voice_section = (
            "\nLINKEDIN BRAND VOICE (apply to linkedin_post only -- do not apply to x_post):\n"
            f"{voice_brief}\n"
        )
    else:
        linkedin_voice_section = ""

    prompt = _SOCIAL_PROMPT.format(
        bvp_json=bvp_json,
        linkedin_voice_section=linkedin_voice_section,
        brain_dump=brain_dump,
        blog_title=blog_title,
    )

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=_thinking_config(thinking_tokens),
    )
    raw = _strip_fences(response.text.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_social: Gemini returned invalid JSON: %r", raw[:200])
        raise ValueError(f"generate_social: Gemini returned invalid JSON: {exc}") from exc

    for key in ("x_post", "linkedin_post"):
        if key not in data:
            raise ValueError(f"generate_social: missing key '{key}' in Gemini response")
        if not isinstance(data[key], str):
            raise ValueError(
                f"generate_social: '{key}' must be a string, got {type(data[key]).__name__}"
            )

    if len(data["x_post"]) > 280:
        logger.warning(
            "generate_social: X post exceeded 280 chars (%d), truncating",
            len(data["x_post"]),
        )
        data["x_post"] = data["x_post"][:279] + "…"

    ln_len = len(data["linkedin_post"])
    if ln_len > 1300:
        logger.warning(
            "generate_social: LinkedIn post exceeded 1300 chars (%d), truncating",
            ln_len,
        )
        data["linkedin_post"] = data["linkedin_post"][:1299] + "…"
    elif ln_len < 500:
        logger.warning(
            "generate_social: LinkedIn post length %d is below expected 500 chars",
            ln_len,
        )

    return data
