# Tierschach: wiedergefundene Prompts (FLUX.2 [klein], Oktober 2026)

Quelle: Claude-Code-Sitzung `~/.claude/projects/-home-stefan-dev-chess-pieces/f5ff84d0-….jsonl` (28.10.2026).
Dort wurde `head -15` auf die alten Skripte ausgeführt – daher nur deren Anfang. Die Skripte selbst
(`~/dev/chess_pieces/schach/bildvorlagen/`, früher `~/dev/asset_pipe/assets/schach/`) existieren nicht mehr.

## 1. vorschlaege.sh – Text-zu-Bild, je 5 Vorschläge (N=5, SEED0=11)

STYLE (an jeden Figuren-Prompt angehängt):

> Cute chibi 3D toy figure, glossy vinyl designer toy, soft rounded shapes, smooth plastic shading, Pixar-like
> 3D render. Three-quarter view from the front-left, body turned about 35 degrees. Big shiny eyes, happy friendly
> smile, cheerful bright saturated colors. No outlines, no line art. Full body centered, plain pure white
> background, soft even studio lighting, no ground shadow.

| Figur | Prompt |
|---|---|
| Bauer (Eichhörnchen, später durch Hase ersetzt) | A cute little squirrel chess pawn standing on its hind legs, holding a big acorn with both paws, large fluffy curled tail, warm orange-brown fur, cream belly, pink cheeks. |
| Springer (Pony) | A cute little pony chess knight, caramel-colored coat, dark brown mane and tail, cream muzzle, pink cheeks, all four legs clearly visible. |
| Läufer (Schaf) | A cute fluffy little sheep chess bishop wearing a tall white bishop's mitre with gold trim, creamy white curly wool, pale pink face and ears, small gold cross on the chest, all four legs clearly visible. |
| Turm (Schnecke) | A cute little snail chess rook, bright green body, two eye stalks, big brown spiral shell with a grey stone castle tower with battlements on top of the shell, pink cheeks. |
| Dame (Giraffe) | **fehlt** (nach Zeile 15 abgeschnitten) |
| König (Elefant) | **fehlt** (nach Zeile 15 abgeschnitten) |

Gewählte Vorschläge: Bauer 3, Springer 1, Läufer 4, Turm 1, Dame 3, König 1.

## 2. farben.sh – Umfärben in Weiß/Schwarz per FLUX-Bearbeitung (SEED=3)

BASE:

> Recolor this 3D toy figure. Keep exactly the same pose, shape, proportions, viewing angle, accessories, face,
> big shiny eyes, happy smile, lighting and plain white background. Only change the colors, all colors matte and
> non-metallic except gold parts. New colors:

Erhaltene Farbzeilen (nur der Anfang, Eichhörnchen-Bauer weiß):
- snow white fur, cream belly, warm brown acorn, pink ears and cheeks
- creamy ivory fur, white belly, golden yellow acorn, pink cheeks

Vorgaben laut Notizen: Schwarz = Braun (~RGB 100,70,50), Gold nur an Kronen/Mitra/Kreuz, Elefant behält rote
Jacke und goldene Krone, weißer König darf hellblau bleiben. (`farben2.sh`/`farben2.txt`: nicht erhalten.)

## 3. korrektur.sh – Runde 3 (19.10.), FLUX-Bearbeitung auf final/<figur>_<farbe>.png

BASE:

> Edit this 3D toy figure. Keep exactly the same pose, body shape, proportions, viewing angle, colors (except as
> stated), big shiny eyes, lighting and plain white background. Do not add any new objects or accessories. All
> colors matte. Changes:

korrektur.txt (vollständig erhalten):

```
bauer_schwarz|the head is much larger relative to the body, cute chibi proportions; the face is a slightly lighter medium brown (RGB 140,95,65), still clearly brown, not yellow or beige; a wide open happy smile with a dark red mouth and pink tongue
bauer_schwarz|the head is 25 percent larger; only the muzzle and cheeks a slightly lighter medium hazel brown (RGB 150,105,70), the rest of the head stays brown; a big open laughing mouth with pink tongue, clearly visible
bauer_schwarz|the head is much larger relative to the body; the face a medium milk-chocolate brown (RGB 135,90,60), not yellow; a wide grin with open mouth showing the pink tongue and two front teeth
bauer_schwarz|the head and ears are larger, big cute head; the face a slightly lighter warm brown (RGB 145,100,65); the smiling mouth twice as wide and open, dark red inside
bauer_schwarz|the head is clearly bigger, like a baby animal; the face medium brown (RGB 140,95,60) with a lighter tan muzzle; a big happy open-mouth smile, the mouth is the most visible feature of the face
turm_schwarz|keep the light grey castle tower on top of the shell exactly as it is; keep the eye stalks dark brown; the face only slightly lighter, a medium brown (RGB 130,85,55); the black pupils move to the right side of each eye, looking sideways
turm_schwarz|keep the light grey castle tower on top of the shell exactly as it is; keep the eye stalks dark brown; the face only slightly lighter, a medium brown (RGB 135,90,60); the black pupils move up, looking slightly upward
turm_schwarz|keep the light grey castle tower on top of the shell exactly as it is; keep the eye stalks dark brown; the face only slightly lighter, a warm medium brown (RGB 130,85,55); the black pupils move to the upper right of each
```
Gewählt: Bauer schwarz 2, Turm schwarz 1. (Gehörte noch zum Eichhörnchen-Bauern.)

## Nicht gefunden

- Prompts für Dame (Giraffe) und König (Elefant) aus `vorschlaege.sh`
- `bauer_neu.sh` (10 Eichhörnchen + 10 andere Tiere → Hase gewählt) und `hase_farben.sh` (Weiß 4 Cremeweiß,
  Schwarz 2 Schokobraun mit cremebeiger Schnauze/Bauch)
- `farben2.sh` / `farben2.txt`
