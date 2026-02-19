#!/bin/bash
# autopush.sh — auto commit + push every 5 minutes
# Usage: bash autopush.sh
# Stop with: Ctrl+C

INTERVAL=300  # seconds

echo "[autopush] Started — committing every ${INTERVAL}s. Ctrl+C to stop."

while true; do
    sleep $INTERVAL

    cd /workspaces/CamPark

    # Check if there's anything to commit
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
        echo "[autopush] $(date '+%H:%M:%S') — nothing to commit, skipping"
        continue
    fi

    git add -A
    MSG="auto: $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$MSG"
    git push origin main && echo "[autopush] $(date '+%H:%M:%S') — pushed: $MSG" \
                         || echo "[autopush] $(date '+%H:%M:%S') — push FAILED"
done
