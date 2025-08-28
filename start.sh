#!/bin/sh

mkdir -p server
python3 -m http.server -d server &

# Verificar que solo uno esté definido
if [ -n "$TOKEN" ] && [ -n "$SESSION_STRING" ]; then
  echo "❌ No puedes usar TOKEN y SESSION_STRING al mismo tiempo."
  exit 1
elif [ -z "$TOKEN" ] && [ -z "$SESSION_STRING" ]; then
  echo "❌ Debes definir TOKEN o SESSION_STRING en el entorno."
  exit 1
fi

# Ejecutar según el caso
if [ -n "$TOKEN" ]; then
  python3 neko.py -a "$API_ID" -H "$API_HASH" -t "$TOKEN"
else
  python3 neko.py -a "$API_ID" -H "$API_HASH" -ss "$SESSION_STRING"
fi
