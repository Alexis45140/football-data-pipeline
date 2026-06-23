FROM python:3.11-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "dbt-bigquery>=1.8.0" "mashumaro==3.11"

COPY . .

ENTRYPOINT ["dbt"]