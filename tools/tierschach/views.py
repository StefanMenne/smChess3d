"""Mehrere Ansichten eines GLB in ein PNG (EEVEE), zum Prüfen von Form und Blickrichtung.

  ~/blender/bin/blender -b --factory-startup --python schach/tools/views.py -- in.glb out.png [--yaw 0] [--size 400]
                        [--action Walk --frames 0,6,12]

Ansichten: vorn (-Y), rechts, hinten, links, oben (Blender Z-up; glTF wird beim Import Z-up).
--yaw dreht die Figur vorher um Z (Grad). Mit --action werden statt der Ansichten Frames der Aktion
von vorn-schräg und von der Seite gerendert.
"""
import argparse
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser(prog="views")
p.add_argument("src")
p.add_argument("out")
p.add_argument("--yaw", type=float, default=0.0)
p.add_argument("--size", type=int, default=400)
p.add_argument("--action", default=None)
p.add_argument("--frames", default="0,6,12")
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
sc = bpy.context.scene
objs = [o for o in sc.objects if o.type == "MESH" and o.name != "Cube"]
for o in sc.objects:
    if o.name == "Cube":
        bpy.data.objects.remove(o)
roots = [o for o in sc.objects if o.parent is None]
for r in roots:
    r.rotation_mode = "XYZ"
    r.rotation_euler.z += math.radians(a.yaw)
bpy.context.view_layer.update()


def bbox():
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        oe = o.evaluated_get(dg)
        m = oe.to_mesh()
        pts += [oe.matrix_world @ v.co for v in m.vertices]
        oe.to_mesh_clear()
    mn = Vector([min(q[i] for q in pts) for i in range(3)])
    mx = Vector([max(q[i] for q in pts) for i in range(3)])
    return mn, mx


mn, mx = bbox()
c = (mn + mx) / 2
r = (mx - mn).length / 2
print(f"[views] bbox min {tuple(round(v, 3) for v in mn)} max {tuple(round(v, 3) for v in mx)}")

w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.87, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))
sc.collection.objects.link(sun)
# Boden für die Bodenhöhe
bpy.ops.mesh.primitive_plane_add(size=r * 8, location=(c.x, c.y, mn.z))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = r * 2.3
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = sc.render.resolution_y = a.size
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"


def look(direction, up=Vector((0, 0, 1))):
    d = Vector(direction).normalized()
    cam.location = c - d * r * 4
    cam.rotation_euler = d.to_track_quat("-Z", "Y" if abs(d.z) < 0.99 else "Y").to_euler()


import os
import tempfile

tmp = tempfile.mkdtemp()
shots = []
if a.action:
    act = bpy.data.actions.get(a.action)
    for o in sc.objects:
        if o.animation_data:
            o.animation_data.action = act
    for f in [int(x) for x in a.frames.split(",")]:
        for d in [(0.6, 1, -0.25), (1, 0, 0)]:
            sc.frame_set(f)
            look(d)
            shots.append((f"{a.action} {f}", d))
else:
    shots = [("vorn", (0, 1, 0)), ("rechts", (-1, 0, 0)), ("hinten", (0, -1, 0)), ("links", (1, 0, 0)),
             ("oben", (0, 0.01, -1))]

files = []
for i, (name, d) in enumerate(shots):
    if a.action:
        sc.frame_set(int(name.split()[-1]))
    look(d)
    fp = os.path.join(tmp, f"{i}.png")
    sc.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    files.append(fp)

imgs = [bpy.data.images.load(f) for f in files]
n = len(imgs)
cols = 6 if a.action else n
rows = math.ceil(n / cols)
S = a.size
out = bpy.data.images.new("sheet", S * cols, S * rows)
import numpy as np

buf = np.ones((S * rows, S * cols, 4), dtype=np.float32)
for i, im in enumerate(imgs):
    px = np.array(im.pixels[:], dtype=np.float32).reshape(S, S, 4)
    row, col = divmod(i, cols)
    y0 = (rows - 1 - row) * S
    buf[y0:y0 + S, col * S:(col + 1) * S] = px
out.pixels = buf.ravel()
out.filepath_raw = a.out
out.file_format = "PNG"
out.save()
print(f"[views] -> {a.out}")
