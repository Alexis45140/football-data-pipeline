# Football Transfers — pipeline ELT automatisé

[![pipeline](https://github.com/Alexis45140/football-data-pipeline/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Alexis45140/football-data-pipeline/actions/workflows/pipeline.yml)
[![ci](https://github.com/Alexis45140/football-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Alexis45140/football-data-pipeline/actions/workflows/ci.yml)

Pipeline de données conteneurisé qui extrait les transferts de football depuis une API, les charge dans BigQuery, les transforme avec dbt et les restitue dans un dashboard Power BI.

Il tourne sans intervention : un workflow GitHub Actions déclenche l'extraction puis `dbt build` tous les jours à 06:00 UTC. Aucune commande à lancer à la main, aucun fichier de données à committer.

---

## Architecture

```
API Football (RapidAPI)
        |
        v
Extraction Python  ------->  BigQuery  transfers_raw
                             (append horodaté, partitionné)
                                  |
                                  v
                        dbt  stg_football_transfers
                             (typage + déduplication)
                                  |
                                  v
                        dbt  fct_transfer_analysis
                             (table de faits)
                                  |
                                  v
                             Power BI
```

L'approche est un ELT : on charge le brut tel quel, on transforme ensuite dans l'entrepôt. `transfers_raw` n'est jamais écrasée, chaque run y ajoute un lot horodaté. C'est elle qui porte l'historique ; les couches dbt au-dessus sont recalculables à tout moment.

---

## Stack

| Outil | Rôle |
|---|---|
| Python — requests, pandas, google-cloud-bigquery | Extraction API et chargement dans l'entrepôt |
| RapidAPI — Free API Live Football Data | Source des transferts |
| Google BigQuery | Entrepôt de données |
| dbt Core 1.12 | Transformations SQL, tests, documentation |
| GitHub Actions | Orchestration planifiée et intégration continue |
| Docker & Docker Compose | Exécution locale reproductible |
| Power BI | Restitution |

---

## Le pipeline en détail

### Extraction — `scripts/extract_transfers.py`

Parcourt les pages de l'API, met les champs à plat, dédoublonne le lot puis écrit directement dans BigQuery. Pas de CSV intermédiaire : rien à committer entre deux runs.

```python
job_config = bigquery.LoadJobConfig(
    schema=RAW_SCHEMA,
    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    time_partitioning=bigquery.TimePartitioning(field="_extracted_at"),
)
job = client.load_table_from_json(df.to_dict("records"), table_id, job_config=job_config)
job.result()
```

Les appels rejouent sur 429 et 5xx avec un backoff exponentiel, et le script sort en code 1 si rien n'est récupéré — sans quoi un run planifié échouerait en silence.

### Staging — `stg_football_transfers` (vue)

Type les colonnes, construit une clé `transfer_id` et dédoublonne. C'est la pièce centrale : l'API renvoie une fenêtre glissante, donc le même transfert revient à chaque run.

```sql
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
```

`safe.parse_timestamp` plutôt que `parse_timestamp` : une date hors format laisse un `null` au lieu de faire tomber le run entier.

Sur les trois premiers runs, 1048 lignes brutes accumulées se sont réduites à 499 transferts uniques dans le mart.

### Mart — `fct_transfer_analysis` (table)

Table de faits consommée par Power BI, partitionnée par mois sur `date_transfert` et clusterisée sur `type_transfert`.

```sql
{{ config(
    materialized='table',
    partition_by={'field': 'date_transfert', 'data_type': 'timestamp', 'granularity': 'month'},
    cluster_by=['type_transfert']
) }}
```

Elle est reconstruite à chaque run depuis l'intégralité de `transfers_raw`. L'accumulation se joue donc en amont, dans la couche brute, pas dans le mart — voir *Limites connues*.

### Tests

Dix tests sur les deux couches : unicité et non-nullité de `transfer_id`, montants positifs, non-nullité du joueur et du type de transfert, fraîcheur de la source.

`dbt build` enchaîne modèles et tests dans l'ordre du graphe et s'arrête au premier échec. Un changement de schéma côté API casse le run au lieu de se propager silencieusement jusqu'au dashboard.

---

## Orchestration

Deux workflows, aucun serveur à maintenir.

**`pipeline.yml`** — tous les jours à 06:00 UTC, déclenchable aussi à la main. Authentification GCP, extraction, `dbt deps && dbt build`, puis publication des artefacts `target/` (dont `run_results.json` et la documentation dbt) pendant 14 jours. Un garde `concurrency` empêche deux runs d'écrire en même temps dans la table brute.

**`ci.yml`** — sur chaque pull request et chaque push sur `main` : `ruff` sur le Python et `dbt parse` sur les modèles. `dbt parse` valide la syntaxe et la cohérence du graphe sans se connecter à BigQuery, donc la CI tourne sans le moindre credential.

Secrets attendus dans *Settings → Secrets and variables → Actions* :

| Secret | Contenu |
|---|---|
| `RAPIDAPI_KEY` | Clé RapidAPI |
| `GCP_PROJECT` | ID du projet Google Cloud |
| `GCP_SA_KEY` | JSON complet du compte de service |

En CI, aucun fichier de credentials n'existe sur disque : le profil dbt lit la clé depuis l'environnement.

```yaml
prod:
  type: bigquery
  method: service-account-json
  project: "{{ env_var('GCP_PROJECT') }}"
  keyfile_json: "{{ env_var('GCP_SA_KEY') | as_native }}"
```

---

## Limites connues

Le projet tourne sur un bac à sable BigQuery, c'est-à-dire un projet GCP sans compte de facturation. Deux contraintes en découlent, assumées :

- **Pas de DML.** `INSERT`, `UPDATE`, `DELETE` et `MERGE` sont refusés. Le mart est donc reconstruit par `CREATE TABLE AS SELECT` au lieu d'un `merge` incrémental. À ce volume la différence de coût est nulle ; elle deviendrait significative à partir de quelques millions de lignes, où l'incrémental s'imposerait.
- **Rétention de 60 jours.** Toute table du sandbox expire automatiquement au bout de 60 jours. L'historique accumulé est donc une fenêtre glissante de 60 jours, pas un historique complet.

Activer la facturation lève les deux limites d'un coup, sans quitter le free tier (1 Tio de requêtes et 10 Gio de stockage gratuits par mois). À ce volume, la facture resterait à zéro.

Le rafraîchissement Power BI reste par ailleurs manuel tant que le rapport est un `.pbix` local.

---

## Dashboard

Le mart alimente un rapport Power BI : trois KPI (nombre de transferts, montant total, montant moyen), l'évolution des montants dans le temps, le top 10 des transferts les plus chers, la répartition entre contrats définitifs et prêts, et des filtres par type et par club.

![Aperçu du dashboard](images/football_dashboard_preview.png)

La capture correspond à une extraction de 500 transferts, pour plus de 450 M€ cumulés.

---

## Exécution locale

### Prérequis

- Docker Desktop
- Un projet GCP avec BigQuery et une clé de compte de service
- Une clé RapidAPI

### Configuration

1. Copier `profiles.yml.example` en `profiles.yml` et renseigner le projet et le dataset
2. Copier `.env.example` en `.env` et renseigner la clé API et le projet GCP
3. Placer la clé de compte de service sous `credentials.json`

Ces trois fichiers sont ignorés par git.

### Lancement

```powershell
docker-compose build
docker-compose run extract          # API -> transfers_raw
docker-compose run dbt deps
docker-compose run dbt build        # modèles + tests
docker-compose down --remove-orphans
```

Pour vérifier l'extraction sans rien écrire dans BigQuery :

```powershell
docker-compose run --entrypoint python extract scripts/extract_transfers.py --pages 1 --dry-run
```

---

## Structure

```
football-data-pipeline/
├── .github/workflows/
│   ├── pipeline.yml            # run quotidien : extraction + dbt build
│   └── ci.yml                  # ruff + dbt parse sur chaque PR
├── models/
│   ├── staging/
│   │   ├── sources.yml
│   │   ├── schema.yml
│   │   └── stg_football_transfers.sql
│   └── marts/
│       ├── schema.yml
│       └── fct_transfer_analysis.sql
├── scripts/
│   └── extract_transfers.py
├── data/
│   └── sample_transferts.csv   # échantillon, hors pipeline
├── images/
├── dbt_project.yml
├── packages.yml
├── profiles.yml.example
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Auteur

**Alexis Claudeon** — Data Analyst | Analytics Engineer junior

- [GitHub](https://github.com/Alexis45140)
- [LinkedIn](https://www.linkedin.com/in/alexis-claudeon)
