import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select

from src.core.config import get_settings
from src.core.database import SessionLocal, init_db
from src.models.entities import Product, ProductEnrichment, Review
from src.services.etl import ETLPipeline
from src.services.insights import InsightService
from src.services.nlp import NLPProcessor
from src.services.rag import RAGIndexer


class IngestionService:
    """End-to-end ingestion service from CSV to SQL, RAG and insights."""

    def __init__(self) -> None:
        self.etl = ETLPipeline()
        self.nlp = NLPProcessor()
        self.rag = RAGIndexer()
        self.insight_service = InsightService()

    def ingest_csv(self, csv_path: str) -> dict[str, int]:
        init_db()
        frame = self.etl.extract_csv(csv_path)
        frame = self.etl.clean_reviews(frame)
        frame = self.etl.transform(frame)
        self._persist_processed_csv(frame, csv_path)

        products_seen: set[str] = set()
        reviews_for_index: list[dict] = []

        with SessionLocal() as session:
            for row in frame.to_dict(orient="records"):
                if row["product_id"] not in products_seen:
                    product = Product(
                        product_id=row["product_id"],
                        source_id=row.get("source_id"),
                        title=row["product_title"],
                        brand=row.get("brand"),
                        category=row.get("category"),
                        price=row.get("price"),
                        currency=row.get("currency", "EUR"),
                        avg_rating=row.get("avg_rating"),
                        review_count=int(row.get("review_count", 0) or 0),
                        marketplace=row.get("marketplace"),
                        created_at=datetime.utcnow(),
                    )
                    session.merge(product)
                    products_seen.add(row["product_id"])

                sentiment_label, sentiment_score = self.nlp.detect_sentiment(row["review_text"])
                review = Review(
                    review_id=row["review_id"],
                    product_id=row["product_id"],
                    author_name=row.get("author_name"),
                    rating=row.get("rating"),
                    review_title=row.get("review_title"),
                    review_text=row["review_text"],
                    review_date=row.get("review_date"),
                    verified_purchase=bool(row.get("verified_purchase", False)),
                    language=row.get("language", "fr"),
                    sentiment_label=sentiment_label,
                    sentiment_score=sentiment_score,
                    summary_short=self.nlp.summarize_review(row["review_text"]),
                    source_url=row.get("source_url"),
                    created_at=datetime.utcnow(),
                )

                session.merge(review)
                reviews_for_index.append(
                    {
                        "review_id": row["review_id"],
                        "product_id": row["product_id"],
                        "rating": row.get("rating"),
                        "review_text": row["review_text"],
                        "sentiment_label": sentiment_label,
                    }
                )

            session.commit()

        self.rag.add_reviews(reviews_for_index)

        for product_id in products_seen:
            self.insight_service.generate_product_insight(product_id)

        return {"products": len(products_seen), "reviews": len(reviews_for_index)}

    def _persist_processed_csv(self, frame, csv_path: str) -> Path:
        settings = get_settings()
        processed_dir = Path(settings.data_processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(csv_path)
        out_path = processed_dir / f"{source_path.stem}_processed.csv"
        frame.to_csv(out_path, index=False, encoding="utf-8")
        return out_path

    def enrich_products_open_beauty_facts(self, limit: int = 50, force: bool = False) -> dict[str, int]:
        init_db()

        with SessionLocal() as session:
            query = select(Product).where(Product.marketplace == "Sephora")
            if not force:
                query = query.where(
                    Product.product_id.not_in(select(ProductEnrichment.product_id))
                )
            products = session.scalars(query.limit(limit)).all()

        matched = 0
        processed = 0

        with SessionLocal() as session:
            for product in products:
                processed += 1
                result = self._open_beauty_facts_search(product_title=product.title, brand=product.brand)
                enrichment = ProductEnrichment(
                    product_id=product.product_id,
                    provider="open_beauty_facts",
                    matched=bool(result.get("matched")),
                    match_score=result.get("match_score"),
                    obf_code=result.get("code"),
                    obf_product_name=result.get("product_name"),
                    obf_brands=result.get("brands"),
                    obf_categories=result.get("categories"),
                    obf_labels=result.get("labels"),
                    ingredients_text=result.get("ingredients_text"),
                    source_url=result.get("url"),
                    raw_json=result.get("raw_json"),
                    updated_at=datetime.utcnow(),
                )
                session.merge(enrichment)
                if enrichment.matched:
                    matched += 1

            session.commit()

        return {"processed": processed, "matched": matched}

    def _open_beauty_facts_search(self, product_title: str, brand: str | None) -> dict:
        query = " ".join([part for part in [brand or "", product_title] if part]).strip()
        if not query:
            return {"matched": False, "match_score": 0.0}

        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": "code,product_name,brands,categories,labels,ingredients_text,url",
        }
        url = "https://world.openbeautyfacts.org/cgi/search.pl?" + urlencode(params)
        data = self._fetch_json(url)
        products = data.get("products") if isinstance(data, dict) else None
        if not products:
            return {"matched": False, "match_score": 0.0}

        query_tokens = self._tokenize(query)
        best = None
        best_score = 0.0

        for item in products:
            candidate_text = " ".join(
                [
                    str(item.get("product_name") or ""),
                    str(item.get("brands") or ""),
                    str(item.get("categories") or ""),
                ]
            )
            cand_tokens = self._tokenize(candidate_text)
            if not query_tokens or not cand_tokens:
                continue
            overlap = len(set(query_tokens) & set(cand_tokens))
            score = overlap / max(len(set(query_tokens)), 1)
            if score > best_score:
                best_score = score
                best = item

        threshold = 0.25
        matched = bool(best and best_score >= threshold and (best.get("product_name") or "").strip())

        if not best:
            return {"matched": False, "match_score": best_score}

        return {
            "matched": matched,
            "match_score": round(float(best_score), 3),
            "code": best.get("code"),
            "product_name": best.get("product_name"),
            "brands": best.get("brands"),
            "categories": best.get("categories"),
            "labels": best.get("labels"),
            "ingredients_text": best.get("ingredients_text"),
            "url": best.get("url"),
            "raw_json": json.dumps(best, ensure_ascii=True),
        }

    def _fetch_json(self, url: str) -> dict:
        req = Request(url, headers={"User-Agent": "ai-marketplace-assistant/1.0"}, method="GET")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _tokenize(self, text: str) -> list[str]:
        normalized = (text or "").lower()
        normalized = re.sub(r"[^a-z0-9\\s]", " ", normalized)
        normalized = re.sub(r"\\s+", " ", normalized).strip()
        return [t for t in normalized.split() if len(t) > 2]
