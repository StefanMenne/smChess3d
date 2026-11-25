"""Riggt eine geschnitzte Figur: Skelett aus einem Profil, automatische Gewichte, starre Requisiten.

  blender -b --python tools/rig_figur.py -- figure.glb out.glb profile=figure.json

- profile: JSON mit den Knochenpositionen als Anteile der Bounding Box ("bones_center", "bones_side": Name ->
  [head, tail]), dem Saum der Tunika ("leg_top", "belly": Anteile der Höhe, darüber blenden die Oberschenkel aus) und
  optionalen starren Requisiten ("props": [{"a": [x,y,z/H], "b": [x,y,z/H], "radius": r, "bone": "ForeArm.R"}],
  Positionen in Modelleinheiten, z als Anteil der Höhe): ihre Vertices folgen starr der Hand, Flächen zum Rest werden
  getrennt. Weitere Schlüssel: "prop_cut_max", "to_hips" (siehe unten).

Ergebnis: GLB mit Skelett (Hips, Spine, Chest, Neck, Head, Shoulder/Arm/ForeArm/Hand, UpLeg/Leg/Foot/Toe je .L/.R),
ohne Animationen. Die Bewegungen erzeugt danach tools/anim_figur.py (Idle, WalkInPlace, Schrittlänge).
"""
import json
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC, DST = argv[0], argv[1]
PROFILE = None
for a in argv[2:]:
    k, v = a.split("=", 1)
    if k == "profile":
        PROFILE = json.load(open(v))
    else:
        sys.exit(f"unbekanntes Argument {a}")

# ------------------------------------------------------------------ mesh
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
mesh = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh.parent = None
bm = bmesh.new()
bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.to_mesh(mesh.data)
bm.free()
V = np.array([v.co[:] for v in mesh.data.vertices])
mn, mx = V.min(0), V.max(0)
half, ctr, H = (mx - mn) / 2, (mn + mx) / 2, mx[2] - mn[2]
print(f"[rt] height {H:.3f}")


def P(f, sx=1):
    return Vector((ctr[0] + sx * f[0] * half[0], ctr[1] + f[1] * half[1], mn[2] + f[2] * H))


# rigid props (spear, staff, sword): vertices near the axis follow the hand; faces to the rest of the figure are cut
PROPS = PROFILE.get("props", []) if PROFILE else [
    {"a": [-0.131, 0.0, 0.07], "b": [-0.150, -0.168, 0.88], "radius": 0.022, "bone": "ForeArm.R", "low_x": -0.112}]
spear, prop_bone = [], {}
for pr in PROPS:
    A = np.array([pr["a"][0], pr["a"][1], pr["a"][2] * H])
    Bp = np.array([pr["b"][0], pr["b"][1], pr["b"][2] * H])
    for v in mesh.data.vertices:
        c = np.array(v.co[:])
        t = (c[2] - A[2]) / (Bp[2] - A[2])
        q = A + t * (Bp - A)
        near = pr.get("t_min", -0.12) < t < 1.25 and math.hypot(c[0] - q[0], c[1] - q[1]) < pr["radius"]
        low = "low_x" in pr and c[2] < 0.12 * H and c[0] < pr["low_x"]
        if near or low:
            spear.append(v.index)
            prop_bone[v.index] = pr["bone"]
ss = set(spear)
bm = bmesh.new()
bm.from_mesh(mesh.data)
# profile "prop_cut_max" (fraction of the height, default 0.30): faces between prop and figure are cut below it
CUT_MAX = PROFILE.get("prop_cut_max", 0.30) if PROFILE else 0.30
cut = [f for f in bm.faces if any(v.index in ss for v in f.verts) and not all(v.index in ss for v in f.verts)
       and max(v.co.z for v in f.verts) < CUT_MAX * H]
bmesh.ops.delete(bm, geom=cut, context="FACES_ONLY")
bm.to_mesh(mesh.data)
bm.free()
print(f"[rt] prop vertices {len(spear)}, faces cut {len(cut)}")

# ------------------------------------------------------------------ armature (fractions of the bounding box)
BONES_C = [
    ("Hips", (0, 0.40, 0.30), (0, 0.35, 0.42), None),
    ("Spine", (0, 0.35, 0.42), (0, 0.30, 0.54), "Hips"),
    ("Chest", (0, 0.30, 0.54), (0, 0.27, 0.64), "Spine"),
    ("Neck", (0, 0.27, 0.64), (0, 0.25, 0.69), "Chest"),
    ("Head", (0, 0.25, 0.69), (0, 0.25, 0.98), "Neck"),
]
BONES_S = [  # left side (+x), mirrored for the right
    ("Shoulder", (0.15, 0.25, 0.62), (0.55, 0.25, 0.62), "Chest"),
    ("Arm", (0.55, 0.25, 0.62), (0.75, 0.15, 0.50), "Shoulder"),
    ("ForeArm", (0.75, 0.15, 0.50), (0.82, -0.35, 0.48), "Arm"),
    ("Hand", (0.82, -0.35, 0.48), (0.84, -0.60, 0.47), "ForeArm"),
    ("UpLeg", (0.30, 0.50, 0.33), (0.30, 0.42, 0.20), "Hips"),
    ("Leg", (0.30, 0.42, 0.20), (0.30, 0.52, 0.07), "UpLeg"),
    ("Foot", (0.30, 0.52, 0.07), (0.30, 0.10, 0.02), "Leg"),
    ("Toe", (0.30, 0.10, 0.02), (0.30, -0.12, 0.01), "Foot"),
]
if PROFILE:
    BC = {b[0]: b for b in BONES_C}
    BS = {b[0]: b for b in BONES_S}
    BONES_C = [(n, *PROFILE["bones_center"].get(n, BC[n][1:3]), BC[n][3]) for n in BC]
    BONES_S = [(n, *PROFILE["bones_side"].get(n, BS[n][1:3]), BS[n][3]) for n in BS]
SPEC = []
for n, h, t, par in BONES_C:
    SPEC.append((n, P(h), P(t), par))
for side, sx in (("L", 1), ("R", -1)):
    for n, h, t, par in BONES_S:
        p = par if par in ("Hips", "Chest") else f"{par}.{side}"
        SPEC.append((f"{n}.{side}", P(h, sx), P(t, sx), p))
NAMES = [s[0] for s in SPEC]

ad = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", ad)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for n, h, t, par in SPEC:
    b = ad.edit_bones.new(n)
    b.head, b.tail, b.roll = h, t, 0
    if par:
        b.parent = ad.edit_bones[par]
bpy.ops.object.mode_set(mode="OBJECT")

# ------------------------------------------------------------------ skinning
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
vg = mesh.vertex_groups
# Bone heat can fail silently (e.g. after cutting a prop loose) and leave vertices without any weight: give those
# weights from the two nearest bone segments (inverse distance), so the figure still moves
_ss = set(spear)
_unw = [v for v in mesh.data.vertices if v.index not in _ss and not any(g.weight > 0 for g in v.groups)]
if _unw:
    _segs = [(b.name, np.array(rig.matrix_world @ b.head_local), np.array(rig.matrix_world @ b.tail_local))
             for b in rig.data.bones if b.use_deform and b.name in vg]
    for v in _unw:
        p = np.array(mesh.matrix_world @ v.co)
        ds = []
        for name, h, t in _segs:
            d = t - h
            u = float(np.clip(np.dot(p - h, d) / max(np.dot(d, d), 1e-12), 0, 1))
            ds.append((float(np.linalg.norm(p - (h + u * d))), name))
        ds.sort()
        w = [1 / max(d, 1e-4) ** 4 for d, _ in ds[:2]]
        for (d, name), wi in zip(ds[:2], w):
            vg[name].add([v.index], wi / sum(w), "REPLACE")
    print(f"[rt] bone heat left {len(_unw)} vertices without weights: nearest-bone weights assigned")
used = {g.group for v in mesh.data.vertices for g in v.groups if g.weight > 0}
print("[rt] bones without weights:", [g.name for g in vg if g.index not in used])
z_body = mn[2] + (PROFILE or {}).get("leg_top", 0.33) * H
z_belly = mn[2] + (PROFILE or {}).get("belly", 0.26) * H
for side in ("L", "R"):
    gl = vg[f"UpLeg.{side}"]
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == gl.index and g.weight > 0:
                k = float(np.clip((z_body - v.co.z) / (z_body - z_belly), 0, 1))
                moved = g.weight * (1 - k)
                if moved > 0:
                    g.weight -= moved
                    vg["Hips"].add([v.index], moved, "ADD")
for g in list(vg):
    g.remove(spear)
# Bereiche, die nur dem Becken folgen (z. B. ein Umhang hinter den Beinen, der sonst mit den Beinen abknickt):
# "to_hips": [{"zmax": Anteil der Höhe, "ymin": y-Mindestwert (hinten = +y)}]
for box in (PROFILE or {}).get("to_hips", []):
    sel = [v.index for v in mesh.data.vertices if v.co.z < mn[2] + box["zmax"] * H and v.co.y > box["ymin"]]
    for g in list(vg):
        g.remove(sel)
    vg["Hips"].add(sel, 1.0, "REPLACE")
    print(f"[rt] to_hips: {len(sel)} vertices follow the hips only")
for vi in spear:
    vg[prop_bone[vi]].add([vi], 0.5, "REPLACE")
    vg["Chest"].add([vi], 0.5, "REPLACE")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="JPEG", export_image_quality=90,
                          export_yup=True, export_skins=True, export_animations=False)
print(f"[rt] OUT {DST}  bones {len(rig.data.bones)}")
