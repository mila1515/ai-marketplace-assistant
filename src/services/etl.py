from pathlib import Path

import pandas as pd


class ETLPipeline:
    """Small ETL helper for MVP CSV ingestion."""

    required_columns = {
        "product_id",
        "product_title",
        "category",
        "review_id",
        "review_text",
        "rating",
    }

    def extract_csv(self, csv_path: str | Path) -> pd.DataFrame:
        frame = pd.read_csv(csv_path)
        if self.required_columns.issubset(set(frame.columns)):
            return frame
        return self._normalize_sephora_csv(frame)

    def clean_reviews(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = self.required_columns - set(frame.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        cleaned = frame.copy()
        cleaned["review_text"] = (
            cleaned["review_text"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        )
        cleaned = cleaned.dropna(subset=["product_id", "review_id", "review_text"])
        cleaned = cleaned[cleaned["review_text"].str.len() > 10]
        cleaned = cleaned.drop_duplicates(subset=["review_id"])
        return cleaned

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        transformed = frame.copy()
        transformed = self._ensure_column(transformed, "review_title", "")
        transformed = self._ensure_column(transformed, "brand", "Unknown")
        transformed = self._ensure_column(transformed, "marketplace", "dataset")
        transformed = self._ensure_column(transformed, "currency", "EUR")
        transformed = self._ensure_column(transformed, "language", "fr")
        transformed = self._coerce_review_date(transformed)
        transformed = self._coerce_verified_purchase(transformed)
        return transformed

    def _ensure_column(
        self,
        frame: pd.DataFrame,
        column_name: str,
        default_value: str,
    ) -> pd.DataFrame:
        if column_name not in frame.columns:
            frame[column_name] = default_value
        else:
            frame[column_name] = frame[column_name].fillna(default_value)
        return frame

    def _coerce_review_date(self, frame: pd.DataFrame) -> pd.DataFrame:
        if "review_date" not in frame.columns:
            return frame
        parsed = pd.to_datetime(frame["review_date"], errors="coerce")
        frame["review_date"] = parsed.dt.date
        return frame

    def _coerce_verified_purchase(self, frame: pd.DataFrame) -> pd.DataFrame:
        if "verified_purchase" not in frame.columns:
            return frame
        normalized = (
            frame["verified_purchase"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False})
        )
        frame["verified_purchase"] = normalized.fillna(False).astype(bool)
        return frame

    def _normalize_sephora_csv(self, frame: pd.DataFrame) -> pd.DataFrame:
        sephora_required = {"Product", "Brand", "Category", "Rating_Stars", "Review"}
        if not sephora_required.issubset(set(frame.columns)):
            missing = self.required_columns - set(frame.columns)
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        normalized = frame.copy()
        normalized["product_title"] = normalized["Product"].astype(str).fillna("").str.strip()
        normalized["brand"] = normalized["Brand"].astype(str).fillna("Unknown").str.strip()
        normalized["category"] = normalized["Category"].astype(str).fillna("Skincare").str.strip()
        normalized["rating"] = pd.to_numeric(normalized["Rating_Stars"], errors="coerce")
        normalized["review_text"] = (
            normalized["Review"]
            .astype(str)
            .str.replace("…read more", "", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        if "Product_id" in normalized.columns:
            normalized["product_id"] = normalized["Product_id"].astype(str).str.strip()
        else:
            normalized["product_id"] = (
                normalized["brand"].astype(str).str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True)
                + "__"
                + normalized["product_title"]
                .astype(str)
                .str.lower()
                .str.replace(r"[^a-z0-9]+", "_", regex=True)
            )

        if "User_id" in normalized.columns:
            normalized["review_id"] = (
                "SEPH_"
                + normalized["product_id"].astype(str)
                + "_"
                + normalized["User_id"].astype(str).str.strip()
                + "_"
                + normalized.index.astype(str)
            )
        else:
            normalized["review_id"] = "SEPH_" + normalized["product_id"].astype(str) + "_" + normalized.index.astype(str)

        if "Product_Url" in normalized.columns:
            normalized["source_url"] = normalized["Product_Url"].astype(str).fillna("").str.strip()

        if "Price" in normalized.columns:
            normalized["price"] = pd.to_numeric(normalized["Price"], errors="coerce")
            normalized["currency"] = "USD"

        normalized["marketplace"] = "Sephora"
        normalized["language"] = "en"
        normalized["verified_purchase"] = False

        columns = [
            "product_id",
            "product_title",
            "category",
            "review_id",
            "review_text",
            "rating",
            "brand",
            "marketplace",
            "price",
            "currency",
            "language",
            "source_url",
        ]
        present = [c for c in columns if c in normalized.columns]
        return normalized[present]
