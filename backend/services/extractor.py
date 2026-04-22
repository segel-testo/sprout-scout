import re
from typing import Iterable

VEGAN_KEYWORDS = [
    "vegan", "vegane", "veganes", "veganer",
    "plant-based", "plant based",
    "pflanzlich", "rein pflanzlich",
    "100% vegan", "100 % vegan",
    "veganes gericht",
    "tierfrei", "animal-free", "cruelty-free",
]

NEGATION_TOKENS = {
    "kein", "keine", "keinen", "keiner", "keines",
    "ohne", "no", "not", "without", "leider", "nicht",
}

ON_REQUEST_MARKERS = [
    "auf anfrage", "vegan auf wunsch", "vegan möglich",
    "on request", "vegan available", "vegan option", "vegan on demand",
]

LEGEND_PATTERNS = [
    re.compile(r"\(\s*([a-z0-9ⓥ★✱‡🌱]{1,3})\s*\)\s*=?\s*vegan", re.IGNORECASE),
    re.compile(r"([a-z0-9ⓥ★✱‡🌱]{1,3})\s*[=:\-–]\s*vegan", re.IGNORECASE),
    re.compile(r"([ⓥ★✱‡🌱])\s+vegan", re.IGNORECASE),
]

SPLIT_RE = re.compile(r"[\n\r.•|·;]+")


def extract_vegan_dishes(text: str, source: str) -> list[dict]:
    if not text:
        return []
    legend_symbols = _find_legend_symbols(text)
    dishes = []
    seen = set()
    for raw_line in SPLIT_RE.split(text):
        line = raw_line.strip()
        if len(line) < 3:
            continue
        confidence, matched = _score_line(line.lower(), legend_symbols)
        if confidence == 0:
            continue
        name = line[:120]
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        dishes.append({
            "name": name,
            "confidence": round(confidence, 2),
            "matched_keywords": matched,
            "source": source,
        })
    return dishes


def _find_legend_symbols(text: str) -> set[str]:
    symbols: set[str] = set()
    for pattern in LEGEND_PATTERNS:
        for match in pattern.finditer(text):
            symbol = match.group(1).strip().lower()
            if symbol and symbol not in {"vegan", "the", "is", "ist"}:
                symbols.add(symbol)
    return symbols


def _score_line(line_lower: str, legend_symbols: set[str]) -> tuple[float, list[str]]:
    for marker in ON_REQUEST_MARKERS:
        if marker in line_lower:
            return 0.3, [marker]

    matched: list[str] = []
    for kw in VEGAN_KEYWORDS:
        if _keyword_present_without_negation(line_lower, kw):
            matched.append(kw)

    for sym in legend_symbols:
        if _symbol_present(line_lower, sym):
            matched.append(f"legend:{sym}")

    if not matched:
        return 0.0, []

    if any(m.startswith("legend:") for m in matched):
        return min(1.0, 0.9 + 0.05 * (len(matched) - 1)), matched
    return min(1.0, 0.4 + 0.2 * len(matched)), matched


def _keyword_present_without_negation(line_lower: str, keyword: str) -> bool:
    start = 0
    while True:
        idx = line_lower.find(keyword, start)
        if idx == -1:
            return False
        prefix = line_lower[max(0, idx - 40):idx]
        prefix_words = re.findall(r"[a-zäöüß]+", prefix)
        if not any(tok in NEGATION_TOKENS for tok in prefix_words[-4:]):
            return True
        start = idx + len(keyword)


def _symbol_present(line_lower: str, symbol: str) -> bool:
    sym = symbol.lower()
    if len(sym) <= 2 and sym.isalnum():
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(sym)}(?![a-z0-9])", line_lower))
    return sym in line_lower
