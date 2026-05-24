#!/usr/bin/env bash
set -euo pipefail

set -a; source .secrets.env; set +a   # loads YETI_TOKEN into env

API="https://app.yetiapp.cloud/1.0/environment/control/rest/addcontainerenvvars"
TOKEN="${YETI_TOKEN:?YETI_TOKEN not set}"
ENV="firiri-production"
NODES=(25248 25249 25250)
ENV_FILE=".production.env"

VARS=$(grep -v -e '^\s*#' -e '^\s*$' "$ENV_FILE" \
  | jq -R 'split("=") | {(.[0]): (.[1:] | join("="))}' \
  | jq -s 'add')

for NODE in "${NODES[@]}"; do
  echo "Updating node $NODE..."
  curl -s -X POST "$API" \
    --data-urlencode "session=$TOKEN" \
    --data-urlencode "envName=$ENV" \
    --data-urlencode "nodeId=$NODE" \
    --data-urlencode "vars=$VARS" | python3 -m json.tool
done
