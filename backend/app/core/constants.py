PLAN_LIMITS: dict[str, dict[str, int]] = {
    "starter": {"clients": 3, "campaigns": 10, "image_gens": 10},
    "growth":  {"clients": 5, "campaigns": 30, "image_gens": 30},
    "agency":  {"clients": 15, "campaigns": 100, "image_gens": 100},
}


def get_stripe_price_to_tier() -> dict[str, str]:
    from app.core.config import settings
    return {
        settings.STRIPE_PRICE_STARTER: "starter",
        settings.STRIPE_PRICE_GROWTH: "growth",
        settings.STRIPE_PRICE_AGENCY: "agency",
    }
