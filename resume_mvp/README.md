# ResumeBoost MVP Backend (FastAPI)

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8090
```

Swagger: `http://127.0.0.1:8090/docs`

## Default OTP (dev)
- `123456`

## Notes
- Default DB is sqlite for local development.
- Switch `DATABASE_URL` to PostgreSQL in production.

## Main Flow APIs
- `POST /api/v1/auth/send-otp`
- `POST /api/v1/auth/login-otp`
- `POST /api/v1/projects`
- `POST /api/v1/projects/{id}/parse`
- `POST /api/v1/projects/{id}/score`
- `POST /api/v1/projects/{id}/jd/analyze`
- `POST /api/v1/projects/{id}/rewrite`
- `POST /api/v1/projects/{id}/export`
- `GET /api/v1/projects/exports/{export_id}/download`
