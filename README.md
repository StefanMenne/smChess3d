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
