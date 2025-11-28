#!/bin/sh
set -e

# echo "Running Alembic migrations..."
# alembic upgrade head
# Migrações desabilitadas - execute manualmente se necessário

echo "Starting ORKIO v4.5 backend..."
uvicorn app.main_v4:app --host 0.0.0.0 --port ${PORT:-8000}
