#!/bin/sh
set -e

echo "Waiting for MongoDB..."
until python -c "import os; from pymongo import MongoClient; MongoClient(os.getenv('MONGO_URI', 'mongodb://mongo:27017/smart_attendance'), serverSelectionTimeoutMS=2000).admin.command('ping')" >/dev/null 2>&1; do
  sleep 2
done

if [ "${SEED_ON_START:-1}" = "1" ]; then
  echo "Seeding default users..."
  python seed_users.py
fi

echo "Starting backend..."
exec python app.py
