# student-attendance-backend

## Deploy on Render

This repo now includes a root `render.yaml` for one-click Render blueprint deploy.

### Required environment variables

- `MONGO_URI` (your MongoDB Atlas connection string)
- `SECRET_KEY` (JWT signing secret)

### Manual Render setup (if not using blueprint)

- Runtime: `Python`
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
