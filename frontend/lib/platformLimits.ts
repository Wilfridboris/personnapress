/**
 * Canonical platform character limits for PersonnaPress.
 *
 * Single source of truth for all platform hard limits and target ranges.
 * All frontend code that needs a platform character limit imports from here.
 *
 * Field-name mapping: x_post -> "x", linkedin_post -> "linkedin",
 * instagram_caption -> "instagram", facebook_post -> "facebook_page",
 * threads_post -> "threads".
 *
 * NOTE: X URL weighting is partial -- URLs count as 23 chars, but
 * emoji weighting and Unicode range weighting are NOT implemented
 * per story 26.1 spec. Full twitter-text weighting is out of scope.
 */

/** Hard limits enforced at generation, approval, and publish time. */
export const HARD_LIMITS: Record<string, number> = {
  x: 280,
  linkedin: 3000,
  instagram: 2200,
  facebook_page: 63206,
  threads: 500,
};

/** X counts every URL as 23 characters regardless of actual length. */
const X_URL_WEIGHT = 23;

/**
 * Regex for URL detection matching X's t.co wrapping behavior.
 * Same pattern used by the backend onboarding link detector.
 */
const URL_PATTERN = /https?:\/\/[^\s]+/g;

/**
 * Return the character count for a platform post.
 *
 * For X, URLs are replaced by a 23-char token before counting
 * (matching X's weighted count behavior for URLs).
 * For all other platforms, returns the Unicode code point count.
 *
 * NOTE: This implements URL weighting only. Emoji weighting and
 * Unicode range weighting are not implemented (out of scope per story 26.1).
 */
export function countChars(platform: string, text: string): number {
  if (!text) return 0;
  if (platform === "x") {
    const weighted = text.replace(URL_PATTERN, "x".repeat(X_URL_WEIGHT));
    return [...weighted].length;
  }
  return [...text].length;
}

/**
 * Return how many characters the text exceeds the hard limit.
 *
 * Returns 0 if within or at the limit.
 * Returns a positive integer indicating overage if over the limit.
 */
export function overLimit(platform: string, text: string): number {
  const limit = HARD_LIMITS[platform];
  if (limit === undefined) return 0;
  const count = countChars(platform, text);
  return Math.max(0, count - limit);
}

/** Danger threshold at 95% of the hard limit. */
export function dangerThreshold(platform: string): number {
  const limit = HARD_LIMITS[platform];
  if (limit === undefined) return 0;
  return Math.floor(limit * 0.95);
}
