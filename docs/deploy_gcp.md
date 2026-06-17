# Deploy GCP — passo a passo

## Pré-requisitos

- `gcloud` CLI instalado
- `docker` instalado
- Conta no GCP com billing configurada
- Repositório GitHub com o código

---

## 1. Autenticar e criar o projeto

```bash
gcloud auth login

gcloud projects create <name> --name="<NAME>"


gcloud billing accounts list
gcloud billing projects link tv-api-2026 --billing-account=<BILLING_ACCOUNT_ID>

gcloud config set project tv-api-2026
```

---

## 2. Habilitar as APIs necessárias

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  bigquery.googleapis.com
```

---

## 3. Criar o repositório no Artifact Registry

```bash
gcloud artifacts repositories create tv-api \
  --repository-format=docker \
  --location=us-central1 \
  --description="TV API images"
```

---

## 4. Configurar o Docker para autenticar no Artifact Registry

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 5. Conectar o Cloud Build ao GitHub (via console)

1. Acesse **Cloud Build → Triggers** no console GCP
2. Clique em **Connect Repository**
3. Selecione **GitHub** e autorize o OAuth
4. Escolha o repositório `tv-api`
5. Crie um trigger:
   - Branch: `^cloud$`
   - Tipo: **Autodetected** (detecta o `cloudbuild.yaml` na raiz)

A partir daqui, cada `git push origin main` dispara o pipeline automaticamente.

---

## 6. Primeiro deploy manual (opcional)

Para testar antes de configurar o trigger:

```bash
docker build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/tv-api-2026/tv-api/api:latest .
docker push us-central1-docker.pkg.dev/tv-api-2026/tv-api/api:latest

gcloud run deploy tv-api \
  --image=us-central1-docker.pkg.dev/tv-api-2026/tv-api/api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated
```

---

## 7. Liberar acesso público à API

Por padrão o Cloud Run bloqueia acesso externo. Para liberar:

```bash
gcloud run services add-iam-policy-binding tv-api \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

---

## 8. Verificar o deploy

```bash
gcloud run services describe tv-api --region=us-central1 --format='value(status.url)'
```

Acesse `<URL>/docs` para confirmar que a API está no ar.

---

## 9. Criar o bucket no Cloud Storage

```bash
gcloud storage buckets create gs://tv-api-raw-data \
  --location=us-central1

# subir os CSVs brutos
gcloud storage cp data/raw/tvaberta_inventory_availability.csv gs://tv-api-raw-data/
gcloud storage cp data/raw/tvaberta_program_audience.csv gs://tv-api-raw-data/

# verificar
gcloud storage ls gs://tv-api-raw-data/
```

---

## 10. Criar o dataset e tabela no BigQuery

```bash
# criar o dataset
bq mk --location=us-central1 tv_api

# criar a tabela com o schema
bq mk --table tv_api.processed_data signal:STRING,program_code:STRING,date:DATE,weekday:INTEGER,available_time:FLOAT,predicted_audience:FLOAT

# verificar
bq ls tv_api
bq show tv_api.processed_data
```

---

## 11. Criar o banco Firestore

```bash
gcloud firestore databases create --location=us-central1

# verificar
gcloud firestore databases list
```

---

## 12. Build e push da imagem do job

```bash
docker build -f Dockerfile.job \
  --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/tv-api-2026/tv-api/job:latest .

docker push us-central1-docker.pkg.dev/tv-api-2026/tv-api/job:latest
```

---

## 13. Criar o Cloud Run Job

```bash
gcloud run jobs create preprocess-job \
  --image=us-central1-docker.pkg.dev/tv-api-2026/tv-api/job:latest \
  --region=us-central1 \
  --set-env-vars="GCS_BUCKET=tv-api-raw-data,BQ_PROJECT=tv-api-2026,BQ_DATASET=tv_api,BQ_TABLE=processed_data"

# verificar
gcloud run jobs describe preprocess-job --region=us-central1

# testar execução manual
gcloud run jobs execute preprocess-job --region=us-central1 --wait
```

---

## 14. Criar o Cloud Scheduler

```bash
gcloud scheduler jobs create http preprocess-daily \
  --location=us-central1 \
  --schedule="0 3 * * *" \
  --time-zone="America/Sao_Paulo" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/tv-api-2026/jobs/preprocess-job:run" \
  --oauth-service-account-email=1093464412761-compute@developer.gserviceaccount.com

# verificar
gcloud scheduler jobs list --location=us-central1
```

---

## Próximos passos (serviços pendentes)

O deploy da API está completo. Os serviços abaixo ainda precisam ser configurados:

| Serviço | O que falta |
|---|---|
| ~~Cloud Storage~~ | ~~Criar bucket e subir os CSVs brutos~~ ✓ |
| ~~BigQuery~~ | ~~Criar dataset e tabela para os dados processados~~ ✓ |
| ~~Firestore~~ | ~~Criar banco para checkpoint do job~~ ✓ |
| ~~Cloud Run Job~~ | ~~Containerizar e fazer deploy do `preprocess.py`~~ ✓ |
| ~~Cloud Scheduler~~ | ~~Criar trigger diário (03:00) para o job~~ ✓ |
