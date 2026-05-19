import json
from collections import Counter
from datetime import datetime

from sqlalchemy import select

from src.core.database import SessionLocal
from src.models.entities import Insight, Product, Review
from src.services.nlp import NLPProcessor


class InsightService:
    def __init__(self) -> None:
        self.nlp = NLPProcessor()

    def generate_product_insight(self, product_id: str) -> Insight | None:
        with SessionLocal() as session:
            product = session.get(Product, product_id)
            if product is None:
                return None

            reviews = session.scalars(
                select(Review).where(Review.product_id == product_id)
            ).all()
            if not reviews:
                return None

            positive_points: Counter[str] = Counter()
            negative_points: Counter[str] = Counter()
            raw_reviews = []

            for review in reviews:
                raw_reviews.append(review.review_text)
                aspects = self.nlp.extract_aspects(review.review_text)
                target = positive_points if (review.sentiment_label or "") == "positive" else negative_points
                target.update(aspects)

            recurring_topics = self.nlp.aggregate_topics(raw_reviews)
            positive = [item for item, _ in positive_points.most_common(3)]
            negative = [item for item, _ in negative_points.most_common(3)]

            summary = (
                f"{product.title} est globalement analyse a partir de {len(reviews)} avis. "
                f"Les points forts dominants sont {', '.join(positive) or 'non identifies'} ; "
                f"les critiques les plus frequentes concernent {', '.join(negative) or 'aucun point faible majeur'}."
            )

            insight = Insight(
                insight_id=f"INS_{product_id}",
                product_id=product_id,
                generated_at=datetime.utcnow(),
                positive_points=json.dumps(positive, ensure_ascii=True),
                negative_points=json.dumps(negative, ensure_ascii=True),
                recurring_topics=json.dumps(recurring_topics, ensure_ascii=True),
                overall_summary=summary,
                confidence_score=0.7,
                source_review_count=len(reviews),
            )
            persisted_insight = session.merge(insight)
            session.commit()
            session.refresh(persisted_insight)
            return persisted_insight
