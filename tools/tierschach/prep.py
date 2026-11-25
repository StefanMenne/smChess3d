"""Mesh aus image_to_3d vorbereiten: Blick nach -Y drehen und auf ~N Dreiecke reduzieren (vor glb_post).

  blender -b --python schach/tools/prep.py -- in.glb out.glb --yaw 25 [--faces 5000]
  (auf dem GB10: blender-Tool mit code=<diese Datei>, args=[in.glb, out.glb, --yaw, 25])

--yaw in Grad um Z (Blender), so gewählt, dass der Körper gerade nach vorn (-Y) schaut (tools/yawsweep.sh).
"""
import argparse
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
p = argparse.ArgumentParser(prog="prep")
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--yaw", type=float, default=0.0)
p.add_argument("--faces", type=int, default=5000)
p.add_argument("--cut-back", type=float, default=None, help="Vertices hinter diesem y (nach yaw) entfernen")
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in meshes:
    o.parent = None
if len(meshes) > 1:
    bpy.ops.object.join()
m = meshes[0]
for o in list(bpy.context.scene.objects):
    if o != m:
        bpy.data.objects.remove(o)
m.rotation_mode = "XYZ"   # glTF-Import stellt Quaternionen ein, sonst wirkt --yaw nicht
m.rotation_euler = (0, 0, math.radians(a.yaw))
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

# Freischwebende Bruchstücke entfernen: Inseln, die weiter als 2 % der BBox-Diagonale vom Rest entfernt sind
import bmesh
from mathutils.kdtree import KDTree

bm = bmesh.new()
bm.from_mesh(m.data)
# glTF trennt das Mesh an UV-Nähten auf: ohne Verschmelzen hält die Inselsuche Kopf- und Körperstücke für
# Bruchstücke und löscht sie (2026-11-23 bei der neuen Schnecke passiert). UVs liegen je Ecke und bleiben erhalten.
n_before = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
print(f"[prep] Nahtpunkte verschmolzen: {n_before} -> {len(bm.verts)}")
bm.verts.ensure_lookup_table()
seen, islands = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, isl = [v], []
    seen.add(v.index)
    while stack:
        x = stack.pop()
        isl.append(x)
        for e in x.link_edges:
            o = e.other_vert(x)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    islands.append(isl)
islands.sort(key=len, reverse=True)
co = [v.co for v in bm.verts]
diag = (max(c.x for c in co) - min(c.x for c in co)) ** 2 + (max(c.y for c in co) - min(c.y for c in co)) ** 2 \
    + (max(c.z for c in co) - min(c.z for c in co)) ** 2
gap = 0.02 * diag ** 0.5
kept = list(islands[0])
for isl in islands[1:]:
    kd = KDTree(len(kept))
    for i, v in enumerate(kept):
        kd.insert(v.co, i)
    kd.balance()
    d = min(kd.find(v.co)[2] for v in isl)
    if d > gap:
        print(f"[prep] Bruchstück entfernt: {len(isl)} Vertices, Abstand {d:.3f}")
        bmesh.ops.delete(bm, geom=isl, context="VERTS")
    else:
        kept += isl
if a.cut_back is not None:
    # Alles hinter y = cut_back abschneiden (z.B. ein zu langer Schwanz), Schnittkante schließen
    cut = [v for v in bm.verts if v.co.y > a.cut_back]
    bmesh.ops.delete(bm, geom=cut, context="VERTS")
    edges = [e for e in bm.edges if e.is_boundary]
    caps = bmesh.ops.holes_fill(bm, edges=edges, sides=64)["faces"]
    uv = bm.loops.layers.uv.active
    capset = set(caps)
    for f in caps:  # Kappe einfarbig: UV einer angrenzenden Originalfläche
        src = next((l2[uv].uv.copy() for l in f.loops for l2 in l.vert.link_loops if l2.face not in capset), None)
        if src is not None:
            for l in f.loops:
                l[uv].uv = src
    print(f"[prep] hinter y={a.cut_back} abgeschnitten: {len(cut)} Vertices")
bm.to_mesh(m.data)
bm.free()

n0 = len(m.data.polygons)
if n0 > a.faces:
    mod = m.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = a.faces / n0
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.shade_smooth()
print(f"[prep] Dreiecke {n0} -> {len(m.data.polygons)}, yaw {a.yaw}")
bpy.ops.export_scene.gltf(filepath=a.dst, export_format="GLB", use_selection=False)
