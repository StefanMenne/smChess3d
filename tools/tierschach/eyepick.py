"""Augenpositionen für tex_eyes --eyes von Hand bestimmen (BBox-Anteile x, Höhe, Vorne).

  blender -b --python schach/tools/eyepick.py -- prep.glb grid.png
      Frontansicht (Blick von -Y), orthografisch genau auf die BBox, mit Raster in Anteilen (alle 0.05)
  blender -b --python schach/tools/eyepick.py -- prep.glb - --pick "0.30,0.60;0.72,0.60"
      Raycast von vorn an (x-Anteil, Höhen-Anteil) -> gibt "x,h,v;x,h,v" mit Vorne-Anteil (1 = ganz vorn) aus
"""
import argparse
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
p = argparse.ArgumentParser(prog="eyepick")
p.add_argument("src")
p.add_argument("out")
p.add_argument("--pick", default=None)
p.add_argument("--size", type=int, default=900)
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
sc = bpy.context.scene
objs = [o for o in sc.objects if o.type == "MESH"]
pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
mn = Vector([min(q[i] for q in pts) for i in range(3)])
mx = Vector([max(q[i] for q in pts) for i in range(3)])
ext = mx - mn

if a.pick:
    dg = bpy.context.evaluated_depsgraph_get()
    res = []
    for pair in a.pick.split(";"):
        fx, fh = (float(t) for t in pair.split(","))
        o = Vector((mn.x + fx * ext.x, mn.y - 1.0, mn.z + fh * ext.z))
        hit, loc, *_ = sc.ray_cast(dg, o, Vector((0, 1, 0)))
        fv = (mx.y - loc.y) / ext.y if hit else 0.85
        res.append(f"{fx:.3f},{fh:.3f},{fv:.3f}")
    print("[eyepick] --eyes " + ";".join(res))
    sys.exit(0)

w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.8, 0.85, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
side = max(ext.x, ext.z)
cam.data.ortho_scale = side
cam.location = ((mn.x + mx.x) / 2, mn.y - 5, (mn.z + mx.z) / 2)
cam.rotation_euler = (1.5708, 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = a.size
sc.view_settings.view_transform = "Standard"
sc.render.filepath = a.out
bpy.ops.render.render(write_still=True)

# Raster in BBox-Anteilen einzeichnen (Bildmitte = BBox-Mitte, Kantenlänge = side)
import numpy as np

img = bpy.data.images.load(a.out)
S = a.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(S, S, 4)
for k in range(21):
    f = k / 20
    col = (1, 0, 0, 1) if k % 2 == 0 else (0.2, 0.2, 1, 1)
    x = int(S / 2 + (mn.x + f * ext.x - (mn.x + mx.x) / 2) / side * S)
    z = int(S / 2 + (mn.z + f * ext.z - (mn.z + mx.z) / 2) / side * S)  # Pixelzeile von unten
    if 0 <= x < S:
        px[:, x] = col
    if 0 <= z < S:
        px[z, :] = col
img.pixels = px.ravel()
img.filepath_raw = a.out
img.save()
print(f"[eyepick] Raster: rote Linien = 0.0, 0.1, ... 1.0; blaue = 0.05, 0.15, ...  -> {a.out}")
