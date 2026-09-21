# ⚽ Pipeline Data ELT — Football Transfers Analytics (Python × BigQuery × dbt Core × Docker)

Ce dépôt héberge un projet de **Modern Data Stack** conteneurisé, simulant un environnement de production pour un **Analytics Engineer / Data Engineer**. L'objectif est d'extraire en temps réel les données de transferts de football via une API, de les charger dans **BigQuery**, de les transformer avec **dbt Core**, et de restituer les résultats dans un **dashboard Power BI**.

---

## 🏗️ Architecture Globale du Pipeline (ELT)

```
API Football (RapidAPI)
        ↓
   Extraction Python (conteneur Docker dédié)
        ↓
   BigQuery — table brute `transfers_raw` (append + partition)
        ↓
   dbt Core — Staging (stg_football_transfers)
        ↓
   dbt Core — Marts (fct_transfer_analysis)
        ↓
   Power BI (Dashboard interactif)
```

L'ensemble tourne seul : un workflow GitHub Actions déclenche l'extraction puis
`dbt build` tous les jours à 06:00 UTC.

Le pipeline suit une approche **ELT** moderne, entièrement conteneurisée :

1. **Extract** — Récupération des transferts de joueurs via l'API RapidAPI (pagination multi-pages)
2. **Load** — Écriture directe dans la table brute BigQuery, en append horodaté
3. **Transform (Staging)** — Typage, déduplication et conversion des dates en `TIMESTAMP`
4. **Transform (Marts)** — Table de faits reconstruite à chaque run depuis l'historique brut accumulé
5. **Conteneurisation** — Deux services Docker indépendants : extraction et transformation
6. **Orchestration** — GitHub Actions : run quotidien planifié, tests dbt bloquants

---

## 🛠️ Stack Technique

| Outil | Rôle |
|---|---|
| **Python (requests, pandas, google-cloud-bigquery)** | Extraction API et chargement dans le warehouse |
| **RapidAPI — Free API Live Football Data** | Source de données transferts |
| **Google BigQuery** | Cloud Data Warehouse — stockage et calcul |
| **dbt Core v1.11** | Transformation SQL modulaire — staging et marts |
| **Docker & Docker Compose** | Conteneurisation des étapes extraction et transformation |
| **GitHub Actions** | Orchestration planifiée et intégration continue |
| **Power BI** | Visualisation et dashboard interactif |
| **Git & GitHub** | Versioning |

---

## 📂 Structure du Projet

```
football-data-pipeline/
├── README.md
├── dbt_project.yml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── profiles.yml.example
├── packages.yml
├── .env.example
├── .github/
│   └── workflows/
│       ├── pipeline.yml       # run quotidien : extract + dbt build
│       └── ci.yml             # lint + validation dbt sur chaque PR
├── images/
│   └── football_dashboard_preview.png
├── data/
│   └── sample_transferts.csv  # échantillon, hors pipeline
├── scripts/
│   └── extract_transfers.py
└── models/
    ├── staging/
    │   ├── sources.yml
    │   ├── schema.yml
    │   └── stg_football_transfers.sql
    └── marts/
        ├── schema.yml
        └── fct_transfer_analysis.sql
```

---

## 🧬 Détail du Pipeline

### 1. Extraction — `scripts/extract_transfers.py`

Récupère les transferts sur plusieurs pages via l'API RapidAPI, dédoublonne le lot et charge le résultat directement dans la table brute BigQuery, en append horodaté par `_extracted_at`. Plus aucun CSV intermédiaire à committer.

```python
def load_to_bigquery(df, project, dataset, table):
    client = bigquery.Client(project=project)
    table_id = f"{project}.{dataset}.{table}"

    job_config = bigquery.LoadJobConfig(
        schema=RAW_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(field="_extracted_at"),
    )
    job = client.load_table_from_json(df.to_dict("records"), table_id, job_config=job_config)
    job.result()
```

L'appel API gère les retries (429 et 5xx) avec backoff exponentiel — indispensable pour un run planifié sans surveillance.

🔐 La clé API est gérée via une variable d'environnement (`.env`, jamais commitée).

---

### 2. Couche Staging — `stg_football_transfers.sql` (Vue)

Type les colonnes, construit la clé `transfer_id` et dédoublonne : le même transfert revient à chaque run tant qu'il reste dans la fenêtre glissante de l'API.

```sql
{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw_football', 'transfers_raw') }}
),

typed as (
    select
        to_hex(md5(concat(
            coalesce(joueur, ''), '|',
            coalesce(club_arrivee, ''), '|',
            coalesce(date_transfert, '')
        ))) as transfer_id,
        ...
        safe.parse_timestamp('%Y-%m-%dT%H:%M:%SZ', date_transfert) as date_transfert
    from source
),

deduplicated as (
    select * except (rn)
    from (
        select *, row_number() over (
            partition by transfer_id order by _extracted_at desc
        ) as rn
        from typed
    )
    where rn = 1
)

select * from deduplicated
```

---

### 3. Couche Marts — `fct_transfer_analysis.sql` (Table)

Table de faits alimentant le dashboard. L'accumulation ne se fait pas ici mais en amont : `transfers_raw` grossit à chaque run, le staging dédoublonne l'ensemble, et le mart est reconstruit par-dessus. L'historique dépasse donc la fenêtre glissante renvoyée par l'API, sans jamais recourir à du DML.

```sql
{{ config(
    materialized='table',
    partition_by={'field': 'date_transfert', 'data_type': 'timestamp', 'granularity': 'month'},
    cluster_by=['type_transfert']
) }}

select ... from {{ ref('stg_football_transfers') }}
```

### 4. Tests

`dbt build` enchaîne modèles et tests dans l'ordre du graphe et s'arrête au premier échec : unicité et non-nullité de `transfer_id`, montants positifs, fraîcheur de la source. Un changement de schéma côté API casse le run au lieu de passer inaperçu dans le dashboard.

---

## 🐳 Conteneurisation — 2 services Docker indépendants

```yaml
services:
  extract:
    build: .
    entrypoint: ["python", "scripts/extract_transfers.py"]
    volumes:
      - .:/usr/app
    env_file:
      - .env

  dbt:
    build: .
    volumes:
      - .:/usr/app
      - ./profiles.yml:/root/.dbt/profiles.yml:ro
      - ./credentials.json:/usr/app/credentials.json:ro
    env_file:
      - .env
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/usr/app/credentials.json
```

Le service `extract` gère uniquement la récupération des données API. Le service `dbt` gère uniquement la transformation. Les deux partagent la même image de base mais s'exécutent indépendamment.

---

## ⚙️ Orchestration — GitHub Actions

Deux workflows, aucun serveur à maintenir.

**`pipeline.yml` — run quotidien**

```yaml
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:
```

Authentification GCP via `google-github-actions/auth`, extraction, puis `dbt deps && dbt build --target prod`. Le job échoue si un test dbt échoue, et les artefacts `target/` (dont `run_results.json` et la doc dbt) sont conservés 14 jours. Un garde `concurrency` empêche deux runs d'écrire en même temps dans la table brute.

**`ci.yml` — sur chaque PR**

`ruff` sur le Python et `dbt parse` sur les modèles. `dbt parse` valide la syntaxe et la cohérence du graphe sans se connecter à BigQuery : la CI tourne donc sans credentials.

**Secrets à créer** dans *Settings → Secrets and variables → Actions* :

| Secret | Contenu |
|---|---|
| `RAPIDAPI_KEY` | Clé RapidAPI |
| `GCP_PROJECT` | ID du projet Google Cloud |
| `GCP_SA_KEY` | Contenu **complet** du JSON de compte de service |

En CI, aucun fichier de credentials n'existe sur disque : le profil dbt lit `keyfile_json` depuis l'environnement.

```yaml
prod:
  type: bigquery
  method: service-account-json
  project: "{{ env_var('GCP_PROJECT') }}"
  keyfile_json: "{{ env_var('GCP_SA_KEY') | as_native }}"
```

---

## ⚠️ Limites connues

Le projet tourne sur un **bac à sable BigQuery**, c'est-à-dire un projet GCP sans compte de facturation. Deux contraintes en découlent, assumées :

- **Pas de DML.** `INSERT`, `UPDATE`, `DELETE` et `MERGE` sont refusés. Le mart est donc reconstruit par `CREATE TABLE AS SELECT` plutôt que par un `merge` incrémental. À ce volume la différence de coût est nulle ; elle deviendrait significative à partir de quelques millions de lignes.
- **Rétention de 60 jours.** Toute table du sandbox expire automatiquement au bout de 60 jours. L'historique accumulé est donc une fenêtre glissante de 60 jours, pas un historique complet.

Activer la facturation sur le projet lève les deux limites d'un coup, sans quitter le free tier (1 Tio de requêtes et 10 Gio de stockage gratuits par mois). À ce volume de données, la facture resterait à zéro.

---

## 📊 Dashboard Power BI

Le mart `fct_transfer_analysis` alimente un dashboard Power BI interactif comprenant :

- **3 KPIs clés** — nombre de transferts analysés, montant total, montant moyen
- **Évolution temporelle** — courbe des montants de transferts jour par jour
- **Top 10 des transferts les plus chers** — classement par montant
- **Répartition par type de transfert** — contrat définitif vs prêt
- **Filtres dynamiques** — par type de transfert et par club

Sur cette extraction, **500 transferts** ont été analysés, représentant un montant total de plus de 450M€.

![Aperçu du dashboard](images/football_dashboard_preview.png)

Le rapport pointe sur le mart BigQuery : chaque run du pipeline enrichit la table, le dashboard suit au rafraîchissement.

> *Le `.pbix` est local, donc rafraîchi à la main — c'est le seul maillon de la chaîne qui ne tourne pas tout seul. Publication sur Power BI Service (refresh planifié via le connecteur BigQuery) à venir.*


---

## 🚀 Guide d'Exécution Locale (Docker)

### Prérequis

- Docker Desktop installé et lancé
- Compte GCP avec un projet BigQuery + clé de service JSON
- Clé API RapidAPI (Free API Live Football Data)

### Configuration

1. Copier `profiles.yml.example` en `profiles.yml` et renseigner vos informations BigQuery
2. Copier `.env.example` en `.env` et renseigner la clé API et le projet GCP
3. Placer votre clé de service GCP sous `credentials.json`

### Déploiement

```powershell
# 1. Build des images Docker
docker-compose build

# 2. Extraction API -> table brute BigQuery
docker-compose run extract

# 3. Modèles + tests
docker-compose run dbt deps
docker-compose run dbt build

# 4. Nettoyage des conteneurs
docker-compose down --remove-orphans
```

Pour vérifier l'extraction sans rien écrire dans BigQuery :

```powershell
docker-compose run --entrypoint python extract scripts/extract_transfers.py --pages 1 --dry-run
```

---

## 👤 Auteur

**Alexis Claudeon** — Data Analyst | Analytics Engineer Junior

- 🐙 [GitHub](https://github.com/Alexis45140)
- 💼 [LinkedIn](https://www.linkedin.com/in/alexis-claudeon)
