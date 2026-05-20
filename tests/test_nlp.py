from src.services.nlp import NLPProcessor
from src.services.etl import ETLPipeline
import pandas as pd


def test_detect_sentiment_positive() -> None:
    processor = NLPProcessor()
    label, score = processor.detect_sentiment("Excellent produit tres confortable")
    assert label == "positive"
    assert score > 0


def test_extract_aspects() -> None:
    processor = NLPProcessor()
    aspects = processor.extract_aspects("La batterie est faible mais le son est excellent")
    assert "batterie" in aspects
    assert "qualite_son" in aspects


def test_etl_transform_adds_optional_columns() -> None:
    pipeline = ETLPipeline()
    frame = pd.DataFrame(
        [
            {
                "product_id": "PRD_001",
                "product_title": "Produit demo",
                "category": "Audio",
                "review_id": "REV_001",
                "review_text": "Excellent son et batterie correcte",
                "rating": 4,
            }
        ]
    )
    transformed = pipeline.transform(frame)
    assert transformed.loc[0, "review_title"] == ""
    assert transformed.loc[0, "brand"] == "Unknown"
    assert transformed.loc[0, "marketplace"] == "dataset"
