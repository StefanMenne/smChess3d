"""Gesichter-Nahaufnahmen mehrerer GLBs (mit Augen-Objekten "Eye*") in ein Kontaktblatt, ein Blender-Prozess.

  blender -b --python schach/tools/faces.py -- out.png a.glb b.glb ... [--size 300]
Kamera schaut von vorn (-Y) auf die Mitte der Augen, Ausschnitt = 4x Augenabstand.
"""
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
S = 300
if "--size" in argv:
    i = argv.index("--size")
    S = int(argv[i + 1])
    del argv[i:i + 2]
out, files = argv[0], argv[1:]
tmp = tempfile.mkdtemp()
shots = []
for k, f in enumerate(files):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    sc = bpy.context.scene
    eyes = [o for o in sc.objects if o.type == "MESH" and o.name.startswith("Eye") and "white" in o.name]
    cs = []
    for o in eyes:
        P = [o.matrix_world @ v.co for v in o.data.vertices]
        cs.append(sum(P, Vector()) / len(P))
    c = sum(cs, Vector()) / len(cs)
    d = max((cs[0] - cs[1]).length, 0.05)
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.8, 0.85, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(20))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 4 * d
    cam.location = c + Vector((0, -2, 0))
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = S
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = os.path.join(tmp, f"{k}.png")
    bpy.ops.render.render(write_still=True)
    shots.append(sc.render.filepath)

cols = min(6, len(shots))
rows = math.ceil(len(shots) / cols)
buf = np.ones((S * rows, S * cols, 4), dtype=np.float32)
for i, fp in enumerate(shots):
    im = bpy.data.images.load(fp)
    px = np.array(im.pixels[:], dtype=np.float32).reshape(S, S, 4)
    r, cidx = divmod(i, cols)
    y0 = (rows - 1 - r) * S
    buf[y0:y0 + S, cidx * S:(cidx + 1) * S] = px
img = bpy.data.images.new("sheet", S * cols, S * rows)
img.pixels = buf.ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print(f"[faces] {len(shots)} -> {out}")
