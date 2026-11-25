"""Schnecken-Rig mit Animationen Idle und Walk für den Turm (Neufassung 2026-11-23; das Original ist verloren).

  blender -b --factory-startup --python tools/rig_snail.py -- in.glb out.glb [--landmarks turm|FILE.json]
          [--walk 0.8] [--height 0.78] [--fps 24] [--save-blend x.blend] [--dump-landmarks out.json]
  (GB10: blender-Tool, Datei mitschicken, code = runpy wie in der README)

Eingabe: Ausgabe von eye_geo (Blender: Z oben, Figur blickt nach -Y, Unterkante z = 0), Augen als Objekte "Eye*".
Knochen wie im alten Rig: root -> sole1 (hinten) -> sole2 -> sole3 (vorn) -> neck -> head -> antenna.L/.R,
dazu shell (Haus samt Turm, starr). Anders als das alte Rig skaliert die Kriechwelle keine Knochen: im alten Rig
hing das Haus in der skalierten Sohlenkette und wurde beim Gleiten um bis zu ±14 % mitgestaucht. Hier sind alle
Sohlenabschnitte und das Haus direkte Kinder von root und werden nur verschoben/gedreht.

Landmarken: Anteile der Bounding Box (x 0 = links .. 1 = rechts, y 0 = vorn .. 1 = hinten, z 0 = unten .. 1 = oben).
"""
import argparse
import json
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

LANDMARKS = {
    # gemessen an der weißen Schnecke vom 2026-11-23 (Seitenraster, Frontraster der Augen)
    "turm": {
        "shell_center": [0.5, 0.64, 0.41],   # Haus als Ellipsoid
        "shell_radius": [0.62, 0.335, 0.315],
        "tower_min": [0.25, 0.55, 0.66],     # Turm als Kasten
        "tower_max": [0.83, 0.86, 1.01],
        "head_x": 0.6,                       # Mitte des Kopfes (das Haus steht seitlich über)
        "head_front": 0.33,                  # Kopf/Hals reichen von vorn bis hier (y)
        "neck_z": [0.12, 0.40],              # Hals von .. bis (z); darüber Kopf
        "antenna_z": 0.63,                   # darüber Fühler
        "sole_z": 0.05,
        "sole_y": [0.97, 0.72, 0.47, 0.22],  # Grenzen sole1 | sole2 | sole3 (hinten -> vorn)
    },
}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
p = argparse.ArgumentParser(prog="rig_snail")
p.add_argument("src", nargs="?")
p.add_argument("dst", nargs="?")
p.add_argument("--landmarks", default="turm", help="Profil aus LANDMARKS oder JSON-Datei")
p.add_argument("--walk", type=float, default=0.8, help="Länge eines Walk-Zyklus in s")
p.add_argument("--height", type=float, default=0.0, help="auf diese Höhe skalieren (0 = unverändert)")
p.add_argument("--fps", type=int, default=24)
p.add_argument("--save-blend", default=None)
p.add_argument("--dump-landmarks", default=None)
a = p.parse_args(argv)

L = LANDMARKS[a.landmarks] if a.landmarks in LANDMARKS else json.load(open(a.landmarks))
if a.dump_landmarks:
    json.dump(L, open(a.dump_landmarks, "w"), indent=2)
    print(f"[rig] Landmarken geschrieben: {a.dump_landmarks}")
    raise SystemExit(0)

# ------------------------------------------------------------------ Import
EYES = ("Eye", "Auge")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH" and not o.name.startswith(EYES)]
eyes = [o for o in scene.objects if o.type == "MESH" and o.name.startswith(EYES)]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes + eyes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in meshes + eyes:
    o.parent = None
if len(meshes) > 1:
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
mesh = meshes[0]
bm = bmesh.new()
bm.from_mesh(mesh.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)  # glTF-Nähte schließen (UVs bleiben je Ecke)
bm.to_mesh(mesh.data)
bm.free()

# auf Höhe skalieren, Unterkante mittig auf z = 0 (Augen mit)
V = np.array([v.co[:] for v in mesh.data.vertices])
mn, mx = V.min(0), V.max(0)
k = a.height / (mx[2] - mn[2]) if a.height > 0 else 1.0
T = Matrix.Scale(k, 4) @ Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))
for o in [mesh] + eyes:
    o.data.transform(T)
    o.data.update()
V = np.array([v.co[:] for v in mesh.data.vertices])
mn, mx = V.min(0), V.max(0)
ext = mx - mn
H = ext[2]
F = (V - mn) / ext  # Anteile


def P(fx, fy, fz):
    """Anteile -> Weltpunkt (y-Anteil 0 = vorn = -Y)."""
    return Vector((mn[0] + fx * ext[0], mn[1] + fy * ext[1], mn[2] + fz * ext[2]))


print(f"[rig] {len(V)} Vertices, Höhe {H:.3f}, Länge {ext[1]:.3f}, Breite {ext[0]:.3f}, Augen-Teile {len(eyes)}")

# ------------------------------------------------------------------ Skelett
arm_data = bpy.data.armatures.new("Rig")
arm = bpy.data.objects.new("Rig", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones
hx = L["head_x"]
sy = L["sole_y"]
sz = L["sole_z"]
nz0, nz1 = L["neck_z"]
az = L["antenna_z"]
hf = L["head_front"]


def bone(name, h, t, parent=None, deform=True):
    b = eb.new(name)
    b.head, b.tail = h, t
    b.roll = 0
    b.use_deform = deform
    if parent:
        b.parent = eb[parent]
    return b


bone("root", P(0.5, 0.5, 0), P(0.5, 0.5, 0.3), deform=False)
for i in range(3):  # hinten -> vorn, zeigen nach vorn (-Y)
    bone(f"sole{i + 1}", P(hx, sy[i], sz), P(hx, sy[i + 1], sz), "root")
c = L["shell_center"]
bone("shell", P(c[0], c[1], c[2]), P(c[0], c[1], min(c[2] + 0.3, 1.0)), "root")
bone("neck", P(hx, 0.17, nz0), P(hx, 0.15, nz1), "sole3")
bone("head", P(hx, 0.15, nz1), P(hx, 0.15, az), "neck")
# Fühler: Mitte der Punkte oberhalb antenna_z je Seite
fr = (F[:, 1] < hf) & (F[:, 2] > az)
for side, sel in (("L", F[:, 0] > hx), ("R", F[:, 0] <= hx)):
    pts = F[fr & sel]
    if len(pts) == 0:
        continue
    base = pts[pts[:, 2] < az + 0.05].mean(0) if (pts[:, 2] < az + 0.05).any() else pts.mean(0)
    tip = pts[pts[:, 2] > pts[:, 2].max() - 0.05].mean(0)
    bone(f"antenna.{side}", P(base[0], base[1], az), P(tip[0], tip[1], tip[2]), "head")
bpy.ops.object.mode_set(mode="OBJECT")
names = [b.name for b in arm_data.bones]
print(f"[rig] Knochen: {names}")

# ------------------------------------------------------------------ Gewichte


def smooth(x, a0, a1):
    t = np.clip((x - a0) / (a1 - a0), 0, 1)
    return t * t * (3 - 2 * t)


fx, fy, fz = F[:, 0], F[:, 1], F[:, 2]
# Haus: Ellipsoid (weicher Rand) oder Turm-Kasten -> starr
r = np.array(L["shell_radius"])
d = np.sqrt((((F - np.array(c)) / r) ** 2).sum(1))
w_shell = 1 - smooth(d, 0.94, 1.04)
tmin, tmax = np.array(L["tower_min"]), np.array(L["tower_max"])
in_tower = np.all((F >= tmin) & (F <= tmax), axis=1)
w_shell = np.maximum(w_shell, in_tower.astype(float))
# die Sohle unter dem Haus gehört nicht zum Haus
w_shell *= smooth(fz, 0.06, 0.12)
rest = 1 - w_shell
# vorn: Hals / Kopf / Fühler
front = 1 - smooth(fy, hf - 0.04, hf + 0.04)
w_ant = front * smooth(fz, az - 0.02, az + 0.03)
w_head = front * smooth(fz, nz1 - 0.05, nz1 + 0.04) * (1 - w_ant / np.maximum(front, 1e-6))
w_neck = front * smooth(fz, nz0 - 0.04, nz0 + 0.06) * (1 - smooth(fz, nz1 - 0.05, nz1 + 0.04))
w_body = np.clip(1 - w_ant - w_head - w_neck, 0, 1)
# Sohle: Dreieck-Kerne um die Mitten der drei Abschnitte (hinten -> vorn)
cent = [(sy[i] + sy[i + 1]) / 2 for i in range(3)]
span = (sy[0] - sy[3]) / 3
ks = np.stack([np.clip(1 - np.abs(fy - cy) / span, 0, 1) for cy in cent], 1)
ks[fy >= cent[0], 0] = 1  # ganz hinten: sole1
ks[fy <= cent[2], 2] = 1  # ganz vorn: sole3
ks /= ks.sum(1, keepdims=True)

W = {
    "shell": w_shell,
    "neck": rest * w_neck,
    "head": rest * w_head,
    "sole1": rest * w_body * ks[:, 0],
    "sole2": rest * w_body * ks[:, 1],
    "sole3": rest * w_body * ks[:, 2],
}
for side, sel in (("L", fx > hx), ("R", fx <= hx)):
    if f"antenna.{side}" in names:
        W[f"antenna.{side}"] = rest * w_ant * sel
    else:
        W["head"] = W["head"] + rest * w_ant * sel
tot = sum(W.values())
for n in W:
    W[n] = W[n] / np.maximum(tot, 1e-6)
mesh.parent = arm
mod = mesh.modifiers.new("Armature", "ARMATURE")
mod.object = arm
for n, w in W.items():
    g = mesh.vertex_groups.new(name=n)
    for i in np.nonzero(w > 1e-3)[0]:
        g.add([int(i)], float(w[i]), "REPLACE")
    print(f"[rig] {n}: {int((w > 0.5).sum())} Vertices überwiegend")

# Augen starr an den Kopf
if eyes:
    for o in eyes:
        o.vertex_groups.new(name="head").add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    for o in eyes:
        o.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    print(f"[rig] Augen am Kopf: {len(eyes)} Teile")

# ------------------------------------------------------------------ Animationen
scene.render.fps = a.fps
pb = arm.pose.bones
for b in pb:
    b.rotation_mode = "XYZ"
# Knochenachsen: Sohle zeigt nach vorn -> lokale Y = vorwärts, lokale Z = oben; Hals/Kopf/Haus zeigen nach oben ->
# lokale X = seitlich (Nicken um X), lokale Y = oben (Drehen um Y)
LEN = ext[1]


def new_action(name, frames):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    act.frame_range = (0, frames)
    act.use_frame_range = True
    act.use_cyclic = True
    return act


def key(f, **bones):
    """bones: name=(loc_vorwärts, loc_oben, nicken°, drehen°, kippen°)"""
    for n, (fwd, up, pitch, yaw, roll) in bones.items():
        if n not in pb:
            continue
        b = pb[n]
        # Verschiebung in Weltrichtungen (vorn = -Y, oben = +Z) in die Ruhe-Achsen des Knochens umrechnen
        b.location = b.bone.matrix_local.to_3x3().inverted() @ Vector((0, -fwd, up))
        b.rotation_euler = (math.radians(pitch), math.radians(yaw), math.radians(roll))
        b.keyframe_insert("location", frame=f)
        b.keyframe_insert("rotation_euler", frame=f)


ZERO = (0, 0, 0, 0, 0)
ALL = ["sole1", "sole2", "sole3", "shell", "neck", "head", "antenna.L", "antenna.R"]

# Idle (4 s): Sohle atmet, Haus wiegt, Kopf schaut sich um, Fühler pendeln
FI = 4 * a.fps
act_idle = new_action("Idle", FI)
n = 24
for i in range(n + 1):
    t = i / n
    ph = 2 * math.pi * t
    breathe = 0.006 * H * math.sin(2 * ph)
    look = 10 * math.sin(ph) * (0.5 + 0.5 * math.sin(ph + 0.6))  # schaut nach links, dann rechts, ruht dazwischen
    key(round(FI * t),
        sole1=(0, breathe * 0.5, 0, 0, 0), sole2=(0, breathe, 0, 0, 0), sole3=(0, breathe * 0.5, 0, 0, 0),
        shell=(0, breathe, 1.0 * math.sin(2 * ph), 0, 0.8 * math.sin(ph)),
        neck=(0, 0, 2 * math.sin(2 * ph + 1), look, 0),
        head=(0, 0, 1.5 * math.sin(2 * ph), 0.5 * look, 2 * math.sin(ph + 1.2)),
        **{"antenna.L": (0, 0, 10 * math.sin(2 * ph + 0.3), 0, 6 * math.sin(ph + 0.8)),
           "antenna.R": (0, 0, 10 * math.sin(2 * ph + 1.3), 0, -6 * math.sin(ph + 1.8))})

# Walk: Kriechwelle von hinten nach vorn durch die Sohle; jeder Abschnitt schiebt sich vor, hebt sich leicht
FW = max(8, round(a.walk * a.fps))
act_walk = new_action("Walk", FW)
n = 16
A = 0.035 * LEN   # Vor/Zurück je Abschnitt
B = 0.012 * H     # Anheben in der Vorwärtsphase
for i in range(n + 1):
    t = i / n
    ph = 2 * math.pi * t
    seg = {}
    for j in range(3):  # Welle läuft nach vorn: vordere Abschnitte später
        q = ph - j * 2 * math.pi / 3
        seg[f"sole{j + 1}"] = (A * math.sin(q), B * max(0.0, math.cos(q)), 0, 0, 0)
    q3 = ph - 2 * 2 * math.pi / 3
    key(round(FW * t), **seg,
        shell=(0.4 * A * math.sin(ph - 2.1), 0.5 * B * (1 + math.sin(2 * ph)), 2.0 * math.sin(ph), 0, 1.5 * math.sin(ph + 1.6)),
        neck=(0, 0, 4 * math.sin(q3 + 0.5), 1.5 * math.sin(ph), 0),
        head=(0, 0, 3 * math.sin(q3 + 1.2), 2 * math.sin(ph + 0.5), 1.5 * math.sin(ph)),
        **{"antenna.L": (0, 0, 12 * math.sin(q3 + 1.8), 0, 5 * math.sin(ph + 1)),
           "antenna.R": (0, 0, 12 * math.sin(q3 + 2.3), 0, -5 * math.sin(ph + 1.4))})

for act in (act_idle, act_walk):
    for fc in getattr(act, "fcurves", []):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

# Ruhepose ohne aktive Aktion
arm.animation_data.action = None
for b in pb:
    b.location, b.rotation_euler, b.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
scene.frame_start, scene.frame_end = 0, FI

if a.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=a.dst,
    export_format="GLB",
    export_image_format="JPEG",
    export_image_quality=90,
    export_yup=True,
    export_skins=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_range=False,
)
print(f"[rig] OUT {a.dst}  Animationen: {[x.name for x in bpy.data.actions]}  Walk {FW} Frames, Idle {FI} Frames")
