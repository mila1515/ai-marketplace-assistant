from fastapi import FastAPI, HTTPException

from src.agents.marketplace_agent import MarketplaceAgent
from src.core.config import get_settings
from src.core.database import init_db
from src.repositories.marketplace import MarketplaceRepository
from src.services.ingestion import IngestionService

settings = get_settings()
app = FastAPI(title=settings.app_name)
repository = MarketplaceRepository()
agent = MarketplaceAgent()
ingestion_service = IngestionService()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/products")
def list_products() -> list[dict]:
    return [product.model_dump() for product in repository.list_products()]


@app.get("/products/{product_id}/insight")
def get_product_insight(product_id: str) -> dict:
    insight = repository.get_latest_insight(product_id)
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight.model_dump()


@app.get("/products/{product_id}/ask")
def ask_product(product_id: str, question: str) -> dict:
    return agent.answer_question(product_id=product_id, question=question).model_dump()


@app.post("/admin/ingest")
def ingest_csv(csv_path: str) -> dict[str, int]:
    return ingestion_service.ingest_csv(csv_path)


@app.post("/admin/enrich-openbeautyfacts")
def enrich_openbeautyfacts(limit: int = 50, force: bool = False) -> dict[str, int]:
    return ingestion_service.enrich_products_open_beauty_facts(limit=limit, force=force)
