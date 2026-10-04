import re

# Canonical bank keys so that "Monobank", "Monobank (Card)" and "Monobank (IBAN)"
# from different exchanges compare as the same payment method.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (key, re.compile(pattern, re.IGNORECASE))
    for key, pattern in [
        ("monobank", r"mono"),
        ("privatbank", r"privat|приват"),
        ("pumb", r"pumb|пумб"),
        ("a-bank", r"\ba-?bank\b|^abank|а-банк"),
        ("sense", r"sense|alfa|альфа"),
        ("raiffeisen", r"raif"),
        ("oschadbank", r"oschad|ощад"),
        ("izibank", r"izi"),
        ("ukrsibbank", r"ukrsib"),
        ("otp", r"\botp\b"),
        ("ukrgasbank", r"ukrgas"),
        ("ukreximbank", r"ukrexim"),
        ("revolut", r"revolut"),
        ("bank transfer", r"bank ?transfer|^bank$|^iban$"),
    ]
]


def normalize_payment(name: str) -> str:
    text = name.strip()
    for key, pattern in _PATTERNS:
        if pattern.search(text):
            return key
    return text.lower()


def normalize_payments(names: list[str]) -> set[str]:
    return {normalize_payment(x) for x in names if x and x.strip()}
