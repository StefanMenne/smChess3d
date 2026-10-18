# Schach 3D

Schach gegen den Computer mit animierten 3D-Figuren (`pieces/*.glb`).

Schnellstart: `./start.sh` (Linux/macOS) bzw. Doppelklick auf `start.bat` (Windows).
Beide installieren beim ersten Start die Abhängigkeiten und Chromium automatisch.

```bash
npm install
npm start      # öffnet das Spiel in einem Chromium-Fenster (Playwright)
npm run serve  # nur Server auf http://127.0.0.1:3000, im eigenen Browser öffnen
npm test       # Playwright-Tests
```

- **Bedienung:** Figur anklicken → mögliche Felder werden markiert → Zielfeld anklicken.
  Mit gedrückter Maustaste ziehen dreht die Kamera, Mausrad zoomt.
- **Regeln:** [chess.js](https://github.com/jhlywa/chess.js) (Rochade, en passant, Umwandlung, Remis-Regeln).
- **Computer:** Alpha-Beta-Suche im Web Worker (`public/ai-worker.js`), vier Stärkestufen.
- **Grafik:** Three.js; Figuren nutzen die Animationen `Idle` und `Walk` aus den GLB-Dateien.

## Verwendete Werkzeuge und Lizenzen

### Im Spiel enthalten

| Komponente | Version | Lizenz | Quelle |
|---|---|---|---|
| three.js | 0.186.1 | MIT | https://github.com/mrdoob/three.js |
| chess.js | 1.4.0 | BSD-2-Clause | https://github.com/jhlywa/chess.js |
| Playwright (Start-Fenster, Tests) | 1.64.1 | Apache-2.0 | https://github.com/microsoft/playwright |

### Erzeugung der Figuren (`pieces/*.glb`)

Die Figuren wurden mit dem Projekt `~/dev/3dpipe` erzeugt: Bild (FLUX.2) → 3D-Mesh und Textur (TRELLIS.2)
→ Nachbearbeitung, Rig und Animationen (Blender). Keine dieser Komponenten wird mit dem Spiel ausgeliefert.

DINOv3 und BiRefNet stehen nicht im TRELLIS.2-Repository. Es sind vortrainierte Modelle, die TRELLIS.2
beim Start von Hugging Face lädt (eingetragen in `pipeline.json` / `texturing_pipeline.json` des Modells
`microsoft/TRELLIS.2-4B`).

| Komponente | Wofür | Lizenz | Quelle |
|---|---|---|---|
| FLUX.2 [klein] 4B (Black Forest Labs) | Bildvorlagen der Tiere | Apache-2.0 | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B |
| Diffusers 0.41.0 | FLUX ausführen | Apache-2.0 | https://github.com/huggingface/diffusers |
| TRELLIS.2 (Microsoft), Modell `TRELLIS.2-4B` | Bild → 3D-Mesh, Textur | MIT | https://github.com/microsoft/TRELLIS.2 |
| O-Voxel (Teil von TRELLIS.2) | Voxel → Mesh, Textur backen | MIT | https://github.com/microsoft/TRELLIS.2 |
| DINOv3 ViT-L/16 (Meta), `dinov3-vitl16-pretrain-lvd1689m` | Bild-Encoder von TRELLIS.2 (unverzichtbar) | DINOv3 License | https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m |
| BiRefNet (`ZhengPeng7/BiRefNet`) | Hintergrund freistellen (statt RMBG-2.0) | MIT | https://github.com/ZhengPeng7/BiRefNet |
| CuMesh, FlexGEMM | Mesh-Vereinfachung, Sparse-Faltung | MIT | https://github.com/JeffreyXiang/CuMesh, https://github.com/JeffreyXiang/FlexGEMM |
| FlashAttention 2.8.3 | Attention-Berechnung in TRELLIS.2 | BSD-3-Clause | https://github.com/Dao-AILab/flash-attention |
| nvdiffrast 0.4.0 (NVIDIA) | Rasterisierung beim Textur-Backen | NVIDIA Source Code License, **nur nicht-kommerziell** | https://github.com/NVlabs/nvdiffrast |
| Blender 5.2.2 LTS | Nachbearbeitung, Rig, Animationen | GPL (gilt nicht für erzeugte Dateien) | https://www.blender.org |

Hinweise:

- **nvdiffrast** darf laut Lizenz nur „non-commercially … for research or evaluation purposes only“
  genutzt werden. Für ein privates Spiel passt das. Bei kommerzieller Nutzung ist zu klären, ob das auch
  für die damit erzeugten Texturen gilt.
- **nvdiffrec** wird vom TRELLIS.2-Setup ebenfalls installiert (gleiche NVIDIA-Lizenz), aber nur für
  Vorschau-Videos und Training gebraucht, nicht auf unserem Weg zu den Figuren. Daher nicht aufgeführt.
- Die Original-Konfiguration von TRELLIS.2 nennt **RMBG-2.0** (briaai, CC BY-NC 4.0). Wir nutzen
  stattdessen BiRefNet (MIT), damit entfällt diese Einschränkung.
- **DINOv3 License**: Weitergabe der Modellgewichte nur zusammen mit dem Lizenztext. Wir geben sie nicht weiter, nur
  die damit erzeugten Figuren; eine Namensnennung ist nicht vorgeschrieben, im Info-Dialog aber freundlich.

### Textvorschlag für den Info-Dialog

> Spiel: three.js (MIT), chess.js (BSD-2-Clause), Playwright (Apache-2.0).
> Figuren erzeugt mit FLUX.2 [klein] (Black Forest Labs, Apache-2.0), TRELLIS.2 (Microsoft, MIT) mit
> DINOv3 (Meta, DINOv3 License), BiRefNet (MIT), FlashAttention (BSD-3-Clause), CuMesh/FlexGEMM (MIT)
> und nvdiffrast (NVIDIA, nicht-kommerzielle Lizenz) sowie Blender.
