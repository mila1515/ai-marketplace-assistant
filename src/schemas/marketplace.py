from pydantic import BaseModel


class ProductSummary(BaseModel):
    product_id: str
    title: str
    category: str | None = None
    brand: str | None = None
    avg_rating: float | None = None
    review_count: int = 0
    marketplace: str | None = None


class InsightSummary(BaseModel):
    product_id: str
    overall_summary: str
    positive_points: list[str]
    negative_points: list[str]
    recurring_topics: list[str]
    source_review_count: int


class AskResponse(BaseModel):
    product_id: str
    question: str
    answer: str
    supporting_reviews: list[str]

