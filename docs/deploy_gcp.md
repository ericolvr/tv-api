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
   - Branch: `^main$`
   - Tipo: **Autodetected** (detecta o `cloudbuild.yaml` na raiz)

A partir daqui, cada `git push origin main` dispara o pipeline automaticamente.

---

## 6. Primeiro deploy manual (opcional)

Para testar antes de configurar o trigger:

```bash
docker build -t us-central1-docker.pkg.dev/tv-api/tv-api/api:latest .
docker push us-central1-docker.pkg.dev/tv-api/tv-api/api:latest

gcloud run deploy tv-api \
  --image=us-central1-docker.pkg.dev/tv-api/tv-api/api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated
```

---

## 7. Verificar o deploy

```bash
gcloud run services describe tv-api --region=us-central1
```

A URL do serviço aparece no campo `URL`. Acesse `<URL>/docs` para confirmar que a API está no ar.
