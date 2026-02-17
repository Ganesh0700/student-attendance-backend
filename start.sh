#!/bin/sh
set -e

echo "Waiting for MongoDB..."
ATTEMPTS=0
MAX_ATTEMPTS=${MONGO_WAIT_MAX_ATTEMPTS:-30}
until python -c "import os; from pymongo import MongoClient; MongoClient(os.getenv('MONGO_URI', 'mongodb://mongo:27017/smart_attendance'), serverSelectionTimeoutMS=2000).admin.command('ping')" >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
    echo "MongoDB not reachable after ${MAX_ATTEMPTS} attempts, continuing startup..."
    break
  fi
  sleep 2
done

if [ "${SEED_ON_START:-1}" = "1" ]; then
  echo "Seeding default users..."
  python seed_users.py || echo "Seed failed, continuing startup..."
fi

echo "Starting backend..."
exec gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers ${WEB_CONCURRENCY:-1} --timeout 120
