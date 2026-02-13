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

## Bootstrap first admin (temporary)

Self-signup is disabled by default and `/users/provision` requires an existing admin.

To create the first admin in production:

1) Deploy once with these env vars set:

- `BOOTSTRAP_ADMIN_ENABLED=true`
- `BOOTSTRAP_ADMIN_EMAIL=admin@gmail.com` (optional but strongly recommended)

2) Call `POST /auth/signup` once to create the admin.

3) Immediately redeploy with `BOOTSTRAP_ADMIN_ENABLED=false` (or unset it).

## Public signup (temporary)

If you want to open up `POST /auth/signup` for everyone, deploy with:

- `SELF_SIGNUP_ENABLED=true`

To also allow creating admins via signup (highly risky), set:

- `SELF_SIGNUP_ALLOW_ADMIN=true`

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
