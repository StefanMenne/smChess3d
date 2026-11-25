"""Glättet einen Bereich einer Figur (Form und Textur), z. B. die erfundene Rückseite eines Helms.

  (Blender) smooth_region.py in.glb out.glb --zmin 0.80 [--ymin -0.01] [--xmin -0.11] [--iter 30]
                             [--blur 10] [--preview before_after.png]

Bereich: Vertices mit z > zmin * Höhe und y > ymin (Blender: vorn = -Y, also hinten = +Y) und x > xmin (Speer
ausnehmen). Zum Rand hin wird die Wirkung weich ausgeblendet (über 0.05 der Höhe).
- Form: Laplace-Glättung (Furchen und Strähnen verschwinden, die Kuppelform bleibt)
- Textur: die UV-Flächen des Bereichs werden in der Farbtextur weichgezeichnet (keine gemalten Strähnen mehr)
"""
import argparse
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFilter

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--zmin", type=float, default=0.80)
p.add_argument("--ymin", type=float, default=-0.01)
p.add_argument("--xmin", type=float, default=-0.11)
p.add_argument("--iter", type=int, default=30)
p.add_argument("--blur", type=float, default=10)
p.add_argument("--preview", default=None)
a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])


def render_back(path):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 480, 480
    if not sc.world:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.5, 0.52, 0.55)
    cam = bpy.data.objects.get("pcam") or bpy.data.objects.new("pcam", bpy.data.cameras.new("pcam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
        for loc, e in (((1.5, 2.5, 2.5), 700), ((-2, 1.5, 1.5), 300), ((0, -2, 2), 200)):
            L = bpy.data.objects.new("pl", bpy.data.lights.new("pl", "POINT"))
            L.data.energy = e
            L.location = loc
            sc.collection.objects.link(L)
    sc.camera = cam
    imgs = []
    for cpos in ((0.9, 1.1, 1.35), (-0.6, 1.3, 1.25)):
        cam.location = cpos
        cam.rotation_euler = (Vector((0, 0.02, H * 0.86)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 85
        sc.render.filepath = f"/tmp/sr_{len(imgs)}.png"
        bpy.ops.render.render(write_still=True)
        imgs.append(Image.open(sc.render.filepath).convert("RGB"))
    return imgs


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
# in Weltkoordinaten arbeiten (glTF-Import: Y-oben-Drehung am Objekt) und Nahtpunkte verschmelzen, damit die
# Glättung an UV-Kanten nicht aufreißt (UVs bleiben pro Ecke erhalten)
bpy.ops.object.select_all(action="DESELECT")
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
ob.parent = None
_bm = bmesh.new()
_bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(_bm, verts=_bm.verts, dist=1e-5)
_bm.to_mesh(ob.data)
_bm.free()
me = ob.data
co = np.array([v.co[:] for v in me.vertices])
H = co[:, 2].max()
before = render_back(None) if a.preview else None

# Gewicht je Vertex: 1 im Bereich, weich ausgeblendet zum unteren Rand und zur Seite
fade = 0.05 * H
wz = np.clip((co[:, 2] - a.zmin * H) / fade, 0, 1)
wy = np.clip((co[:, 1] - a.ymin) / (0.03), 0, 1)
wx = np.clip((co[:, 0] - a.xmin) / 0.01, 0, 1)
w = wz * wy * wx
sel = np.where(w > 0)[0]
print(f"[smooth] height {H:.3f}, region vertices {len(sel)} of {len(co)}")

# Form: Laplace-Glättung, gewichtet
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
orig = co.copy()
for _ in range(a.iter):
    cur = np.array([v.co[:] for v in bm.verts])
    new = cur.copy()
    for i in sel:
        v = bm.verts[i]
        nb = [e.other_vert(v).index for e in v.link_edges]
        if nb:
            new[i] = cur[i] + 0.5 * w[i] * (cur[nb].mean(0) - cur[i])
    for i in sel:
        bm.verts[i].co = new[i]
# Volumen erhalten: Laplace schrumpft; entlang der Normalen etwas zurückschieben
cur = np.array([v.co[:] for v in bm.verts])
bm.normal_update()
for i in sel:
    v = bm.verts[i]
    shrink = (orig[i] - cur[i]) @ np.array(v.normal[:])
    v.co = Vector(cur[i] + 0.8 * shrink * np.array(v.normal[:]))
bm.to_mesh(me)
me.update()

# Textur: UV-Flächen des Bereichs weichzeichnen
mat = ob.active_material
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
img = bsdf.inputs["Base Color"].links[0].from_node.image
W, Hh = img.size
px = np.empty(W * Hh * 4, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(Hh, W, 4)
uv = me.uv_layers.active.data
mask = Image.new("L", (W, Hh), 0)
dr = ImageDraw.Draw(mask)
wset = set(sel.tolist())
for poly in me.polygons:
    vs = list(poly.vertices)
    if not all(v in wset for v in vs):
        continue
    ww = float(np.mean(w[vs]))
    pts = [(uv[li].uv[0] * W, uv[li].uv[1] * Hh) for li in poly.loop_indices]
    dr.polygon(pts, fill=int(255 * ww))
inside = np.asarray(mask).astype(np.float32) / 255 > 0.02          # nur echte Texel des Bereichs
m = np.asarray(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)[..., None] / 255


def gblur(arr):
    from scipy.ndimage import gaussian_filter
    return np.stack([gaussian_filter(arr[..., c], a.blur) for c in range(arr.shape[-1])], -1)


# normierte Weichzeichnung: nur Texel innerhalb des Bereichs mitteln, kein Hintergrund der Textur blutet ein
src = np.clip(px[..., :3], 0, 1) * inside[..., None]
num = gblur(src.astype(np.float32))
den = gblur(inside[..., None].astype(np.float32))[..., :1]
blurred = np.where(den > 1e-3, num / np.maximum(den, 1e-3), px[..., :3])
# Patina (gebackene Rillen) zusätzlich aufhellen: der Helm ist jetzt glatt, Mittelwert des Bereichs als Untergrenze
mean = src[inside].mean(0) if inside.any() else np.zeros(3)
blurred = np.maximum(blurred, 0.85 * mean)
px[..., :3] = px[..., :3] * (1 - m) + blurred * m
img.pixels.foreach_set(px.ravel())
img.update()
print(f"[smooth] texture {W}x{Hh}, masked {float((m > 0.5).mean()) * 100:.2f} % of the texture")

if a.preview:
    after = render_back(None)
    out = Image.new("RGB", (480 * 2, 480 * 2), "white")
    for i, im in enumerate(before):
        out.paste(im, (480 * i, 0))
    for i, im in enumerate(after):
        out.paste(im, (480 * i, 480))
    out.save(a.preview)

for o in list(bpy.context.scene.objects):
    if o.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=a.dst, export_format="GLB", export_image_format="JPEG",
                          export_image_quality=92, export_yup=True)
print(f"[smooth] OUT {a.dst}")
