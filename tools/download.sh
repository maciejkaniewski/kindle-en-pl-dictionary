#!/usr/bin/env bash
# Download source data (kaikki.org Wiktionary extracts) and the kindling compiler.
set -euo pipefail
cd "$(dirname "$0")/.."

KINDLING_VERSION="${KINDLING_VERSION:-v0.46.2}"
mkdir -p data/raw bin

fetch() {  # url dest
  if [[ -s "$2" ]]; then echo "have $2"; else echo "fetching $1"; curl -fL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"; fi
}

# Polish Wiktionary (English entries with Polish definitions)
fetch https://kaikki.org/dictionary/downloads/pl/pl-extract.jsonl.gz data/raw/pl-extract.jsonl.gz
# English Wiktionary, raw dump (~3 GB; English entries give inflected forms and Polish translations)
fetch https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz data/raw/raw-wiktextract-data.jsonl.gz

# kindling: MIT-licensed kindlegen replacement (https://github.com/ciscoriordan/kindling)
case "$(uname -s)" in
  Linux)  asset=kindling-cli-linux ;;
  Darwin) [[ "$(uname -m)" == arm64 ]] && asset=kindling-cli-mac-apple-silicon || asset=kindling-cli-mac-intel ;;
  *) echo "unsupported OS; download kindling manually into bin/kindling-cli"; exit 1 ;;
esac
fetch "https://github.com/ciscoriordan/kindling/releases/download/${KINDLING_VERSION}/${asset}" bin/kindling-cli
chmod +x bin/kindling-cli
