# Product Requirements Document (PRD): PersonaPress
**Vision:** Every content-driven founder, coach, and agency owner in North America publishes SEO-ranked blog posts and social campaigns weekly — written in their authentic voice — without hiring a writer, through PersonaPress.

## 1. Core Concept & USP
PersonaPress is an autonomous content engine designed to eliminate "AI slop." Users input a raw "brain dump" (voice note or bullet points), and the agent formats it into a highly structured SEO blog post and a matching multi-platform social campaign. 
**USP:** "Your Ideas, Published and Ranked — In Your Voice, Not AI's."

## 2. Target Audience & Problem
* **Target:** SaaS Founders, Business Coaches, Marketing Agencies.
* **Problem:** Time scarcity (3-6 hours per article), generic AI voice, lack of SEO structure, siloed workflows (blogging but failing to cross-post to social).
* **The Solution:** A local/cloud-hybrid LLM agent that learns the user's exact writing style from past content, requires only a "brain dump," and never publishes without a human-in-the-loop approval.

## 3. Platform Rollout Strategy (Day-1 Approvals)
To ensure immediate usability without waiting for lengthy manual app reviews, Phase 1 integrates only platforms with self-serve or instant API access:
1. **WordPress:** Instant via Application Passwords.
2. **Webflow:** Instant via CMS API Bearer Tokens.
3. **X (Twitter):** Instant via Developer Portal (Free/Basic Tier OAuth 2.0).
4. **LinkedIn:** Instant for Personal Profiles (via "Share on LinkedIn" self-serve product).
*(Note: Meta/Instagram/Threads require screencast audits. They are architected in the DB but deferred to Phase 2 for publishing).*

## 4. Key Workflows
1. **Brand Ingestion:** Scrape website URL + parse uploaded historical text to extract Tone, Cadence, and "Banned Jargon" into a JSON profile.
2. **Brain Dump:** User inputs a raw thought.
3. **Draft Generation:** Hermes Agent writes the blog (HTML) and social posts (Text).
4. **Media Generation:** Replicate (FLUX.1-dev) generates a custom featured image.
5. **Approval Gate:** Post stays in 'Pending' until user clicks 'Approve'.
6. **Publishing:** System natively hits WordPress/Webflow and X/LinkedIn APIs.