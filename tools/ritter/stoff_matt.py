"""Macht farbigen Stoff einer Ritterfigur matt und heller, direkt in der GLB (Rig, Animationen, Mesh bleiben).

  python3 tools/ritter/stoff_matt.py in.glb out.glb [--farbe blau|rot] [--hell 1.5] [--metal 0] [--rough 0.9]

image_to_3d markiert Stoff manchmal als Metall (weißer Springer: Umhang Metallwert ~1). Metall mit dunkler
Grundfarbe spiegelt nur die Umgebung und wirkt im Brettlicht fast schwarz, die Stofffarbe geht verloren.
- --farbe: welche Pixel als Stoff gelten (blau: Farbton 0,55–0,80; rot: um 0), jeweils Sättigung > 64
- --hell: Faktor für die Helligkeit (V) dieser Pixel
- --metal: höchster Metallwert, --rough: kleinste Rauheit für diese Pixel
Braucht nur Pillow.
"""
import io
import json
import struct
import sys

from PIL import Image, ImageChops

args = sys.argv[1:]
SRC, DST = args[0], args[1]
opt = dict(zip(args[2::2], args[3::2]))
FARBE = opt.get("--farbe", "blau")
HELL = float(opt.get("--hell", 1.5))
METAL = float(opt.get("--metal", 0))
ROUGH = float(opt.get("--rough", 0.9))

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
    return ImageChops.multiply(ch.point(lambda x: 255 if x >= lo else 0), ch.point(lambda x: 255 if x <= hi else 0))


pbr = gltf["materials"][0]["pbrMetallicRoughness"]
bsrc, base = image_of(pbr["baseColorTexture"])
h, s, v = base.convert("RGB").convert("HSV").split()
if FARBE == "blau":
    hue = band(h, int(0.55 * 255), int(0.80 * 255))
else:
    hue = ImageChops.lighter(band(h, 0, int(0.05 * 255)), band(h, int(0.95 * 255), 255))
stoff = ImageChops.multiply(hue, band(s, 64, 255))
v2 = Image.composite(v.point(lambda x: min(255, round(x * HELL))), v, stoff)
store(bsrc, Image.merge("HSV", (h, s, v2)).convert("RGB"))

msrc, mr = image_of(pbr["metallicRoughnessTexture"])
r, g, b = mr.convert("RGB").split()
st = stoff if stoff.size == mr.size else stoff.resize(mr.size)
g = Image.composite(g.point(lambda x: max(x, round(ROUGH * 255))), g, st)
b = Image.composite(b.point(lambda x: min(x, round(METAL * 255))), b, st)
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
print(f"geschrieben {DST}: Stoff ({FARBE}) {stoff.histogram()[255] / n:.0%}, Helligkeit x {HELL}, "
      f"Metall <= {METAL}, Rauheit >= {ROUGH}")
