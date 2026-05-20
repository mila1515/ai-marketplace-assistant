import json

from sqlalchemy import func, select

from src.core.database import SessionLocal
from src.models.entities import Insight, Product, ProductEnrichment, Review
from src.schemas.marketplace import InsightSummary, ProductSummary


class MarketplaceRepository:
    def list_products(self) -> list[ProductSummary]:
        with SessionLocal() as session:
            rows = session.execute(
                select(
                    Product.product_id,
                    Product.title,
                    Product.category,
                    Product.brand,
                    Product.marketplace,
                    func.avg(Review.rating).label("avg_rating"),
                    func.count(Review.review_id).label("review_count"),
                )
                .join(Review, Review.product_id == Product.product_id, isouter=True)
                .group_by(
                    Product.product_id,
                    Product.title,
                    Product.category,
                    Product.brand,
                    Product.marketplace,
                )
                .order_by(func.count(Review.review_id).desc(), Product.created_at.desc())
            ).all()

            return [
                ProductSummary(
                    product_id=product_id,
                    title=title,
                    category=category,
                    brand=brand,
                    avg_rating=float(avg_rating) if avg_rating is not None else None,
                    review_count=int(review_count or 0),
                    marketplace=marketplace,
                )
                for (
                    product_id,
                    title,
                    category,
                    brand,
                    marketplace,
                    avg_rating,
                    review_count,
                ) in rows
            ]

    def get_latest_insight(self, product_id: str) -> InsightSummary | None:
        with SessionLocal() as session:
            insight = session.scalars(
                select(Insight)
                .where(Insight.product_id == product_id)
                .order_by(Insight.generated_at.desc())
            ).first()
            if insight is None or insight.overall_summary is None:
                return None

            return InsightSummary(
                product_id=product_id,
                overall_summary=insight.overall_summary,
                positive_points=json.loads(insight.positive_points or "[]"),
                negative_points=json.loads(insight.negative_points or "[]"),
                recurring_topics=json.loads(insight.recurring_topics or "[]"),
                source_review_count=insight.source_review_count,
            )

    def get_recent_reviews(self, product_id: str, limit: int = 15) -> list[dict]:
        with SessionLocal() as session:
            reviews = session.scalars(
                select(Review)
                .where(Review.product_id == product_id)
                .order_by(Review.created_at.desc())
                .limit(limit)
            ).all()
            return [
                {
                    "review_id": r.review_id,
                    "rating": r.rating,
                    "sentiment_label": r.sentiment_label,
                    "sentiment_score": r.sentiment_score,
                    "review_text": r.review_text,
                    "review_title": r.review_title,
                    "review_date": r.review_date.isoformat() if r.review_date else None,
                }
                for r in reviews
            ]

    def get_sentiment_counts(self, product_id: str) -> dict[str, int]:
        with SessionLocal() as session:
            rows = session.execute(
                select(Review.sentiment_label, func.count(Review.review_id))
                .where(Review.product_id == product_id)
                .group_by(Review.sentiment_label)
            ).all()
            return {str(label or "unknown"): int(count) for label, count in rows}

    def get_global_sentiment_counts(self) -> dict[str, int]:
        with SessionLocal() as session:
            rows = session.execute(
                select(Review.sentiment_label, func.count(Review.review_id)).group_by(Review.sentiment_label)
            ).all()
            return {str(label or "unknown"): int(count) for label, count in rows}

    def get_enrichment(self, product_id: str) -> dict | None:
        with SessionLocal() as session:
            enrichment = session.get(ProductEnrichment, product_id)
            if enrichment is None:
                return None
            return {
                "product_id": enrichment.product_id,
                "provider": enrichment.provider,
                "matched": enrichment.matched,
                "match_score": enrichment.match_score,
                "obf_code": enrichment.obf_code,
                "obf_product_name": enrichment.obf_product_name,
                "obf_brands": enrichment.obf_brands,
                "obf_categories": enrichment.obf_categories,
                "obf_labels": enrichment.obf_labels,
                "ingredients_text": enrichment.ingredients_text,
                "source_url": enrichment.source_url,
                "updated_at": enrichment.updated_at.isoformat() if enrichment.updated_at else None,
            }

    def get_enrichment_stats(self) -> dict[str, int]:
        with SessionLocal() as session:
            total = session.execute(select(func.count(Product.product_id))).scalar_one()
            enriched = session.execute(select(func.count(ProductEnrichment.product_id))).scalar_one()
            matched = session.execute(
                select(func.count(ProductEnrichment.product_id)).where(ProductEnrichment.matched.is_(True))
            ).scalar_one()
            return {"products_total": int(total), "products_enriched": int(enriched), "products_matched": int(matched)}

    def get_enriched_reviews(self) -> list[dict]:
        with SessionLocal() as session:
            rows = session.execute(
                select(
                    Review.review_id,
                    Review.product_id,
                    Review.rating,
                    Review.sentiment_label,
                    Review.review_text,
                    Product.title,
                    Product.brand,
                    Product.category,
                    ProductEnrichment.matched,
                    ProductEnrichment.match_score,
                    ProductEnrichment.obf_labels,
                    ProductEnrichment.ingredients_text,
                )
                .join(Product, Product.product_id == Review.product_id)
                .join(ProductEnrichment, ProductEnrichment.product_id == Product.product_id, isouter=True)
                .where(Product.marketplace == "Sephora")
            ).all()

            return [
                {
                    "review_id": review_id,
                    "product_id": product_id,
                    "rating": float(rating) if rating is not None else None,
                    "sentiment_label": sentiment_label or "unknown",
                    "review_text": review_text,
                    "product_title": title,
                    "brand": brand,
                    "category": category,
                    "matched": bool(matched) if matched is not None else False,
                    "match_score": float(match_score) if match_score is not None else None,
                    "labels": obf_labels,
                    "ingredients_text": ingredients_text,
                }
                for (
                    review_id,
                    product_id,
                    rating,
                    sentiment_label,
                    review_text,
                    title,
                    brand,
                    category,
                    matched,
                    match_score,
                    obf_labels,
                    ingredients_text,
                ) in rows
            ]
