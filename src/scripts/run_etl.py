import sys

from src.services.ingestion import IngestionService


def run_etl(csv_path: str) -> None:
    service = IngestionService()
    stats = service.ingest_csv(csv_path)
    print(f"Ingestion terminee: {stats['products']} produits, {stats['reviews']} avis.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m src.scripts.run_etl <csv_path>")
    run_etl(sys.argv[1])
