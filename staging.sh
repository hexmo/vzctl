#!/usr/bin/env bash
set -euo pipefail

# ---------- logging ----------
log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }

# ---------- config ----------
set -a; source .secrets.env; set +a
TOKEN="${YETI_TOKEN:?YETI_TOKEN not set}"
API="https://app.yetiapp.cloud/1.0/environment/control/rest/addcontainerenvvars"
ENV="firiri-staging"
NODES=(25245 25246 25247)
ENV_FILE=".staging.env"

log "Starting env var sync for environment '$ENV'"
log "Target nodes: ${NODES[*]}"

# ---------- load vars ----------
log "Loading variables from '$ENV_FILE'..."
VARS=$(grep -v -e '^\s*#' -e '^\s*$' "$ENV_FILE" \
  | jq -R 'split("=") | {(.[0]): (.[1:] | join("="))}' \
  | jq -s 'add')

COUNT=$(echo "$VARS" | jq 'length')
log "Loaded $COUNT variable(s):"
echo "$VARS" | jq -r 'to_entries[] | "  - \(.key) = \(.value)"'

# ---------- push to each node ----------
FAILED=0
for NODE in "${NODES[@]}"; do
  log "Updating node $NODE ..."
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API" \
    --data-urlencode "session=$TOKEN" \
    --data-urlencode "envName=$ENV" \
    --data-urlencode "nodeId=$NODE" \
    --data-urlencode "vars=$VARS")

  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  BODY=$(echo "$RESPONSE" | sed '$d')
  RESULT=$(echo "$BODY" | jq -r '.result // "no-result-field"')

  if [[ "$HTTP_CODE" == "200" && "$RESULT" == "0" ]]; then
    log "  ✓ Node $NODE updated OK (HTTP $HTTP_CODE, result $RESULT)"
  else
    err "  ✗ Node $NODE FAILED (HTTP $HTTP_CODE, result $RESULT)"
    err "    Response: $BODY"
    FAILED=$((FAILED+1))
  fi
done

# ---------- summary ----------
if [[ "$FAILED" -eq 0 ]]; then
  log "Done. All ${#NODES[@]} node(s) updated successfully."
else
  err "Done with errors. $FAILED of ${#NODES[@]} node(s) failed."
  exit 1
fi
