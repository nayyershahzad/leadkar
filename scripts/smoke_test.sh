#!/usr/bin/env bash
# LeadKar end-to-end smoke test (CLAUDE.md §9 Phase 8).
#
# Checks the running stack: health, packs API, catalog order creation. The full
# pay->webhook->email leg is manual (needs PayPro sandbox + a live callback URL).
#
# Usage:
#   BASE_URL=http://127.0.0.1:8002 scripts/smoke_test.sh
#   BASE_URL=https://leadkar.pk    scripts/smoke_test.sh   # against production
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8002}"
PASS=0
FAIL=0

check() { # name, expected_code, curl-args...
  local name="$1" expected="$2"; shift 2
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$@")"
  if [[ "$code" == "$expected" ]]; then
    echo "  PASS  $name ($code)"; PASS=$((PASS+1))
  else
    echo "  FAIL  $name (got $code, want $expected)"; FAIL=$((FAIL+1))
  fi
}

echo "Smoke test against $BASE_URL"
check "health"            200 "$BASE_URL/health"
check "GET /api/packs"    200 "$BASE_URL/api/packs"
check "GET unknown pack"  404 "$BASE_URL/api/packs/__nope__"
check "order unknown pack" 404 -X POST "$BASE_URL/api/orders/catalog" \
  -H 'Content-Type: application/json' \
  -d '{"pack_slug":"__nope__","customer":{"email":"smoke@leadkar.pk","name":"Smoke"}}'

echo "----"
echo "PASS=$PASS FAIL=$FAIL"
echo "NOTE: full payment->webhook->email flow requires PayPro sandbox + a public"
echo "      callback URL; run scripts/smoke_paypro.py once entitlement is enabled."
[[ "$FAIL" -eq 0 ]]
