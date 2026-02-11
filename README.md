# LMS Backend (FastAPI)

## Quickstart

1. Create venv
```bash
uv venv
```

2. Install deps
```bash
uv sync
```

3. Run server
```bash
uv run uvicorn app.main:app --reload
```

## Env
Copy `.env.example` to `.env` and update values.

## Cloud Run

Local container run:
```bash
docker build -t lms-backend .
docker run --rm -p 8080:8080 --env-file .env lms-backend
```

Deploy (replace placeholders):
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/lms-backend
gcloud run deploy lms-backend \
  --image gcr.io/PROJECT_ID/lms-backend \
  --region REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB,JWT_SECRET=your_secret,CORS_ORIGINS=https://your-frontend.example
```

Required env vars: `DATABASE_URL`, `JWT_SECRET`. Optional: `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `CORS_ORIGINS`.
