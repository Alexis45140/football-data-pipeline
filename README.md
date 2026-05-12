# ⚽ Football Data Pipeline (ELT) - Mercato 2026

Ce projet illustre la mise en place d'une **Modern Data Stack** complète pour l'analyse en temps réel du marché des transferts. Il automatise l'extraction depuis une **API de football**, le chargement vers le Cloud et la transformation en une **Table de Faits** optimisée pour la Business Intelligence.

## 🚀 Vue d'Ensemble
L'objectif est de démontrer une maîtrise du cycle de vie de la donnée sur des données actuelles :
1. **Extraction (API)** : Récupération automatisée des transferts récents, incluant les transactions de **2026**.
2. **Chargement** : Centralisation des données brutes (JSON/API) dans Google BigQuery via Docker.
3. **Transformation** : Utilisation de **dbt** pour le nettoyage et la modélisation SQL.
4. **Visualisation** : Dashboard interactif Power BI analysant les tendances du marché 2026.

## 🏗️ Architecture des Données
Le pipeline suit une architecture de médaillon simplifiée :
- **Staging (`stg_football_transfers`)** : Nettoyage des données API, renommage des colonnes et typage initial.
- **Marts (`fct_transfer_analysis`)** : Couche finale de reporting exploitant les données de l'année en cours (**2026**). Gestion des formats ISO complexes (`YYYY-MM-DDTHH:MM:SSZ`) convertis en `DATE` et `TIMESTAMP`.

## 🛠️ Stack Technique
- **API Source** : Football Data API (Extracts 2026)
- **Data Warehouse** : Google BigQuery
- **Transformation** : dbt (Data Build Tool)
- **Environnement** : Docker & Docker Compose
- **Visualisation** : Power BI

## 📂 Structure du Projet
```text
├── dbt/
│   ├── models/
│   │   ├── staging/      # Nettoyage et normalisation
│   │   └── marts/        # Tables de faits prêtes pour le BI
│   ├── dbt_project.yml   # Configuration du projet dbt
│   └── sources.yml       # Définition des sources BigQuery
├── docker-compose.yml    # Orchestration du container dbt
├── Dockerfile            # Image personnalisée dbt-bigquery
└── README.md             # Documentation
```

## ⚙️ Installation et Utilisation
### Pré-requis
* Docker installé sur votre machine.
* Un projet Google Cloud avec un accès à BigQuery.
* Un fichier `profiles.yml` configuré pour dbt.

### Lancement du pipeline
1. **Clonez le dépôt :**

Bash
git clone [https://github.com/Alexis45140/football-data-pipeline.git](https://github.com/Alexis45140/football-data-pipeline.git)
Exécutez les transformations avec Docker :

Bash
docker compose run --rm dbt run


## 📊 Dashboard
Le modèle de données final alimente un dashboard permettant d'analyser :
- Le volume total des transferts par saison.
- Les clubs les plus actifs sur le marché.
- La précision temporelle des transactions (timestamping).

![Aperçu du Dashboard](images/football_dashboard_preview.png)

## 🧠 Défis Techniques Résolus
- **Data Quality** : Résolution de problèmes de formatage de dates via `SAFE.PARSE_TIMESTAMP` pour éviter les échecs de pipeline.
- **Conteneurisation** : Mise en place d'un environnement Docker pour assurer la reproductibilité des builds SQL indépendamment de la machine locale.

## 👤 CONTACT
**Ton Prénom Nom**
* [Mon Profil LinkedIn](https://www.linkedin.com/in/alexis-claudeon/)
* [Mon Portfolio](https://github.com/alexis45140)

