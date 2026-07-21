"""Shared prompts and helpers for content generation.

Imported by both integrations/gemini.py and integrations/anthropic_client.py
so that prompt changes need only be made in one place.
"""

import re


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

BANNED CHARACTER: Never use the em-dash character (—) anywhere in the output. Rewrite the sentence so it flows naturally without one — split it into two sentences, use a subordinate clause, or restructure the phrasing. Do not mechanically substitute a comma or colon; the sentence must read naturally on its own.

BANNED WORDS, do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor), it's worth noting, it's important to, plays a crucial role, serves as a reminder, Key Takeaways (as heading), in conclusion, in essence, moving forward, game-changer, leveraging, at the end of the day, the reality is, needless to say

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
    """Fix markdown syntax that LLMs leak inside otherwise-valid HTML."""
    # **bold** → <strong>bold</strong>
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html, flags=re.DOTALL)
    # *italic* → <em>italic</em> (single asterisks not part of **)
    html = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", html, flags=re.DOTALL)
    # ## Heading / ### Heading at the start of a line
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    return html
