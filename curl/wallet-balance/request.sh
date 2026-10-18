#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
: "${BUSINESS_ID:?Set BUSINESS_ID}"
: "${ACCESS_TOKEN:?Set ACCESS_TOKEN}"
API_BASE_URL="${API_BASE_URL:-https://api.sandbox.1-funnel.org}"
API_BASE_URL="${API_BASE_URL%/}"
if [[ ! "$BUSINESS_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
  echo "Set BUSINESS_ID to the issued UUID" >&2
  exit 1
fi
if [[ "$API_BASE_URL" != "https://api.sandbox.1-funnel.org" && ! "$API_BASE_URL" =~ ^http://127\.0\.0\.1:[0-9]+$ ]]; then
  echo "Use the Sandbox API origin, or loopback HTTP for offline tests" >&2
  exit 1
fi
curl --fail-with-body --silent --show-error --include --max-time 15 \
  --url "$API_BASE_URL/v1/businesses/$BUSINESS_ID/wallet/balance" \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header "Accept: application/json"
