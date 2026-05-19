from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    avg_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    marketplace: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reviews: Mapped[list["Review"]] = relationship(back_populates="product")
    insights: Mapped[list["Insight"]] = relationship(back_populates="product")
    enrichment: Mapped["ProductEnrichment"] = relationship(back_populates="product", uselist=False)


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    author_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_short: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="reviews")


class Insight(Base):
    __tablename__ = "insights"

    insight_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    positive_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_review_count: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="insights")


class ProductEnrichment(Base):
    __tablename__ = "product_enrichment"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.product_id"), primary_key=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), default="open_beauty_facts")
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    obf_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    obf_product_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    obf_brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    obf_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    obf_labels: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingredients_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="enrichment")
