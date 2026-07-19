#!/bin/bash
set -euo pipefail

SHARED_DIR="${SHARED_DIR:-/opt/manim/shared/videos/template_examples}"

mkdir -p "$SHARED_DIR"

for src in \
  /opt/manim/backend/videos/template_examples \
  /opt/manim-v2/backend/videos/template_examples \
  /opt/manim-v2-3003-snapshot/backend/videos/template_examples \
  /opt/manim/backend/app/videos/template_examples \
  /opt/manim-v2/backend/app/videos/template_examples \
  /opt/manim-v2-3003-snapshot/backend/app/videos/template_examples
do
  if [ -d "$src" ]; then
    cp -an "$src"/*.mp4 "$SHARED_DIR"/ 2>/dev/null || true
  fi
done

echo "Shared template examples synced to: $SHARED_DIR"
ls -la "$SHARED_DIR"
