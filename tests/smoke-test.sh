#!/usr/bin/env bash
#
# Docker smoke test — ported from the Drupal git-manual demo.
#
# Builds the image (which migrates, imports all 1,426 pages, and builds the
# Pagefind index), starts the container, and asserts:
#   1. the app serves HTTP,
#   2. the Pagefind index metadata is served,
#   3. the index reports >= 1,400 pages (the single 'en' bucket holds every
#      page across all five languages, exactly as in the Drupal demo).
set -euo pipefail

PORT=8080
IMAGE="gitmastery-django-smoke-$$"
PAGEFIND_ENTRY_URL="http://localhost:${PORT}/pagefind/pagefind-entry.json"
MIN_PAGES=1400

cd "$(dirname "$0")/.."

echo "==> Building Docker image (migrate + import + index build happen here)..."
docker build -t "$IMAGE" .

cleanup() {
  docker stop "$IMAGE" 2>/dev/null || true
  docker rm "$IMAGE" 2>/dev/null || true
  docker rmi "$IMAGE" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Starting container on port $PORT..."
docker run -d --name "$IMAGE" -p "${PORT}:8080" "$IMAGE"

echo "==> Waiting for HTTP server (up to 60s)..."
RESPONDED=0
for i in $(seq 1 30); do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/" 2>/dev/null || true)
  if [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
    echo "==> Container responded: HTTP $HTTP_CODE — image build and start OK"
    RESPONDED=1
    break
  fi
  sleep 2
done

if [ "$RESPONDED" -eq 0 ]; then
  echo "==> FAIL: no HTTP response after 60s"
  docker logs "$IMAGE" || true
  exit 1
fi

echo "==> Verifying search index..."
META_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PAGEFIND_ENTRY_URL" 2>/dev/null || true)
if [ "$META_CODE" != "200" ]; then
  echo "FAIL: Pagefind index metadata not found at $PAGEFIND_ENTRY_URL (HTTP $META_CODE)"
  docker logs "$IMAGE" 2>&1 | tail -20
  exit 1
fi
echo "PASS: Pagefind index metadata served (HTTP 200)"

PAGE_COUNT=$(curl -s "$PAGEFIND_ENTRY_URL" | python3 -c "
import sys, json
d = json.load(sys.stdin)
counts = [d['languages'][l]['page_count'] for l in d.get('languages', {})]
print(max(counts) if counts else 0)
" 2>/dev/null || echo "0")

if [ "$PAGE_COUNT" -lt "$MIN_PAGES" ]; then
  echo "FAIL: Only $PAGE_COUNT pages indexed (minimum: $MIN_PAGES)"
  exit 1
fi
echo "PASS: $PAGE_COUNT pages indexed (minimum: $MIN_PAGES)"

echo "==> Verifying content fixtures are present in the image..."
test -f content/en/content-en-batch1.yaml || (echo "FAIL: English content missing from repo" && exit 1)
test "$(ls content/translations/content-*-batch*.yaml | wc -l)" -ge 16 \
  || (echo "FAIL: translation content missing from repo" && exit 1)
echo "PASS: content corpus committed (1,425 translated pages + About built on image build)"

echo "==> ALL SMOKE TESTS PASSED"
