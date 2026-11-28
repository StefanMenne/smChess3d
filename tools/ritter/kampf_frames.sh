#!/bin/bash
# Einzelbilder eines LTX-Videos (generate_video frames=True, Grün-Hintergrund) freistellen und als WebP mit Alpha
# für das Spiel ablegen:
#   tools/ritter/kampf_frames.sh video_<seed>_frames.zip public/assets/sets/ritter/kampf/<ordner> [groesse=1024] [treffer] [bilder]
# treffer: bei Angriffsvideos das Bild, in dem die Waffe das Opfer trifft (dort startet das Sterbevideo), sonst -
# bilder:  nur die ersten so vielen Bilder nehmen (Sterbevideo kürzen, sobald das Opfer still liegt)
# Chromakey auf das Grün, das LTX aus dem Reingrün der Vorlagen macht (gemessen um 07EB03), Grünstich an den Rändern entfernen (despill), dann meta.json.
set -e
ZIP=$1; OUT=$2; SIZE=${3:-1024}; HIT=${4:-}; [ "$HIT" = - ] && HIT=; COUNT=$5
[ -f "$ZIP" ] && [ -n "$OUT" ] || { echo "Aufruf: $0 frames.zip zielordner [groesse]"; exit 1; }
TMP=$(mktemp -d)
unzip -q "$ZIP" -d "$TMP"
mapfile -t PNGS < <(find "$TMP" -name '*.png' | sort | head -n "${COUNT:-100000}")
[ ${#PNGS[@]} -gt 0 ] || { echo "keine PNGs in $ZIP"; exit 1; }
mkdir -p "$OUT"
rm -f "$OUT"/*.webp
i=0
for f in "${PNGS[@]}"; do ln -s "$f" "$TMP/in_$(printf %04d $i).png"; i=$((i+1)); done
ffmpeg -loglevel error -i "$TMP/in_%04d.png" \
  -vf "format=rgba,chromakey=0x07eb03:0.13:0.06,despill=type=green:mix=0.6:expand=0.2,scale=${SIZE}:${SIZE}" \
  -c:v libwebp -quality 82 -start_number 0 -f image2 "$OUT/%03d.webp"
N=$(ls "$OUT"/*.webp | wc -l)
echo "{ \"frames\": $N, \"fps\": 24, \"size\": $SIZE${HIT:+, \"hit\": $HIT} }" > "$OUT/meta.json"
rm -rf "$TMP"
du -sh "$OUT"; cat "$OUT/meta.json"
