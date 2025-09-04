#!/bin/sh

mkdir -p server
python3 -m http.server -d server &

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

if [ -z "$GIT_API" ]; then
  echo "❌ Debes definir GIT_API en el entorno."
  exit 1
fi

if [ -z "$GIT_REPO" ]; then
  echo "❌ Debes definir GIT_REPO en el entorno."
  exit 1
fi

CMD="python3 neko.py -a \"$API_ID\" -H \"$API_HASH\" -b \"$GIT_API\" -r \"$GIT_REPO\""

if [ -n "$OWNER" ]; then
  CMD="$CMD -owner \"$OWNER\""
fi

if [ -n "$TOKEN" ]; then
  CMD="$CMD -t \"$TOKEN\""
else
  CMD="$CMD -ss \"$SESSION_STRING\" -id \"$USER_ID\""
fi

eval $CMD
