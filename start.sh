#!/usr/bin/env bash
set -euo pipefail

# O Render fornece PORT. Apenas o Node abre essa porta.
# O Python é um cliente local e usa a mesma PORT para chamar /send.
node server.js &
WHATSAPP_PID=$!
PYTHON_PID=""

cleanup() {
  kill "$WHATSAPP_PID" "$PYTHON_PID" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# Espera o Node realmente abrir /status antes de iniciar as buscas da Shopee.
PORT="${PORT:-3333}"
for i in $(seq 1 30); do
  if (echo >"/dev/tcp/127.0.0.1/$PORT") >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! (echo >"/dev/tcp/127.0.0.1/$PORT") >/dev/null 2>&1; then
  echo "❌ O server.js não abriu a porta $PORT dentro de 30 segundos."
  exit 1
fi

python3 main.py --loop &
PYTHON_PID=$!

wait -n "$WHATSAPP_PID" "$PYTHON_PID"
