"""Dreht einen Turm auf Rädern (aus einem Schrägbild) so, dass er gerade steht: Wände parallel zu den Achsen,
Räder links und rechts (Achsen in x), Mitte auf (0, 0). Vor tools/rig_turm.py.

  blender -b --python tools/ritter/turm_ausrichten.py -- in.glb out.glb [--z 0.3,0.6] [--extra 0]

Der Drehwinkel kommt aus dem kleinsten umschließenden Rechteck des Grundrisses im Höhenband --z (Turmkörper).
Danach liegen die Räder entweder an den x- oder den y-Seiten; liegen sie an den y-Seiten, wird um weitere 90° gedreht.
--extra: zusätzliche Drehung in Grad (z. B. 180, wenn die Schauseite hinten liegt).
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]
o = dict(zip(argv[2::2], argv[3::2]))
Z0, Z1 = (float(v) for v in o.get("--z", "0.3,0.6").split(","))
EXTRA = float(o.get("--extra", 0))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
m = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"][0]
bpy.context.view_layer.objects.active = m
m.select_set(True)
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in m.data.vertices])
band = co[(co[:, 2] > Z0) & (co[:, 2] < Z1), :2]


def extent(a):
    c, s = math.cos(a), math.sin(a)
    r = band @ np.array([[c, -s], [s, c]])
    return (r[:, 0].max() - r[:, 0].min()) * (r[:, 1].max() - r[:, 1].min())


angs = np.radians(np.arange(0, 90, 0.25))
best = float(angs[np.argmin([extent(a) for a in angs])])


def rotate(a):
    R = Matrix.Rotation(a, 4, "Z")
    for v in m.data.vertices:
        v.co = R @ v.co


rotate(-best)   # Rechteck achsparallel
co = np.array([v.co[:] for v in m.data.vertices])
body = co[(co[:, 2] > Z0) & (co[:, 2] < Z1)]
low = co[co[:, 2] < 0.2]
over_x = max(low[:, 0].max() - body[:, 0].max(), body[:, 0].min() - low[:, 0].min())
over_y = max(low[:, 1].max() - body[:, 1].max(), body[:, 1].min() - low[:, 1].min())
turn = 90.0 if over_y > over_x else 0.0
rotate(math.radians(turn + EXTRA))
co = np.array([v.co[:] for v in m.data.vertices])
cx, cy = (co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2
for v in m.data.vertices:
    v.co.x -= cx
    v.co.y -= cy
co = np.array([v.co[:] for v in m.data.vertices])
body = co[(co[:, 2] > Z0) & (co[:, 2] < Z1)]
print(f"[ausrichten] Grundriss um {math.degrees(best):.2f}° gedreht, dazu {turn + EXTRA:.0f}°; "
      f"Körper |x| <= {np.abs(body[:, 0]).max():.3f}, Räder bis |x| {np.abs(co[co[:, 2] < 0.2, 0]).max():.3f}, "
      f"Tiefe y {co[:, 1].min():.3f}..{co[:, 1].max():.3f}")
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="AUTO", export_yup=True)
