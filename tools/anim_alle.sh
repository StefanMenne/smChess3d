#!/bin/bash
# Eigene Bewegungen (ohne Mixamo) für die Schnitzfiguren neu erzeugen und in die GLBs einsetzen.
#   tools/anim_alle.sh [figur ...]      z. B. tools/anim_alle.sh dame_weiss
# Ohne Argumente: alle zehn Figuren mit Menschen-Skelett (der Turm hat eigene Bewegungen aus rig_turm.py).
# Mesh und Material bleiben unverändert (anim_splice.py); vorher committen, um vergleichen zu können.
set -e
cd "$(dirname "$0")/.."
M=public/assets/sets/schnitz
TMP=$(mktemp -d)
FIGS=("$@")
[ ${#FIGS[@]} -eq 0 ] && FIGS=(bauer_weiss bauer_schwarz dame_weiss dame_schwarz koenig_weiss koenig_schwarz
  laeufer_weiss laeufer_schwarz springer_weiss springer_schwarz)
for n in "${FIGS[@]}"; do
  case $n in
    dame*)    OPT="--stride 0.6 --frames 24" ;;   # Trippelschritte unter dem langen Kleid (wie bisher)
    laeufer*) OPT="--stride 1.4" ;;               # Bischofsgewand: kürzere Schritte
    *)        OPT="" ;;
  esac
  blender -b --python tools/anim_figur.py -- "$M/$n.glb" "$TMP/$n.anim.glb" $OPT 2>&1 | grep -E "Beinlänge|Kniebeugung|Hüftweg|stride|Error|Traceback"
  python3 tools/anim_splice.py "$M/$n.glb" "$TMP/$n.anim.glb" "$TMP/$n.glb"
  mv "$TMP/$n.glb" "$M/$n.glb"
done
rm -rf "$TMP"
