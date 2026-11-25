# Staunton-Satz (gedrechselt)

Klassische Staunton-Figuren. Bauer, Turm, Läufer, Dame und König sind Rotationskörper aus Profilen in
`drehen.py`; nur der Springerkopf ist ein 3D-Modell aus image_to_3d. Alle Figuren sind starr (ohne Skelett);
das Spiel lässt sie gleiten, den Springer im Bogen springen (`rigid`, `jump` in `PIECE_SET_LOOK`).

## Springerkopf

1. Bild: gb10-assets `generate_image` (Qwen-Image-2512), 1104×1472, seed 11, Ergebnis `springer_vorlage.jpg`
   (verkleinert):
   > Product photo of a single classic Staunton chess knight piece, turned and carved from smooth plain pale
   > boxwood with no visible grain, elegant horse head with carved mane, open mouth and ears, on a round turned
   > pedestal with a collar and wide base. Three-quarter view from the front left, slightly above, the whole
   > piece fully visible and filling most of the image, centered. Plain light grey seamless studio background,
   > soft even lighting, no shadow, no other objects, no board.
2. 3D: `image_to_3d` (Pixal3D), seed 42, max_faces 80000, texture_size 1024.
3. `glb_post model_42.glb springer_kopf.glb --height 1.0 --tex 1024` → `springer_kopf.glb` (hier abgelegt).

## Satz bauen

Mit dem gb10-assets-Tool `blender` (eigener Code), Eingabedateien `drehen.py` und `springer_kopf.glb`:

```python
import runpy, sys
sys.argv = ["drehen.py", ".", "--knight", "springer_kopf.glb", "--tex", "2048", "--preview", "lineup.png"]
runpy.run_path("drehen.py", run_name="__main__")
```

Die zwölf GLBs kommen nach `public/assets/sets/staunton/`. `drehen.py` schneidet den generierten Sockel des
Springers ab (`KNIGHT_CUT`), dreht den Kopf nach vorn (`KNIGHT_YAW`) und setzt ihn auf einen gedrechselten
Sockel. Das Holz (Weiß Buchsbaum, Schwarz Ebenholz) ist eine prozedurale 3D-Maserung, mit Cycles in eine
Farbtextur gebacken; die Textur des generierten Kopfs wird verworfen.
