"""Zieht eine breit auf dem Boden liegende Schleppe an das Gewand heran (vor dem Riggen).

  blender -b --python tools/ritter/saum_einziehen.py -- in.glb out.glb [--rx 0.28] [--front 0.16] [--back 0.21]
          [--cy 0.0] [--z0 0.08] [--z1 0.13] [--keep 0.15]

Waagerechter Abstand von der Mitte als Ellipse gemessen (Halbachse --rx in x, --front nach vorn (-y), --back nach
hinten (+y), Mitte bei y = --cy; Modelleinheiten). Was unterhalb von --z0 außerhalb der Ellipse liegt, rückt
heran: vom Überstand bleibt der Anteil --keep. Zwischen --z0 und --z1 wird die Wirkung linear ausgeblendet.
Mesh-Verbindungen, UVs und Textur bleiben unverändert, der Pelzsaum legt sich enger ums Gewand.
"""
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]
o = dict(zip(argv[2::2], argv[3::2]))
RX, FR, BK, CY = float(o.get("--rx", 0.28)), float(o.get("--front", 0.16)), float(o.get("--back", 0.21)), float(o.get("--cy", 0.0))
Z0, Z1, KEEP = float(o.get("--z0", 0.08)), float(o.get("--z1", 0.13)), float(o.get("--keep", 0.15))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
m = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"][0]
M, Mi = m.matrix_world, m.matrix_world.inverted()
moved, far = 0, 0.0
for v in m.data.vertices:
    p = M @ v.co
    if p.z >= Z1:
        continue
    w = 1.0 if p.z <= Z0 else (Z1 - p.z) / (Z1 - Z0)
    dy = p.y - CY
    ry = BK if dy > 0 else FR
    rho = math.hypot(p.x / RX, dy / ry)
    if rho <= 1.0:
        continue
    rho2 = 1.0 + (rho - 1.0) * KEEP
    s = 1.0 + w * (rho2 / rho - 1.0)
    far = max(far, rho)
    p.x *= s
    p.y = CY + dy * s
    v.co = Mi @ p
    moved += 1
print(f"[saum] {moved} Punkte herangezogen, größter Überstand vorher {far:.2f} x Ellipse")
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="AUTO", export_yup=True)
