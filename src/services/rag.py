import json
import re
from collections.abc import Iterable
from pathlib import Path

from src.core.config import get_settings


class RAGIndexer:
    def __init__(self) -> None:
        settings = get_settings()
        self.store_dir = Path(settings.vector_store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "reviews_index.json"
        self._index = self._load_index()

    def add_reviews(self, items: Iterable[dict]) -> None:
        for item in items:
            self._index[item["review_id"]] = {
                "review_id": item["review_id"],
                "product_id": item["product_id"],
                "review_text": item["review_text"],
                "rating": float(item.get("rating", 0) or 0),
                "sentiment_label": item.get("sentiment_label", "unknown"),
                "tokens": self._tokenize(item["review_text"]),
            }
        self._persist_index()

    def search(self, question: str, product_id: str, top_k: int | None = None) -> list[str]:
        settings = get_settings()
        n_results = top_k or settings.default_top_k
        query_tokens = set(self._tokenize(question))
        scored_reviews: list[tuple[float, str]] = []

        for item in self._index.values():
            if item["product_id"] != product_id:
                continue

            review_tokens = set(item["tokens"])
            overlap_score = len(query_tokens & review_tokens)
            rating_bonus = float(item.get("rating", 0)) / 10
            total_score = overlap_score + rating_bonus

            if total_score > 0:
                scored_reviews.append((total_score, item["review_text"]))

        scored_reviews.sort(key=lambda row: row[0], reverse=True)
        if scored_reviews:
            return [review for _, review in scored_reviews[:n_results]]

        fallback_reviews = [
            item["review_text"]
            for item in self._index.values()
            if item["product_id"] == product_id
        ]
        return fallback_reviews[:n_results]

    def _load_index(self) -> dict[str, dict]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _persist_index(self) -> None:
        self.index_path.write_text(
            json.dumps(self._index, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _tokenize(self, text: str) -> list[str]:
        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return [token for token in normalized.split() if len(token) > 2]
