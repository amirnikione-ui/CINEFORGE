#!/usr/bin/env bash
# CINEFORGE smoke test — hits a RUNNING api per docs/API_CONTRACTS.md v0.1
# (contract paths: /health, /api/projects, /api/projects/{pid}/chat)
# Usage: BASE=http://localhost:8000 bash scripts/smoke_test.sh
set -euo pipefail
BASE="${BASE:-http://localhost:8000}"

say() { printf "\n\033[1;33m== %s ==\033[0m\n" "$1"; }

say "health (contract: providers map present)"
curl -fsS "$BASE/health" | python3 -c "
import json,sys
h=json.load(sys.stdin)
assert h.get('status')=='ok', h
assert 'providers' in h, 'contract expects providers map'
print('health ok · providers:', {k:v[:2] for k,v in h['providers'].items()})
"

say "create project (contract: POST /api/projects)"
PID=$(curl -fsS -X POST "$BASE/api/projects" -H 'Content-Type: application/json' \
  -d '{"title":"RELAY smoke promo","brief":"12s dark cinematic promo, instagram 9:16","platform":"instagram","duration_hint_s":12}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
echo "project id: $PID"

say "chat → director produces (contract: POST /api/projects/{pid}/chat)"
curl -fsS -X POST "$BASE/api/projects/$PID/chat" -H 'Content-Type: application/json' \
  -d '{"message":"make a 12 second dark cinematic promo"}' | python3 -c "
import json,sys
r=json.load(sys.stdin)
assert r.get('assistant_message',{}).get('content'), 'assistant reply missing'
print('assistant:', r['assistant_message']['content'][:120].replace(chr(10),' '))
print('assets:', len(r.get('assets',[])), '| jobs:', len(r.get('jobs',[])))
"

say "SMOKE OK"
