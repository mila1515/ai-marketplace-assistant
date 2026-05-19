import json
import os
from urllib.request import Request, urlopen

from src.repositories.marketplace import MarketplaceRepository
from src.schemas.marketplace import AskResponse
from src.core.config import get_settings
from src.services.rag import RAGIndexer


class MarketplaceAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repository = MarketplaceRepository()
        self.indexer = RAGIndexer()

    def answer_question(self, product_id: str, question: str) -> AskResponse:
        supporting_reviews = self.indexer.search(question=question, product_id=product_id)
        insight = self.repository.get_latest_insight(product_id)
        enrichment = self.repository.get_enrichment(product_id)

        insight_summary = insight.overall_summary if insight else "Aucune synthese disponible."
        context_reviews = supporting_reviews[:5]

        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
        if openai_key:
            answer = self._answer_with_openai(
                api_key=openai_key,
                product_id=product_id,
                question=question,
                insight_summary=insight_summary,
                enrichment=enrichment,
                supporting_reviews=context_reviews,
            )
        else:
            context = " ".join(context_reviews) if context_reviews else "Aucun avis pertinent retrouve."
            answer = f"Synthese produit : {insight_summary} Elements recuperes dans les avis : {context}"

        return AskResponse(
            product_id=product_id,
            question=question,
            answer=answer,
            supporting_reviews=supporting_reviews,
        )

    def _answer_with_openai(
        self,
        api_key: str,
        product_id: str,
        question: str,
        insight_summary: str,
        enrichment: dict | None,
        supporting_reviews: list[str],
    ) -> str:
        model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

        reviews_block = "\n".join(
            f"- {self._truncate(r, 700)}" for r in supporting_reviews if (r or "").strip()
        )
        enrichment_block = ""
        if enrichment and enrichment.get("matched"):
            ingredients = (enrichment.get("ingredients_text") or "").strip()
            enrichment_block = (
                f"Open Beauty Facts (match_score={enrichment.get('match_score')}): "
                f"{enrichment.get('obf_product_name') or ''} "
                f"brands={enrichment.get('obf_brands') or ''} "
                f"categories={enrichment.get('obf_categories') or ''} "
                f"labels={enrichment.get('obf_labels') or ''} "
                f"ingredients={self._truncate(ingredients, 900)}"
            ).strip()

        system_msg = (
            "Tu es un assistant data/IA. Tu reponds en francais, de facon courte et actionnable. "
            "Tu dois te baser uniquement sur le contexte fourni (synthese + avis + enrichissement). "
            "Si l'information n'est pas dans le contexte, dis-le."
        )
        user_msg = (
            f"Produit: {product_id}\n"
            f"Synthese: {insight_summary}\n"
            f"Enrichissement: {enrichment_block or 'Aucun'}\n"
            f"Avis pertinents:\n{reviews_block or '- Aucun'}\n\n"
            f"Question: {question}"
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.2,
            "max_tokens": 350,
        }

        try:
            req = Request(
                url="https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            content = (content or "").strip()
            if content:
                return content
        except Exception:
            pass

        context = " ".join(supporting_reviews[:3]) if supporting_reviews else "Aucun avis pertinent retrouve."
        return f"Synthese produit : {insight_summary} Elements recuperes dans les avis : {context}"

    def _truncate(self, text: str, max_chars: int) -> str:
        value = (text or "").strip()
        if len(value) <= max_chars:
            return value
        return value[: max_chars - 1] + "…"
