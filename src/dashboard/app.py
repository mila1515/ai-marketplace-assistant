import os

import pandas as pd
import plotly.express as px
import streamlit as st

from src.agents.marketplace_agent import MarketplaceAgent
from src.core.database import init_db
from src.repositories.marketplace import MarketplaceRepository
from src.services.ingestion import IngestionService


def main() -> None:
    init_db()
    repository = MarketplaceRepository()
    agent = MarketplaceAgent()
    ingestion_service = IngestionService()

    st.set_page_config(page_title="AI Marketplace Assistant", layout="wide")
    st.title("AI Marketplace Assistant")
    st.caption("Dashboard MVP pour explorer les produits, avis, enrichissement et chat IA.")

    products = repository.list_products()
    if not products:
        st.warning(
            "Aucun produit en base pour l'instant. Lancez l'ETL d'abord (ex: python -m src.scripts.run_etl data/raw/sephora_skindataall.csv)."
        )
        return

    product_df = pd.DataFrame([item.model_dump() for item in products])
    product_df["avg_rating"] = pd.to_numeric(product_df["avg_rating"], errors="coerce")
    product_df["review_count"] = pd.to_numeric(product_df["review_count"], errors="coerce").fillna(0).astype(int)

    tab_dashboard, tab_produit, tab_insights, tab_chat, tab_enrich = st.tabs(
        ["Dashboard", "Produit", "Insights", "Chat IA", "Enrichissement"]
    )

    with tab_dashboard:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Produits", len(product_df))
        col2.metric("Avis total", int(product_df["review_count"].sum()))
        col3.metric("Note moyenne", round(float(product_df["avg_rating"].fillna(0).mean()), 2))
        col4.metric("OpenAI", "OK" if (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")) else "Non configure")

        sentiment_counts = repository.get_global_sentiment_counts()
        if sentiment_counts:
            st.subheader("Sentiment global")
            sentiment_df = pd.DataFrame(
                [{"sentiment": k, "count": v} for k, v in sentiment_counts.items()]
            ).sort_values("count", ascending=False)
            fig = px.bar(sentiment_df, x="sentiment", y="count", title="Sentiment (tous avis)")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Catalogue")
        category_filter = st.selectbox(
            "Categorie",
            options=["Toutes"] + sorted(product_df["category"].dropna().unique().tolist()),
        )
        filtered_df = (
            product_df if category_filter == "Toutes" else product_df[product_df["category"] == category_filter]
        )
        st.dataframe(
            filtered_df[["title", "brand", "category", "avg_rating", "review_count", "marketplace"]],
            use_container_width=True,
        )

        st.subheader("Distribution des notes")
        fig = px.histogram(
            filtered_df.dropna(subset=["avg_rating"]),
            x="avg_rating",
            nbins=10,
            title="Distribution des notes moyennes",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_produit:
        category_filter = st.selectbox(
            "Categorie (vue produit)",
            options=["Toutes"] + sorted(product_df["category"].dropna().unique().tolist()),
            key="category_filter_product",
        )
        filtered_df = (
            product_df if category_filter == "Toutes" else product_df[product_df["category"] == category_filter]
        )
        selected_product = st.selectbox(
            "Produit a analyser",
            options=filtered_df["product_id"].tolist(),
            format_func=lambda pid: (filtered_df.loc[filtered_df["product_id"] == pid, "title"].iloc[0]),
        )
        product_row = filtered_df.loc[filtered_df["product_id"] == selected_product].iloc[0]

        cols = st.columns(4)
        cols[0].metric("Note moyenne", round(float(product_row["avg_rating"] or 0), 2))
        cols[1].metric("Avis", int(product_row["review_count"] or 0))
        cols[2].metric("Marque", str(product_row.get("brand") or ""))
        cols[3].metric("Categorie", str(product_row.get("category") or ""))

        enrichment = repository.get_enrichment(selected_product)
        if enrichment:
            st.subheader("Enrichissement Open Beauty Facts")
            st.write(
                {
                    "matched": enrichment.get("matched"),
                    "match_score": enrichment.get("match_score"),
                    "obf_product_name": enrichment.get("obf_product_name"),
                    "obf_brands": enrichment.get("obf_brands"),
                    "obf_categories": enrichment.get("obf_categories"),
                    "obf_labels": enrichment.get("obf_labels"),
                    "source_url": enrichment.get("source_url"),
                }
            )
            if enrichment.get("ingredients_text"):
                st.write("Ingredients :", enrichment["ingredients_text"])
        else:
            st.info("Aucun enrichissement pour ce produit pour l'instant.")

        insight = repository.get_latest_insight(selected_product)
        if insight:
            st.subheader("Synthese IA")
            st.write(insight.overall_summary)
            st.write("Points forts :", ", ".join(insight.positive_points) or "Aucun")
            st.write("Points faibles :", ", ".join(insight.negative_points) or "Aucun")
            st.write("Themes recurrents :", ", ".join(insight.recurring_topics) or "Aucun")

        sentiment_counts = repository.get_sentiment_counts(selected_product)
        if sentiment_counts:
            st.subheader("Sentiment (produit)")
            sentiment_df = pd.DataFrame(
                [{"sentiment": k, "count": v} for k, v in sentiment_counts.items()]
            ).sort_values("count", ascending=False)
            fig = px.bar(sentiment_df, x="sentiment", y="count", title="Sentiment (produit)")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Avis recents")
        recent = repository.get_recent_reviews(selected_product, limit=12)
        if recent:
            st.dataframe(pd.DataFrame(recent), use_container_width=True)
        else:
            st.info("Aucun avis trouve pour ce produit.")

    with tab_insights:
        st.subheader("Insights Ingredients / Labels")
        stats = repository.get_enrichment_stats()
        st.write(stats)

        enriched_rows = repository.get_enriched_reviews()
        if not enriched_rows:
            st.warning("Aucune donnee disponible.")
        else:
            df = pd.DataFrame(enriched_rows)
            df["sentiment_label"] = df["sentiment_label"].fillna("unknown")

            matched_only = st.checkbox("Analyser uniquement les produits matches Open Beauty Facts", value=True)
            min_reviews = int(
                st.number_input(
                    "Seuil minimum d'avis par groupe",
                    min_value=10,
                    max_value=5000,
                    value=80,
                    step=10,
                )
            )

            analysis_df = df[df["matched"] == True] if matched_only else df
            if analysis_df.empty:
                st.info(
                    "Pas assez de donnees enrichies pour l'analyse. Lance l'enrichissement sur plus de produits."
                )
            else:
                analysis_df["ingredients_text"] = analysis_df["ingredients_text"].fillna("").astype(str)
                ingredients_lower = analysis_df["ingredients_text"].str.lower()

                keyword_sets = {
                    "fragrance": ["fragrance", "parfum", "perfume"],
                    "alcohol": ["alcohol", "alcohol denat", "ethanol"],
                    "retinol": ["retinol"],
                    "niacinamide": ["niacinamide", "nicotinamide"],
                    "hyaluronic_acid": ["hyaluronic", "sodium hyaluronate"],
                    "vitamin_c": ["ascorbic", "vitamin c", "ascorbyl"],
                    "salicylic_acid": ["salicylic", "bha"],
                }

                for key, terms in keyword_sets.items():
                    mask = False
                    for t in terms:
                        mask = mask | ingredients_lower.str.contains(t, regex=False)
                    analysis_df[key] = mask

                analysis_df["is_negative"] = (
                    analysis_df["sentiment_label"].astype(str).str.lower().eq("negative")
                )
                analysis_df["is_positive"] = (
                    analysis_df["sentiment_label"].astype(str).str.lower().eq("positive")
                )

                rows = []
                for key in keyword_sets.keys():
                    for flag_value, name in [(True, "avec"), (False, "sans")]:
                        part = analysis_df[analysis_df[key] == flag_value]
                        if len(part) < min_reviews:
                            continue
                        avg_rating = float(pd.to_numeric(part["rating"], errors="coerce").mean())
                        neg_rate = float(part["is_negative"].mean())
                        pos_rate = float(part["is_positive"].mean())
                        rows.append(
                            {
                                "feature": key,
                                "groupe": name,
                                "avis": int(len(part)),
                                "note_moy": round(avg_rating, 2) if avg_rating == avg_rating else None,
                                "taux_negatif": round(neg_rate, 3),
                                "taux_positif": round(pos_rate, 3),
                            }
                        )

                if rows:
                    feat_df = pd.DataFrame(rows).sort_values(["feature", "groupe"])
                    st.subheader("Impact ingredients (proxy)")
                    st.dataframe(feat_df, use_container_width=True)

                    fig = px.bar(
                        feat_df,
                        x="feature",
                        y="taux_negatif",
                        color="groupe",
                        barmode="group",
                        title="Taux negatif par ingredient (avec/sans)",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        "Pas assez d'avis par groupe pour calculer des stats (augmente l'enrichissement ou baisse le seuil)."
                    )

                st.subheader("Top labels (Open Beauty Facts)")
                labels_series = analysis_df["labels"].fillna("").astype(str)
                labels_exploded = labels_series.str.split(",").explode().astype(str).str.strip()
                labels_exploded = labels_exploded[labels_exploded.str.len() > 2]
                if not labels_exploded.empty:
                    tmp = analysis_df[["review_id", "is_negative", "rating"]].copy()
                    tmp["label"] = labels_exploded.values
                    label_group = (
                        tmp.groupby("label", dropna=True)
                        .agg(
                            avis=("review_id", "count"),
                            taux_negatif=("is_negative", "mean"),
                            note_moy=("rating", "mean"),
                        )
                        .reset_index()
                    )
                    label_group = label_group[label_group["avis"] >= min_reviews].sort_values(
                        ["taux_negatif", "avis"], ascending=[False, False]
                    )
                    st.dataframe(label_group.head(25), use_container_width=True)
                else:
                    st.info("Aucun label exploitable pour l'instant (match rate trop faible ou labels vides).")

    with tab_chat:
        selected_product = st.selectbox(
            "Produit (chat)",
            options=product_df["product_id"].tolist(),
            format_func=lambda pid: (product_df.loc[product_df["product_id"] == pid, "title"].iloc[0]),
            key="product_chat",
        )
        question = st.text_input("Pose ta question (ex: Quels problemes reviennent souvent ?)")
        if question:
            response = agent.answer_question(product_id=selected_product, question=question)
            st.subheader("Reponse")
            st.write(response.answer)
            if response.supporting_reviews:
                st.write("Avis utilises :")
                for review in response.supporting_reviews[:5]:
                    st.write(f"- {review}")

    with tab_enrich:
        stats = repository.get_enrichment_stats()
        st.subheader("Etat enrichissement")
        st.write(stats)

        col_a, col_b = st.columns(2)
        limit = int(col_a.number_input("Nombre de produits a enrichir", min_value=5, max_value=200, value=50, step=5))
        force = bool(col_b.checkbox("Re-enrichir meme si deja fait", value=False))

        if st.button("Lancer enrichissement Open Beauty Facts"):
            result = ingestion_service.enrich_products_open_beauty_facts(limit=limit, force=force)
            st.success(result)
            st.rerun()


if __name__ == "__main__":
    main()
