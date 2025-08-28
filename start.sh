#!/bin/bash

mkdir -p server
python3 -m http.server -d server &
python3 neko.py -a "$API_ID" -H "$API_HASH" -t "$TOKEN"
