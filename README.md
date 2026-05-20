# AI Marketplace Assistant

Assistant IA orienté e-commerce qui transforme des avis clients en insights actionnables : synthèse produit, points forts/faibles, tendances récurrentes, et un chat Q&A basé sur les avis.

## Problème & valeur métier

- Trop d’avis à lire manuellement : extraction rapide des irritants et des points forts.
- Aide à la décision : comparaison produits/catégories via KPIs et synthèses.
- Utilisable en démo portfolio : pipeline de bout en bout (data → insights → dashboard → agent).

## Ce que fait la version actuelle

- Ingestion d’un CSV Sephora dans PostgreSQL (nettoyage + normalisation).
- Analyse NLP légère sur les avis : sentiment + résumé court.
- Génération d’insights par produit (synthèse + points forts/faibles + thèmes).
- Dashboard Streamlit : catalogue, fiche produit, insights, enrichissement, chat.
- RAG MVP : index JSON local + recherche lexicale pour récupérer des avis pertinents.
- Enrichissement optionnel via Open Beauty Facts (si match) : labels / ingrédients.

## Données

- Source principale : `data/raw/sephora_skindataall.csv`
- Le fichier CSV n’est pas versionné : à placer manuellement dans `data/raw/`.

## Démarrage (Docker recommandé)

```bash
docker compose up --build
```

Accès :

- Dashboard : http://localhost:8502
- API : http://localhost:8000/health
- pgAdmin : http://localhost:8080

Connexion DB :

- Depuis pgAdmin (dans Docker) : host `db`, port `5432`, DB `review_analysis`, user `user`, password `pass`
- Depuis un client local : host `localhost`, port `5433`

## Workflow (Sephora → DB → Dashboard)

1. Mettre le CSV Sephora dans `data/raw/`.
2. Lancer l’ETL :

```bash
docker compose run --rm etl
```

3. Ouvrir le dashboard et explorer les produits / insights.
4. Optionnel : lancer l’enrichissement Open Beauty Facts depuis l’onglet Enrichissement.

Le pipeline sauvegarde aussi une version nettoyée du CSV dans `data/processed/` (en plus de la BDD).

## Dashboard (Streamlit)

Le dashboard sert à explorer rapidement les données, comprendre les problèmes récurrents et obtenir une synthèse actionnable par produit.

Onglets principaux :

- Dashboard : KPIs globaux (nb produits/avis, sentiment), catalogue et distributions.
- Produit : fiche produit (note, volume d’avis), avis récents, synthèse et enrichissement (si disponible).
- Insights : analyses simples basées sur l’enrichissement (ex: taux négatif “avec/sans” certains ingrédients).
- Chat IA : Q&A sur un produit, réponses basées sur la synthèse + des extraits d’avis (OpenAI optionnel).
- Enrichissement : lance la recherche Open Beauty Facts et affiche la couverture (combien de produits matchés).

Exemples de questions à poser dans Chat IA :

- “Quels sont les points faibles les plus cités pour ce produit ?”
- “Qu’est-ce qui revient souvent dans les avis négatifs ?”
- “Résume les avis en 5 bullet points.”
- “Quelles attentes clients ne sont pas satisfaites ?”

## Enrichissement (Open Beauty Facts) : le concept

Objectif : compléter les produits Sephora avec des infos externes (labels, ingrédients) pour permettre des analyses “proxy” (ex: corréler certains ingrédients avec un taux négatif plus élevé).

Important : Open Beauty Facts ne matche pas toujours les produits Sephora (couverture variable). Dans ce cas, l’enrichissement peut afficher `matched = 0` même si l’appel API fonctionne.

## API (optionnel)

- `GET /health`
- `GET /products`
- `GET /products/{product_id}/insight`
- `GET /products/{product_id}/ask?question=...`
- `POST /admin/ingest?csv_path=data/raw/sephora_skindataall.csv`
- `POST /admin/enrich-openbeautyfacts?limit=50&force=false`

## Stack

- Python, Pandas
- PostgreSQL (Docker), SQLAlchemy, pg8000
- FastAPI (API), Streamlit + Plotly (dashboard)
- Open Beauty Facts (enrichissement)
- OpenAI (optionnel) : définir `OPENAI_API_KEY` dans `.env`
