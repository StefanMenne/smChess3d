"""Gleicht die Texturen einer Ritterfigur an den Bauern an, direkt in der GLB (Rig, Animationen, Mesh bleiben).

  python3 tools/ritter/tex_angleich.py in.glb out.glb [--hue -0.05] [--metal 0.85] [--rough 0.8] [--dark 0.4]
                                                       [--keep-above 0.84]

- --hue: verschiebt den Farbton aller deutlich blauen Pixel der Grundfarbe (Anteil des Farbkreises; negativ =
  weg von Violett, zum Blau des Bauern hin)
- Stahl = wenig gesättigte Pixel (auch warmgraue Schattenpartien), ohne Blau und Gold. image_to_3d malt Rüstungen
  manchmal hell mit eingebrannten Glanzlichtern, kaum als Metall markiert und glatt; im warmen Brettlicht wirken
  sie dann bronzen. Für den Stahl: --metal Mindest-Metallwert, --rough Mindest-Rauheit, --dark Helligkeitsfaktor der
  Grundfarbe; der Farbton wird kühlgrau wie beim Stahl des Bauern. Immer auf die unbearbeitete GLB anwenden.
- --keep-above: Flächen, die ganz über diesem Anteil der Höhe liegen, bleiben unverändert (z. B. die weiße Mitra
  des Läufers, die sonst als Stahl gälte); ihre hellen, ungesättigten Pixel werden zu Stoff (kein Metall, matt)
Braucht nur Pillow.
"""
import io
import json
import struct
import sys

from PIL import Image, ImageChops, ImageDraw

args = sys.argv[1:]
SRC, DST = args[0], args[1]
opt = dict(zip(args[2::2], args[3::2]))
HUE = float(opt.get("--hue", -0.05))
METAL = float(opt.get("--metal", 0.85))
ROUGH = float(opt.get("--rough", 0.8))
DARK = float(opt.get("--dark", 0.4))
KEEP = float(opt["--keep-above"]) if "--keep-above" in opt else None

data = open(SRC, "rb").read()
jlen = struct.unpack("<I", data[12:16])[0]
gltf = json.loads(data[20:20 + jlen])
bin_off = 20 + jlen + 8
binary = data[bin_off:bin_off + struct.unpack("<I", data[20 + jlen:24 + jlen])[0]]
views = [binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]] for v in gltf["bufferViews"]]


def image_of(tex):
    src = gltf["images"][gltf["textures"][tex["index"]]["source"]]
    return src, Image.open(io.BytesIO(views[src["bufferView"]]))


def store(src, im):
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    src["mimeType"] = "image/jpeg"
    views[src["bufferView"]] = buf.getvalue()


def band(ch, lo, hi):
    """Maske 255 für lo <= Kanalwert <= hi."""
    return ImageChops.multiply(ch.point(lambda x: 255 if x >= lo else 0), ch.point(lambda x: 255 if x <= hi else 0))


pbr = gltf["materials"][0]["pbrMetallicRoughness"]
bsrc, base = image_of(pbr["baseColorTexture"])
base = base.convert("RGB")
h, s, v = base.convert("HSV").split()
blue = ImageChops.multiply(band(h, int(0.55 * 255), int(0.80 * 255)), band(s, 64, 255))
shift = round(HUE * 255)
h2 = Image.composite(h.point(lambda x: (x + shift) % 256), h, blue)
# Stahl: Sättigung < 70, nicht ganz dunkel, kein Blau
steel = ImageChops.multiply(ImageChops.multiply(band(s, 0, 70), band(v, 40, 255)), ImageChops.invert(blue))


def accessor(i):
    a = gltf["accessors"][i]
    bv = gltf["bufferViews"][a["bufferView"]]
    fmt = {5126: "f", 5125: "I", 5123: "H", 5121: "B"}[a["componentType"]]
    k = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
    raw = views[a["bufferView"]][a.get("byteOffset", 0):]
    stride = bv.get("byteStride", struct.calcsize(fmt) * k)
    return [struct.unpack_from("<" + fmt * k, raw, j * stride) for j in range(a["count"])]


if KEEP is not None:   # Flächen oben (glTF: y = oben) in UV-Koordinaten als Maske zeichnen und aussparen
    keep = Image.new("L", base.size, 0)
    dk = ImageDraw.Draw(keep)
    W_, H_ = base.size
    for mesh in gltf["meshes"]:
        for prim in mesh["primitives"]:
            pos = accessor(prim["attributes"]["POSITION"])
            uv = accessor(prim["attributes"]["TEXCOORD_0"])
            idx = [t[0] for t in accessor(prim["indices"])]
            y0, y1 = min(p[1] for p in pos), max(p[1] for p in pos)
            lim = y0 + KEEP * (y1 - y0)
            for t in range(0, len(idx), 3):
                tri = idx[t:t + 3]
                if all(pos[j][1] > lim for j in tri):
                    dk.polygon([(uv[j][0] * W_, uv[j][1] * H_) for j in tri], fill=255)
    steel = ImageChops.multiply(steel, ImageChops.invert(keep))
    cloth = ImageChops.multiply(keep, ImageChops.multiply(band(s, 0, 60), band(v, 120, 255)))
else:
    cloth = None
s2 = Image.composite(s.point(lambda x: 15), s, steel)       # fast neutrales, leicht kühles Grau
h2 = Image.composite(h.point(lambda x: 140), h2, steel)
v2 = Image.composite(v.point(lambda x: round(x * DARK)), v, steel)
store(bsrc, Image.merge("HSV", (h2, s2, v2)).convert("RGB"))

if "metallicRoughnessTexture" in pbr:
    msrc, mr = image_of(pbr["metallicRoughnessTexture"])
    mr = mr.convert("RGB")
    st = steel if steel.size == mr.size else steel.resize(mr.size)
    r, g, b = mr.split()
    g = Image.composite(g.point(lambda x: max(x, round(ROUGH * 255))), g, st)
    b = Image.composite(b.point(lambda x: max(x, round(METAL * 255))), b, st)
    if cloth is not None:
        cl = cloth if cloth.size == mr.size else cloth.resize(mr.size)
        g = Image.composite(g.point(lambda x: 230), g, cl)
        b = Image.composite(b.point(lambda x: 0), b, cl)
    store(msrc, Image.merge("RGB", (r, g, b)))

# Binärteil neu packen (4-Byte-Ausrichtung)
out = b""
for i, chunk in enumerate(views):
    gltf["bufferViews"][i]["byteOffset"] = len(out)
    gltf["bufferViews"][i]["byteLength"] = len(chunk)
    out += chunk + b"\0" * (-len(chunk) % 4)
gltf["buffers"][0]["byteLength"] = len(out)
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * (-len(js) % 4)
glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(out))
glb += struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(out)) + b"BIN\0" + out
open(DST, "wb").write(glb)
n = base.size[0] * base.size[1]
print(f"geschrieben {DST}: Farbton {HUE:+.3f} auf {blue.histogram()[255] / n:.0%}, Stahl {steel.histogram()[255] / n:.0%} "
      f"(Metall >= {METAL}, Rauheit >= {ROUGH}, Helligkeit x {DARK})")
