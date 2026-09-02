#!/usr/bin/env bash
set -e

node server.js &
WHATSAPP_PID=$!

python main.py --loop &
PYTHON_PID=$!

trap 'kill $WHATSAPP_PID $PYTHON_PID 2>/dev/null || true' TERM INT EXIT
wait -n $WHATSAPP_PID $PYTHON_PID
