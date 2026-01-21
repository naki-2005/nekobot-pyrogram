#!/bin/sh

mkdir -p server
#python3 -m http.server -d server &

if [ -n "$TOKEN" ] && [ -n "$SESSION_STRING" ]; then
  echo "❌ No puedes usar TOKEN y SESSION_STRING al mismo tiempo."
  exit 1
elif [ -z "$TOKEN" ] && [ -z "$SESSION_STRING" ]; then
  echo "❌ Debes definir TOKEN o SESSION_STRING en el entorno."
  exit 1
fi

if [ -n "$SESSION_STRING" ] && [ -z "$USER_ID" ]; then
  echo "❌ Debes definir USER_ID si usas SESSION_STRING."
  exit 1
fi

if [ -z "$API_ID" ] || [ -z "$API_HASH" ]; then
  echo "❌ Debes definir API_ID y API_HASH en el entorno."
  exit 1
fi

if [ -z "$GIT_API" ]; then
  echo "❌ Debes definir GIT_API en el entorno."
  exit 1
fi

if [ -z "$GIT_REPO" ]; then
  echo "❌ Debes definir GIT_REPO en el entorno."
  exit 1
fi

# Construcción del comando
CMD="python3 neko.py \
  -a \"$API_ID\" \
  -H \"$API_HASH\" \
  -b \"$GIT_API\" \
  -r \"$GIT_REPO\""

[ -n "$OWNER" ] && CMD="$CMD -owner \"$OWNER\""
[ -n "$WEB_LINK" ] && CMD="$CMD -w \"$WEB_LINK\""
[ -n "$GROUP_ID" ] && CMD="$CMD -g $GROUP_ID"
[ -n "$BLACKWORDS" ] && CMD="$CMD -bw $BLACKWORDS"
[ -n "$FRIENDS" ] && CMD="$CMD -fu $FRIENDS"
[ -n "$SAFE_LINKS" ] && CMD="$CMD -sb \"$SAFE_LINKS\""

if [ -n "$TOKEN" ]; then
  CMD="$CMD -t \"$TOKEN\""
else
  CMD="$CMD -ss \"$SESSION_STRING\" -id \"$USER_ID\""
fi

echo "🚀 Ejecutando: $CMD"
eval "$CMD"
