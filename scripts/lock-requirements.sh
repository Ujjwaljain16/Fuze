#!/usr/bin/env bash
# Regenerate requirements.lock: every package the production image installs, at the exact
# version and file hash pip picks on the image's platform (python:3.11, linux x86_64).
# Run after changing requirements.txt; commit both files together.
set -euo pipefail
cd "$(dirname "$0")/.."

docker run --rm -v "$PWD:/src" -w /src python:3.11 sh -c '
  pip install --quiet --upgrade pip >/dev/null 2>&1
  pip install --dry-run --quiet --ignore-installed --report /tmp/report.json \
      --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt 2>/dev/null
  python /src/scripts/_write_lock.py /tmp/report.json requirements.lock'
