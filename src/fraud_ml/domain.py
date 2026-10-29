"""Authoritative feature schema independent of generation and training."""

from collections.abc import Mapping

SCALES = {"EUR": 10000, "USD": 12000, "JPY": 15000}
DOMAINS = {c: (s // 20, s * 50) for c, s in SCALES.items()}
FEATURE_ORDER = ("log_amount_standardized", "currency_EUR", "currency_USD", "currency_JPY")


def validate_features(features: Mapping[str, object]) -> tuple[int, str]:
    if set(features) != {"amount_minor", "currency"}:
        raise ValueError("Features must contain only amount_minor and currency")
    amount, currency = features["amount_minor"], features["currency"]
    if type(amount) is not int or not 1 <= amount <= 10**12:
        raise ValueError("amount_minor must be a bounded strict integer")
    if not isinstance(currency, str) or currency not in SCALES:
        raise ValueError("Unsupported currency")
    if not SCALES[currency] // 20 <= amount <= SCALES[currency] * 50:
        raise ValueError("outside_training_domain")
    return amount, currency
