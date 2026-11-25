# Umgebung (HDR)

`public/assets/umgebung/raum.hdr` ist ein selbst gerendertes Rundum-Bild eines Arbeitszimmers. Es beleuchtet
die Szene im Spiel von allen Seiten und gibt Metall, Lack und Glas etwas zu spiegeln (vorher: der synthetische
graue `RoomEnvironment`-Raum von three.js, in dem senkrechte Metallflächen einfarbig grau wirkten).

Erzeugt mit `raum.py` auf dem GB10 (gb10-assets-Tool `blender`, eigener Code, Cycles auf der GPU):

```python
import runpy, sys
sys.argv = ["raum.py", "raum.hdr", "--size", "2048", "--samples", "512", "--preview", "raum_vorschau.jpg"]
runpy.run_path("raum.py", run_name="__main__")
```

Abgestimmt: Fenster und Sonne links vorn (wie die Sonne im Spiel), Pendelleuchte gedämpft (sonst wird alles
nach oben Gewandte, vor allem das Brett, blass). Im Spiel: `ENV_HDR_INTENSITY` (Helligkeit) und `ENV_ROTATION`
(Ausrichtung) in `public/main.js`; `?umgebung=studio` zeigt zum Vergleich den alten synthetischen Raum.
