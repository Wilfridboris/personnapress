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

    _raw_sig = bvp.get("signature_phrases")
    sig_phrases = [
        p for p in (_raw_sig if isinstance(_raw_sig, list) else [])
        if isinstance(p, str) and p.strip()
    ][:10]
    _raw_anchors = bvp.get("voice_anchor_sentences")
    voice_anchors = [
        s for s in (_raw_anchors if isinstance(_raw_anchors, list) else [])
        if isinstance(s, str) and s.strip()
    ][:5]
    _raw_anti = bvp.get("anti_pattern_example")
    anti_pattern = ((_raw_anti if isinstance(_raw_anti, str) else "") or "").strip().replace("—", "--").replace('"', "'")

    sig_block = ""
    if sig_phrases:
        phrases_clean = [p.replace("—", "--").replace("\n", " ").replace("\r", "") for p in sig_phrases]
        sig_bullet_list = "\n".join(f"- {p}" for p in phrases_clean)
        sig_block = (
            "\nSIGNATURE PHRASES (short phrases this writer uses naturally -- weave 2-3 into the post "
            "where they fit organically; never force them and never repeat the same phrase twice):\n"
            + sig_bullet_list
        )

    anchor_block = ""
    if voice_anchors:
        anchors_clean = [s.replace("—", "--").replace("\n", " ").replace("\r", "") for s in voice_anchors]
        anchor_bullet_list = "\n".join(f"- {s}" for s in anchors_clean)
        anchor_block = (
            "\nVOICE ANCHORS (verbatim sentences from this writer -- these represent the target register, "
            "rhythm, and directness; match this level throughout the post):\n"
            + anchor_bullet_list
        )

    anti_block = ""
    if anti_pattern:
        anti_block = (
            f'\nANTI-PATTERN (this writer would NEVER produce a sentence like this -- avoid this register, '
            f'vocabulary, and structure throughout):\n"{anti_pattern}"'
        )

    return (
        f"{voice_brief}\n\n"
        "VOICE APPLICATION RULES (apply within the SEO structure -- do not override structure):\n"
        "- SEO structure is mandatory: H1, meta description, H2/H3 headings, body, conclusion, "
        "word count is governed by the content strategy\n"
        f"- {list_rule}\n"
        "- Opening pattern applies to the FIRST BODY PARAGRAPH, not the H1 or meta description\n"
        f"- Pronoun preference applies consistently throughout: {pronoun}\n"
        f"- {spec_rule}"
        f"{header_rule}"
        f"{closing_rule}"
        + sig_block
        + anchor_block
        + anti_block
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

BRAIN DUMP:
{brain_dump}

Before writing, silently classify every part of the brain dump above into one of three types:

AUTHORED PASSAGE -- 2 or more coherent first-person sentences that read as finished prose (not
a list, not a fragment, not a label:value pair). These are Information Gain signals: content
that exists nowhere else on the web because only this author lived it. Google's ranking
algorithm scores this uniqueness directly.

FRAGMENT/NOTE -- bullet points, single-line fragments, data lists, label:value pairs (e.g.
"Tools: Apollo, Clay"), shorthand notes. Raw material for you to expand.

DIRECTIVE -- any line beginning with "Note:", "Final note:", "PS:", or "Important:". These are
author instructions to you. Follow them silently. Do not output them as content.

TREATMENT RULES:
- AUTHORED PASSAGES: reproduce in the blog with grammar corrections only. Do not rewrite
  structure, improve vocabulary, or apply the Brand Voice Profile to these passages -- the
  author's own words ARE the voice here. If a passage contains an em-dash, rewrite that
  sentence naturally without one but change nothing else. Preserve expressions of uncertainty,
  self-deprecation, conversational asides, and off-script moments exactly as written -- these
  are authenticity signals, not errors.
- AUTHORED PASSAGES must open the section they belong to: place them as the first content after
  the H2 or H3 heading. The authored passage is the Information Gain delta; surface it first so
  Google's passage indexing can capture it independently.
- For sections you generate from FRAGMENT/NOTE content: match the directness, sentence length,
  and register of the AUTHORED PASSAGES in this brain dump. Do not default to a generic
  professional blog voice -- the authored passages are your register benchmark.
- FRAGMENT/NOTE content: expand into full prose using the Brand Voice Profile and SEO structure.
- DIRECTIVES: follow them silently. Never quote or reference them in the output.

RETAIN all first-person experiences, specific numbers, dates, named tools, and unique outcomes
regardless of classification. These are E-E-A-T signals; do not generalize or anonymize them.
If the brain dump contains any URLs (http:// or https://), embed each as an HTML anchor link
<a href="[URL]" rel="noopener noreferrer" target="_blank">[natural anchor text describing what
the URL points to]</a> at the point in the article where it is most relevant; preserve each URL
exactly as provided. If the brain dump contains no URLs, do not add any anchor tags or links.

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
- Target {word_count_range}
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
- Never use passive voice when active voice is possible. Write "I tested this" not "this was
  tested", "the data showed" not "it was shown by the data". Passive voice is the single most
  detectable AI writing pattern.
- In 1-2 sections, take a clear direct opinion: "I think X is wrong", "most advice on this is
  backwards", "in my view Y is overrated". State it as the author's personal view, not
  universal fact. Opinion statements are the strongest authenticity signal in written content.
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

{length_override_section}
Output ONLY the HTML above. Do NOT append any word count, compliance summary, keyword checklist, or verification notes after the closing HTML tag.
"""

_FIDELITY_PROMPT = """Evaluate the following blog post against the Brand Voice Profile AND for SEO quality.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP SAMPLE (first 1500 characters of the original brain dump -- used only to verify authored passage preservation):
{brain_dump_sample}

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
  "authored_passages_preserved": <boolean: true if at least one passage of 2+ coherent first-person sentences from the brain dump sample appears in the blog HTML with only minor grammar changes; false if all brain dump content has been fully rewritten>,
  "tags": [<list of 3-5 concise lowercase SEO tags relevant to this specific post, e.g. ["brand voice", "content marketing", "ai tools"]>]
}}
{expanded_scoring_section}"""

_SOCIAL_PROMPT = """Based on the brain dump and brand voice, write two social media posts.

BRAND VOICE PROFILE:
{bvp_json}
{linkedin_voice_section}
BRAIN DUMP:
{brain_dump}

Reading the brain dump: if it contains AUTHORED PASSAGES (2+ coherent first-person sentences in
finished prose), use their exact wording as the LinkedIn post opening hook -- preserve the
register and do not professionalize. Distil the sharpest claim or opinion from any authored
passage as the X post hook. DIRECTIVES (lines beginning "Note:", "Final note:", "PS:") are
author instructions -- follow them silently, never include them in the posts. Preserve
personality signals (humor, self-deprecation, bluntness) from authored passages exactly.

BLOG TITLE:
{blog_title}

Return ONLY a valid JSON object (no markdown):
{{
  "x_post": "<X post text, max 280 characters, tease the blog without duplicating it>",
  "linkedin_post": "<LinkedIn post, 500-1300 characters, use blank lines for paragraph breaks. Must open with a first-person hook tied to the brain dump's key insight. Acceptable openers: 'I just discovered...', 'Last week I...', 'After testing X, I found...'. Tease the specific outcome from the brain dump, not the general topic. No em-dash character (—) anywhere in either post.>"
}}
"""

_SOCIAL_STANDALONE_PROMPT = """You are an expert social media copywriter. Write two native social posts.
These posts stand alone -- there is no blog article to link to or tease.

BRAND VOICE PROFILE:
{bvp_json}
{linkedin_voice_section}
{bvp_structure_hints}
BRAIN DUMP:
{brain_dump}

Reading the brain dump: if it contains AUTHORED PASSAGES (2+ coherent first-person sentences in
finished prose), use their exact wording as the LinkedIn post opening hook -- preserve the
register and do not professionalize. Distil the sharpest claim or opinion from any authored
passage as the X post hook. DIRECTIVES (lines beginning "Note:", "Final note:", "PS:") are
author instructions -- follow them silently, never include them in the posts. Preserve
personality signals (humor, self-deprecation, bluntness) from authored passages exactly.

Return ONLY a valid JSON object (no markdown):
{{
  "x_post": "<X post, 70-280 characters. Structure: Hook (first ~70 chars, stops the scroll) then Value (1 core insight or 2-3 short bullets) then Proof (a number or outcome from the brain dump if available) then Nudge (simple ask: Save this / Reply with X / Drop a comment). This is the complete thought -- no 'Read the full guide', no link CTA, no em-dash character (—) anywhere.>",
  "linkedin_post": "<LinkedIn post, 1200-2500 characters. Use blank lines between each section. Structure must follow this order: (1) HOOK lines 1-2: choose the strongest pattern for this content -- bold data claim (I analyzed N things. Here is the pattern.), before/after transformation (X months ago [pain]. Today [outcome]. Here is what changed.), contrarian one-liner (Everyone says X. Here is why that costs you.), personal reveal (I almost [negative outcome]. The problem was not what you think.), timeline/result (In N days we [result]. Here is exactly what changed.), mistake/pain (Most [audience] do X. Here is the cost.). (2) RE-HOOK lines 3-4: one sharp line clarifying who this is for. (3) PROBLEM/STAKES: 3-6 short lines with concrete specifics -- numbers, budget, time, emotional cost -- pulled from the brain dump. (4) STORY/INSIGHT: 5-10 lines with specific details, named tools, outcomes, or data from the brain dump. (5) STEPS/FRAMEWORK: 3-7 bullets, each a clear action or belief shift, not a vague principle. (6) SOFT CTA: 1-2 lines -- a specific question the reader can answer, a comment trigger ('Comment X and I will send it'), or a DM invite. Never close with 'thoughts?' or 'you can too'. No em-dash character (—) anywhere. No 'Read the full guide' or blog link CTA.>"
}}
"""


def _build_standalone_voice_injection(bvp: dict) -> str:
    """Build BRAND STRUCTURE HINTS section for standalone social posts.

    Injects BVP fields that are captured during voice extraction but unused
    in the standard social prompt: opening_pattern, closing_pattern,
    post_structure_template.
    Returns empty string when none of these fields are present.
    """
    if not bvp:
        return ""
    hints: list[str] = []

    opening = (bvp.get("opening_pattern") or "").strip()
    opening_map = {
        "question": "question hook (open with a question the audience is already asking)",
        "bold_claim": "bold claim or data hook (open with a specific number or contrarian statement)",
        "anecdote": "personal reveal or before/after hook (open with a micro-story or confession)",
        "stat": "data/numbers hook (open with a statistic or surprising figure)",
        "problem": "mistake/pain hook (open by naming a common mistake or its cost)",
    }
    if opening and opening in opening_map:
        hints.append(f"- LinkedIn hook should lean toward: {opening_map[opening]}")

    closing = (bvp.get("closing_pattern") or "").strip()
    closing_map = {
        "cta": "end with a direct action CTA (comment trigger or DM invite)",
        "question": "end with a specific question the reader can answer in the comments",
        "summary": "end with one crisp sentence that crystallises the main lesson",
        "one_liner": "end with a punchy one-liner that creates a memorable takeaway",
    }
    if closing and closing in closing_map:
        hints.append(f"- LinkedIn CTA should: {closing_map[closing]}")

    structure = (bvp.get("post_structure_template") or "").strip()
    if structure:
        hints.append(f"- Author's preferred post structure: {structure} -- use as guide for section ordering")

    _raw_sig = bvp.get("signature_phrases")
    sig_phrases = [
        p for p in (_raw_sig if isinstance(_raw_sig, list) else [])
        if isinstance(p, str) and p.strip()
    ][:5]
    _raw_anti = bvp.get("anti_pattern_example")
    anti_pattern = ((_raw_anti if isinstance(_raw_anti, str) else "") or "").strip().replace("—", "--").replace('"', "'")

    if sig_phrases:
        phrases_str = ", ".join(p.replace("—", "--").replace("\n", " ").replace("\r", "") for p in sig_phrases)
        hints.append(
            f"- Writer's signature phrases -- use 1-2 naturally in the LinkedIn post (not in x_post): {phrases_str}"
        )
    if anti_pattern:
        hints.append(f'- ANTI-PATTERN: never produce text like "{anti_pattern}"')

    if not hints:
        return ""
    return (
        "\nBRAND STRUCTURE HINTS (from voice profile -- apply to linkedin_post only):\n"
        + "\n".join(hints)
        + "\n"
    )


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


def _extract_json_object(text: str) -> str:
    """Return the first complete JSON object from text, discarding any trailing prose."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _strip_fences(raw: str) -> str:
    fence_start = raw.find("```")
    if fence_start == -1:
        return _extract_json_object(raw)
    lines = raw[fence_start:].split("\n")
    start = 1
    end = len(lines)
    if lines and lines[-1].strip() == "```":
        end -= 1
    return _extract_json_object("\n".join(lines[start:end]).strip())


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


def _strip_blog_trailer(html: str) -> str:
    m = re.search(r"(?s).*(?:</[a-zA-Z][a-zA-Z0-9]*>|/>)", html)
    if not m:
        return html
    return m.group(0).rstrip()
