# Deploy GCP — passo a passo

## Pré-requisitos

- `gcloud` CLI instalado
- `docker` instalado
- Conta no GCP com billing configurada
- Repositório GitHub com o código

---

## 0. Definir variáveis

Execute isso no terminal antes de rodar qualquer comando abaixo:

```bash
export PROJECT_ID=tv-api-2028
export REGION=us-central1
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
export REGISTRY=${REGION}-docker.pkg.dev/${PROJECT_ID}/tv-api
```

---

## 1. Autenticar e criar o projeto

```bash
gcloud auth login

gcloud projects create $PROJECT_ID --name="TV API"

gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>

gcloud config set project $PROJECT_ID
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
  --location=$REGION \
  --description="TV API images"
```

---

## 4. Configurar o Docker para autenticar no Artifact Registry

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
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

A partir daqui, cada `git push origin cloud` dispara o pipeline automaticamente.

---

## 6. Primeiro deploy manual (opcional)

Para testar antes de configurar o trigger:

```bash
docker build --platform linux/amd64 -t $REGISTRY/api:latest .
docker push $REGISTRY/api:latest

gcloud run deploy tv-api \
  --image=$REGISTRY/api:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated
```

---

## 7. Liberar acesso público à API

```bash
gcloud run services add-iam-policy-binding tv-api \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker"
```

---

## 8. Verificar o deploy

```bash
gcloud run services describe tv-api --region=$REGION --format='value(status.url)'
```

Acesse `<URL>/docs` para confirmar que a API está no ar.

---

## 9. Criar o bucket no Cloud Storage

```bash
gcloud storage buckets create gs://tv-api-raw-data --location=$REGION

gcloud storage cp data/raw/tvaberta_inventory_availability.csv gs://tv-api-raw-data/
gcloud storage cp data/raw/tvaberta_program_audience.csv gs://tv-api-raw-data/

gcloud storage ls gs://tv-api-raw-data/

# permissão de leitura para o Cloud Run Job
gcloud storage buckets add-iam-policy-binding gs://tv-api-raw-data \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectViewer"
```

---

## 10. Criar o dataset e tabela no BigQuery

```bash
bq mk --location=$REGION tv_api

bq mk --table tv_api.processed_data \
  signal:STRING,program_code:STRING,date:DATE,weekday:INTEGER,available_time:FLOAT,predicted_audience:FLOAT

bq ls tv_api
bq show tv_api.processed_data
```

---

## 11. Criar o banco Firestore

```bash
gcloud firestore databases create --location=$REGION

gcloud firestore databases list
```

---

## 12. Build e push da imagem do job

```bash
docker build -f Dockerfile.job --platform linux/amd64 -t $REGISTRY/job:latest .

docker push $REGISTRY/job:latest
```

---

## 13. Criar o Cloud Run Job

```bash
gcloud run jobs create preprocess-job \
  --image=$REGISTRY/job:latest \
  --region=$REGION \
  --set-env-vars="GCS_BUCKET=tv-api-raw-data,BQ_PROJECT=$PROJECT_ID,BQ_DATASET=tv_api,BQ_TABLE=processed_data"

gcloud run jobs describe preprocess-job --region=$REGION

# testar execução manual
gcloud run jobs execute preprocess-job --region=$REGION --wait
```

---

## 14. Criar o Cloud Scheduler

```bash
gcloud scheduler jobs create http preprocess-daily \
  --location=$REGION \
  --schedule="0 3 * * *" \
  --time-zone="America/Sao_Paulo" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/preprocess-job:run" \
  --oauth-service-account-email=$SA

gcloud scheduler jobs list --location=$REGION
```

---

## Serviços configurados

| Serviço | Descrição |
|---|---|
| Artifact Registry | Repositório de imagens Docker |
| Cloud Run (API) | FastAPI — GET /program e GET /period |
| Cloud Storage | CSVs brutos de entrada |
| BigQuery | Dados processados — destino do job |
| Firestore | Checkpoint do job para retomada em falha |
| Cloud Run Job | preprocess_gcp.py — executa e desliga |
| Cloud Scheduler | Aciona o job diariamente às 03:00 |
| Cloud Build | CI/CD — build + deploy a cada push na branch `cloud` |
