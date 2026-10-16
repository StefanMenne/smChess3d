#!/usr/bin/env bash
# Startet das Schachspiel (Linux/macOS)
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js wurde nicht gefunden. Bitte installieren: https://nodejs.org" >&2
  exit 1
fi

if [ ! -d node_modules ]; then
  echo "Installiere Abhängigkeiten ..."
  npm install
fi

# Chromium für Playwright herunterladen, falls noch nicht vorhanden
npx playwright install chromium

exec npm start
