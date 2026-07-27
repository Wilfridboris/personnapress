UNLIMITED = 999_999

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "starter": {"clients": 2, "campaigns": 10, "image_gens": 10, "roadmaps": 1},
    "growth":  {"clients": 5, "campaigns": 30, "image_gens": 30, "roadmaps": 4},
    "agency":  {"clients": 20, "campaigns": UNLIMITED, "image_gens": 100, "roadmaps": UNLIMITED},
}


def get_stripe_price_to_tier() -> dict[str, str]:
    from app.core.config import settings
    return {
        settings.STRIPE_PRICE_STARTER: "starter",
        settings.STRIPE_PRICE_GROWTH: "growth",
        settings.STRIPE_PRICE_AGENCY: "agency",
    }
