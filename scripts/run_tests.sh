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

run tests
run packages/video-engine/tests
run backend/tests

exit $status
