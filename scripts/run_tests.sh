#!/usr/bin/env bash
# Run every test suite that exists in the tree (M0-friendly; CI + local).
set -uo pipefail
cd "$(dirname "$0")/.."

status=0
run() {
  if [ -d "$1" ]; then
    echo "==> pytest $1"
    pytest "$1" -q || status=1
  fi
}

needs() {  # skip a suite when its deps are absent (CI engine job has no fastapi)
  python3 -c "import $1" >/dev/null 2>&1
}

run tests
run packages/video-engine/tests
if needs fastapi; then run backend/tests; else echo "==> skip backend/tests (fastapi not installed in this env)"; fi

exit $status
