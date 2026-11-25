# Tierfiguren neu erzeugen (Stand 2026-11-23)

Die Tierfiguren stammen aus dem Repo StefanMenne/smChess3d (`public/assets/sets/tiere/`). Ihre ursprünglichen
Skripte sind verloren; diese hier sind aus einer alten Claude-Code-Sitzung rekonstruiert bzw. neu geschrieben.
Die alte Anleitung: `README_2026-10-28.md` (Pfade darin sind veraltet). Prompts: `prompts.md`.

Ablauf je Figur und Farbe (Zwischenstände in `konzepte/tierschach/<figur>_<farbe>_neu/`, nicht im Repo):

1. Bild: GB10 `generate_image` (Qwen-Image-2512; FLUX.2 [klein] gibt es nicht mehr) mit dem Stil-Prompt aus
   `prompts.md`. Schwarz: das gewählte weiße Bild per `edit_image` umfärben (gleiche Pose), BASE-Prompt aus farben.sh.
   Mehrere Varianten, der User wählt.
2. Mesh: GB10 `image_to_3d`, seed 42, max_faces 10000, texture_size 2048.
3. `blender -b --factory-startup --python prep.py -- raw.glb prep.glb --yaw <grad>` (Winkel mit views.py --yaw suchen).
   prep.py verschmilzt jetzt zuerst die glTF-Nähte (sonst löscht die Inselsuche Kopf/Körper).
4. Augen (GB10, eigener Code `eyes_chain.py`): automatisch, mit `--find-opts=--eyes …` oder
   `--eyes-json` (von Hand: eyepick.py-Raster ablesen, eyes_json.py auf die glb_post-Fassung).
5. Rig (GB10): Pony/Schaf/Giraffe `rig_quadruped`, Hase/Elefant `rig_biped`, Schnecke `rig_snail.py`
   (neu geschrieben: Kriechwelle per Verschiebung, Haus starr). Parameter siehe README-Tabelle.
6. Prüfen: `frames.py` (Walk/Idle-Einzelbilder, Blender), dann im Spiel.

Gemacht: alle Figuren in Weiß und Schwarz (24.11.). Die Originale (`*_original.glb`) wurden am 25.11. gelöscht (in der git-History noch vorhanden).

Springer weiß v2 (24.11.): per `edit_image` aus der schwarzen Vorlage (froehlich_B/image_71) umgefärbt — schneeweißes
Fell, Mähne flieder mit rosa Strähnen, fliederfarbene Hufe (Seed 201). Prompt: BASE aus farben.sh + "snow white coat,
pastel lavender and soft lilac mane and tail with light pink strands, pale pink muzzle, rosy pink cheeks, pink inner
ears, pale lilac-grey hooves with white socks, warm brown eyes". yaw 32, Augen von Hand `0.330,0.716;0.850,0.713`
--r 0.042 (tex_eyes automatisch setzte sie zu weit außen/ungleich), Rig wie README. Gesättigte Farben übersteht
Pixal3D gut, nur sehr helles Creme kippt ins Pfirsich.

Turm weiß v2 (24.11.): per `edit_image` aus image_23 (gleiche Pose), Prompt: „Make the eyes much bigger: huge round
shiny cute eyes … snow white body, pastel mint turquoise shell with a white spiral line, very light pale grey almost
white stone castle tower, light turquoise tips on the eye stalks, rosy pink cheeks“ (Seed 502). yaw 38. Augen: tex_eyes
automatisch, Radius ×1.25 (`augen/turm_weiss_gross.json`), `--cover-opts=--only-dark 0.85` (sonst schmiert die
Übermalung Mint vom Haus ums Auge), danach `eye_iris.py` (braune Iris + kleinere Pupille; neu, weil das Augenweiß auf
weißem Körper sonst verschwindet und die Augen wie Knöpfe wirken). Rig: `rig_snail.py --landmarks
turm_weiss_v2_landmarks.json --walk 0.8 --height 0.78` (Kopf mittiger als bei der alten Schnecke: head_x 0.465).

Turm schwarz (24.11.): per `edit_image` aus der weißen v2-Vorlage (turm_weiss_v2/B_mint/image_502, gleiche Pose, Seed
602), 4 Varianten, gewählt B: BASE + "milk chocolate brown body, rosy pink cheeks, raspberry pink and berry red snail
shell with a light pink spiral line, dark brown stone castle tower, sunny golden yellow tips on the eye stalks".
yaw 38. tex_eyes greift wieder die Fühlerkugeln -> Augen von Hand `0.332,0.539;0.687,0.533`, r in der JSON auf 0.052
(wie Weiß), dann `eye_iris.py` (Standardwerte). Rig lokal: `rig_snail.py --landmarks turm_weiss_v2_landmarks.json
--walk 0.8 --height 0.78`.

Läufer weiß (24.11.): neu per `generate_image` (keine alte Vorlage mehr), STYLE aus prompts.md + "A cute fluffy little
sheep chess bishop wearing a tall bishop's mitre, snow white curly wool, pale pink face and pink inner ears, rosy pink
cheeks, huge round shiny cute brown eyes, all four legs clearly visible with light mint hooves. The mitre is pastel mint
turquoise with a white band and soft gold trim and a small gold cross on the front, small gold cross pendant on the
chest." (Seed 702; 4 Mitra-Farben, gewählt Mint). yaw 28. Augen: tex_eyes automatisch richtig, Radius ×1.25
(`augen/laeufer_weiss_gross.json`), `--cover-opts=--only-dark 0.85`, dann `eye_iris.py`. Rig wie README.

Läufer schwarz (24.11.): per `edit_image` aus dem weißen Läufer (image_702) umgefärbt, gewählt Schoko/Himbeere
(image_801, Mitra himbeer wie das Schneckenhaus), dann mit dem schwarzen Springer als zweitem Eingabebild auf dessen
Braun gezogen ("Recolor the curly wool of the sheep in image 1 to exactly the same warm reddish caramel brown as the coat
of the pony in image 2 …", Seed 811). **Hauptfarbe aller schwarzen Tiere = Braun des schwarzen Springers** (Render-Median
H19 S0.53 V0.44). Pixal3D machte die Wolle trotzdem ockergelb (H32 S0.80) -> `farbton.py prep_schwarz.glb
prep_schwarz_braun.glb --smin 0.58 --vmax 0.72 --to-h 19 --sfac 0.66 --vfac 1.1` (Wolle liegt bei S>=0.6/V<=0.7, Gold
und Gesicht bei S 0.2–0.5, so bleibt das Kreuz golden). yaw 28; Augen tex_eyes automatisch, r 0.0397 wie Weiß
(`augen/laeufer_schwarz_gross.json`), `--only-dark 0.85`, `eye_iris.py`. Rig wie README.

König weiß (24.11.): neu per `generate_image`, STYLE + "A cute little baby elephant chess king standing upright on its
two hind legs like a person, short chubby legs and small arms, snow white skin, big round ears with pink inner ears,
rosy pink cheeks, huge round shiny cute brown eyes, short curled trunk, wearing a shiny gold royal crown with small
jewels and a short royal cape in pastel sky blue velvet with gold trim and little gold stars, a small pink bow tie,
both feet clearly visible." (Seed 904). Qwen malt die Haut hellgrau -> per `edit_image` "Only change the elephant's grey
skin to pure snow white, like a white porcelain toy" (Seed 914). Pixal3D macht den eingerollten Rüssel lang und gerade
(wie beim alten König). yaw 20 (Bild frontaler als sonst). Augen von Hand `0.370,0.615;0.630,0.603` --r 0.045
(tex_eyes ungleich groß), `--only-dark 0.85`, `eye_iris.py`. Rig wie README; der Umhangsaum wird im Walk etwas vom
Bein mitgezogen (wie beim alten König).

König schwarz (24.11.): per `edit_image` aus dem weißen König (image_914) mit dem schwarzen Springer als zweitem Bild
("the elephant's skin exactly the same warm reddish caramel brown as the pony's coat in image 2 … the cape rich royal
purple velvet; a golden yellow bow tie", Seed 922; 4 Umhangfarben, gewählt Purpur). yaw 20. Haut nach Pixal3D zu hell
(Render V0.55) -> `farbton.py --h 5,35 --smin 0.65 --vmax 0.65 --to-h 20 --sfac 1.12 --vfac 0.8` (Render H16 S0.49
V0.46). tex_eyes findet auf der braunen Haut nur die Brauen -> Augen von Hand `0.366,0.622;0.641,0.611` --r 0.045
(eyes_json auf die *_post.glb), Cover ohne only-dark, `eye_iris.py`. Rig wie README.

Dame weiß (24.11.): neu per `generate_image`, STYLE + "A cute little baby giraffe chess queen standing on all four legs,
snow white coat with soft pastel pink patches, short cute neck, big head, small rounded ossicones with pink tips, pink
inner ears, rosy pink cheeks, huge round shiny cute brown eyes with long lashes, pastel pink mane and tail tuft, pale pink
hooves, wearing a small shiny gold queen's crown with pink jewels, all four legs clearly visible." (Seed 1001), dann die
himmelblaue Schleife aus Variante D (Seed 1004, "a little sky blue ribbon bow at the neck") per `edit_image` mit zwei
Bildern übernommen (Seed 1011). Pixal3D machte das Fell cremegelb -> `farbton.py --h 25,70 --smin 0.03 --smax 0.27
--vmin 0.8 --vmax 1.0 --to-h 40 --sfac 0.2 --vfac 1.03` (Gold der Krone liegt bei S 0.3–0.5 und bleibt). yaw 32. Augen:
tex_eyes automatisch richtig, r 0.0345 (`augen/dame_weiss_gross.json`), `--only-dark 0.85`, `eye_iris.py`. Rig:
`rig_quadruped --landmarks giraffe --walk 0.6 --stride 25 --knee 40 --height 1.1` (kurzer Hals, daher nicht 1.38).

Dame schwarz (24.11.): per `edit_image` aus der weißen Dame (image_1011) mit dem schwarzen Springer als zweitem Bild
("coat exactly the same warm reddish caramel brown as the pony's coat in image 2, with soft pink patches, soft pink mane
and tail tuft, light cream muzzle … the ribbon bow deep teal turquoise", Seed 1023). Achtung: das Pony-Bild färbt bei
manchen Seeds auch die Form ab (Pony-Mähne/-Schwanz). Pixal3D: Fell ocker, Schleife dunkelblau, Krone blass. Zwei
`farbton.py`-Durchgänge: Fell `--h 15,45 --smin 0.6 --vmax 0.75 --to-h 19 --sfac 0.8 --vfac 0.77` (Render H15 S0.44
V0.46), Schleife `--h 195,225 --smin 0.9 --vmin 0.42 --vmax 1.0 --to-h 182 --sfac 0.85 --vfac 1.1` (farbton.py kann
jetzt jeden Zielfarbton). yaw 32. Augen von Hand `0.340,0.698;0.703,0.680` --r 0.041, **`--skip-cover`**: tex_eyecover
holte Petrol aus der benachbarten Schleifen-Insel der UV-Karte; ohne Übermalen bleiben die schwarzen Wimpern. `eye_iris.py`,
Rig wie Dame weiß (Höhe 1.1).

Bauer weiß (24.11.): neu per `generate_image`, STYLE + "A cute little bunny chess pawn standing upright on its hind legs,
snow white fluffy fur, long upright ears with pink inner ears, rosy pink cheeks, pink nose, huge round shiny cute brown
eyes, holding a small orange carrot with green leaves in both front paws, round white fluffy tail, both feet clearly
visible." (Seed 1101; 4 Varianten mit/ohne Accessoire, gewählt ohne). Fell bleibt nach Pixal3D weiß, kein farbton nötig.
yaw 29 (ein Schnurrhaar fällt als Bruchstück weg). Augen: tex_eyes automatisch richtig, r 0.042
(`augen/bauer_weiss_gross.json`), `--only-dark 0.85`, `eye_iris.py`. Rig wie README (`rig_biped rabbit --mode hop`).

Bauer schwarz (24.11.): per `edit_image` aus dem weißen Hasen (image_1101), **ohne** Springer-Bild (mit Pony-Bild wurden
alle 4 Varianten zu Ponys), Braun als RGB im Text: "the fur warm reddish caramel brown (RGB 150, 95, 60), light cream
belly and cream muzzle, pink inner ears, rosy pink cheeks, cream fluffy tail" (Seed 1131). yaw 29. Fell nach Pixal3D
orange (Render H26 S0.73 V0.56) -> `farbton.py --h 12,40 --smin 0.6 --vmax 0.72 --to-h 19 --sfac 0.73 --vfac 0.79`
(Render H18 S0.54 V0.44; die Möhre ist heller als 0.72 und bleibt). Augen: tex_eyes-Positionen, r 0.042 wie Weiß,
`--skip-cover` (Übermalen zog Creme von der Schnauze unters Auge), `eye_iris.py`. Rig wie README.

Stand 24.11.: alle 12 Tierfiguren neu. Hauptfarbe Schwarz = Springer-Braun (Render-Median H15–19 S0.44–0.54 V0.44–0.46).
