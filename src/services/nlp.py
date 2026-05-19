import re
from collections import Counter


POSITIVE_WORDS = {
    "excellent",
    "bon",
    "bonne",
    "super",
    "top",
    "parfait",
    "confortable",
    "rapide",
    "solide",
    "great",
    "amazing",
    "love",
    "loved",
    "perfect",
    "works",
    "worked",
    "effective",
    "smooth",
    "soft",
    "gentle",
    "hydrating",
    "moisturizing",
    "glowing",
    "recommend",
    "favorite",
}

NEGATIVE_WORDS = {
    "mauvais",
    "nulle",
    "nul",
    "lent",
    "fragile",
    "instable",
    "decevant",
    "decevante",
    "probleme",
    "bad",
    "worst",
    "hate",
    "hated",
    "broken",
    "broke",
    "waste",
    "drying",
    "irritating",
    "irritation",
    "burn",
    "burning",
    "stinging",
    "itchy",
    "rash",
    "breakout",
    "breakouts",
    "pimples",
}

ASPECT_KEYWORDS = {
    "batterie": {"batterie", "autonomie", "charge"},
    "qualite_son": {"son", "audio", "micro"},
    "confort": {"confort", "leger", "ergonomique"},
    "prix": {"prix", "cher", "rapport"},
    "livraison": {"livraison", "colis", "retard"},
    "connectivite": {"bluetooth", "connexion", "connecte"},
    "hydration": {"hydration", "hydrate", "hydrating", "moisture", "moisturizing", "dry", "dryness", "dehydrate"},
    "irritation": {"irritation", "irritating", "burn", "burning", "sting", "stinging", "itch", "itchy", "rash", "redness"},
    "texture": {"texture", "sticky", "greasy", "oily", "lightweight", "thick", "absorb", "absorbs"},
    "scent": {"scent", "smell", "fragrance", "parfum", "odor"},
    "acne": {"acne", "pimples", "breakout", "breakouts", "comedones"},
    "packaging": {"packaging", "bottle", "pump", "dropper", "leak", "leaking"},
}


class NLPProcessor:
    """Simple heuristic NLP layer for the initial scaffold."""

    def normalize_text(self, text: str) -> str:
        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def detect_sentiment(self, text: str) -> tuple[str, float]:
        normalized = self.normalize_text(text)
        words = set(normalized.split())
        positive_hits = len(words & POSITIVE_WORDS)
        negative_hits = len(words & NEGATIVE_WORDS)
        score = float(positive_hits - negative_hits)

        if score > 0:
            return "positive", min(score / 3, 1.0)
        if score < 0:
            return "negative", max(score / 3, -1.0)
        return "neutral", 0.0

    def summarize_review(self, text: str, max_words: int = 18) -> str:
        normalized = self.normalize_text(text)
        words = normalized.split()
        return " ".join(words[:max_words])

    def extract_aspects(self, text: str) -> list[str]:
        normalized = self.normalize_text(text)
        tokens = set(normalized.split())
        matched = []
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if tokens & keywords:
                matched.append(aspect)
        return matched

    def aggregate_topics(self, reviews: list[str], top_k: int = 5) -> list[str]:
        counts: Counter[str] = Counter()
        for review in reviews:
            counts.update(self.extract_aspects(review))
        return [topic for topic, _ in counts.most_common(top_k)]
