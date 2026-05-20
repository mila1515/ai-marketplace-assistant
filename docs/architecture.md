# Architecture du projet

## Structure

```text
ai-marketplace-assistant/
├── README.md
├── requirements.txt
├── .env.example
├── data/
├── docs/
├── src/
│   ├── api/
│   ├── agents/
│   ├── core/
│   ├── dashboard/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── scripts/
│   └── services/
└── tests/
```

## Couches

- `core/` : configuration, base de donnees, utilitaires transverses
- `models/` : modele relationnel SQLAlchemy
- `schemas/` : schemas Pydantic exposes a l'API
- `services/` : logique ETL, NLP, RAG MVP, generation d'insights
- `repositories/` : acces aux donnees
- `agents/` : orchestration des reponses utilisateur
- `api/` : backend FastAPI
- `dashboard/` : interface Streamlit
- `scripts/` : seed, ingestion et utilitaires d'initialisation

## Flux applicatif

1. Les donnees brutes arrivent via CSV, API ou scraping.
2. Le pipeline ETL nettoie et structure les produits et avis.
3. Le service NLP ajoute sentiment, resume et aspects.
4. Les avis sont indexes dans un index local JSON pour le MVP.
5. Le service d'insights produit une synthese par produit.
6. L'agent repond aux questions a partir du SQL + recherche lexicale.
7. L'API et le dashboard exposent les resultats.

## Evolution prevue

- MVP : recherche lexicale locale, peu de dependances, installation rapide
- Phase 2 : embeddings + base vectorielle reelle
- Phase 3 : orchestration ETL et exposition cloud

## Execution Docker

- une image Python 3.12 unique pour l'application
- un service `api` qui initialise les donnees de demo puis expose FastAPI
- un service `dashboard` qui partage le meme dossier `data/`
- persistance locale via montage `./data:/app/data`
