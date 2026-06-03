#!/bin/bash
# Arranca SafePay (interno :5001) + backend principal (:$PORT)
ROOT=$(cd "$(dirname "$0")" && pwd)
APP_PORT="${PORT:-8000}"

# SafePay en puerto interno 5001
cd "$ROOT/safepay"
PORT=5001 gunicorn app:app --workers 1 --bind 0.0.0.0:5001 --timeout 120 &

# Backend principal en el puerto publico de Railway
export SAFEPAY_API_URL=http://localhost:5001
cd "$ROOT/backend"
exec gunicorn main:app --workers 2 --bind "0.0.0.0:$APP_PORT" --timeout 120
