"""Rig the rook (a round tower on a four-wheeled cart) and write its animations by hand.

  rig_turm.py in.glb out.glb

Input: glb_post output (bottom at z=0, front = -Y, the drawbar points to the front). The wheels are found as the
vertices outside the chassis (|x| > WHEEL_X) below the wheel top; they are split into four by side and axle.

Bones: Hips (root at the ground centre, carries the root motion of "Walk"), Tip (pivot on the ground at the right
wheels, for falling over), Body (rocking and shaking), Wheel.FL/FR/BL/BR (spin about the axle).
Actions (30 fps): Idle, Walk (root motion = one wheel circumference per cycle, so the wheels roll without sliding),
WalkInPlace, Attack (ram forward and back), Impact (shake), Death (topples over to the side).
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC, DST = argv[0], argv[1]
FPS = 30
WHEEL_X = 0.235   # |x| beyond the chassis: wheels and hub caps

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
mesh = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o is not mesh:
        bpy.data.objects.remove(o, do_unlink=True)

co = np.array([v.co[:] for v in mesh.data.vertices])
H = co[:, 2].max()

# ------------------------------------------------------------------ wheels: side (x sign) and axle (front/back in y)
low = (np.abs(co[:, 0]) > WHEEL_X) & (co[:, 2] < 0.30 * H)
wy = co[low, 1]
# two axles: split the wheel vertices at the largest gap / median in y
y_mid = 0.5 * (wy.min() + wy.max())
axles = {}
for name, sel in (("F", wy < y_mid), ("B", wy >= y_mid)):
    ys = wy[sel]
    zs = co[low, 2][sel]
    axles[name] = (0.5 * (ys.min() + ys.max()), 0.5 * (zs.min() + zs.max()), 0.5 * (zs.max() - zs.min()))
# drawbar side = front: the cart must look to -Y. If the drawbar sticks out at +Y, turn the model round.
lowc = co[co[:, 2] < 0.3 * H]
centre_y = 0.5 * (axles["F"][0] + axles["B"][0])
if lowc[:, 1].max() - centre_y > centre_y - lowc[:, 1].min():
    for v in mesh.data.vertices:
        v.co.x, v.co.y = -v.co.x, -v.co.y
    co = np.array([v.co[:] for v in mesh.data.vertices])
    return_flip = True
    axles = {"F": (-axles["B"][0], axles["B"][1], axles["B"][2]), "B": (-axles["F"][0], axles["F"][1], axles["F"][2])}
    centre_y = -centre_y
else:
    return_flip = False
# centre the cart between the axles on the square
for v in mesh.data.vertices:
    v.co.y -= centre_y
co = np.array([v.co[:] for v in mesh.data.vertices])
axles = {k: (a[0] - centre_y, a[1], a[2]) for k, a in axles.items()}
R = 0.5 * (axles["F"][2] + axles["B"][2])
print(f"[turm] H {H:.3f} flipped {return_flip} axles F y {axles['F'][0]:.3f} B y {axles['B'][0]:.3f} "
      f"hub z {axles['F'][1]:.3f}/{axles['B'][1]:.3f} R {R:.3f}")

# ------------------------------------------------------------------ armature
arm = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", arm)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.edit_bones
x_side = float(np.abs(co[np.abs(co[:, 0]) > WHEEL_X, 0]).max())


def bone(name, head, tail, parent=None):
    b = eb.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.roll = 0
    if parent:
        b.parent = eb[parent]
    return b


bone("Hips", (0, 0, 0), (0, 0, 0.15 * H))
bone("Tip", (x_side, 0, 0), (x_side, 0, 0.15 * H), "Hips")
bone("Body", (0, 0, R), (0, 0, 0.6 * H), "Tip")
WHEELS = {}
for ax in ("F", "B"):
    y, z, _ = axles[ax]
    for side, sx in (("L", 1), ("R", -1)):
        n = f"Wheel.{ax}{side}"
        # every wheel bone points to +X: its own Y axis is the world X axis, the axle
        bone(n, (sx * x_side, y, z), (sx * x_side + 0.05, y, z), "Body")
        WHEELS[n] = (sx, y, z)
bpy.ops.object.mode_set(mode="OBJECT")

# ------------------------------------------------------------------ skinning: rigid parts
vg = {n: mesh.vertex_groups.new(name=n) for n in ["Hips", "Tip", "Body"] + list(WHEELS)}


def nearest_wheel(x, y):
    return min(WHEELS, key=lambda n: (np.sign(x) != WHEELS[n][0]) * 9 + abs(y - WHEELS[n][1]))


def in_wheel(x, y, z, x_min, r_max):
    if abs(x) <= x_min:
        return False
    _, wy_, wz_ = WHEELS[nearest_wheel(x, y)]
    return math.hypot(y - wy_, z - wz_) < r_max


# the edge of the cart board lies at the same |x| as the inner face of the wheels: decide per connected part
# (a wheel is usually its own part), and inside mixed parts only by a stricter test
import bmesh  # noqa: E402

bm = bmesh.new()
bm.from_mesh(mesh.data)
bm.verts.ensure_lookup_table()
seen = np.zeros(len(bm.verts), bool)
wheel_of = {}
for v0 in bm.verts:
    if seen[v0.index]:
        continue
    stack, part = [v0], []
    seen[v0.index] = True
    while stack:
        v = stack.pop()
        part.append(v.index)
        for e in v.link_edges:
            w = e.other_vert(v)
            if not seen[w.index]:
                seen[w.index] = True
                stack.append(w)
    pts = co[part]
    loose = np.mean([in_wheel(*p, WHEEL_X, 1.12 * R) for p in pts])
    if loose > 0.8:
        for i in part:
            wheel_of[i] = nearest_wheel(co[i, 0], co[i, 1])
    else:
        for i in part:
            if in_wheel(*co[i], WHEEL_X + 0.012 * H, 1.02 * R) and co[i, 2] < axles["F"][1] + 0.9 * R:
                wheel_of[i] = nearest_wheel(co[i, 0], co[i, 1])
bm.free()
for n in WHEELS:
    vg[n].add([i for i, w in wheel_of.items() if w == n], 1.0, "REPLACE")
vg["Body"].add([v.index for v in mesh.data.vertices if v.index not in wheel_of], 1.0, "REPLACE")
print("[turm] wheel vertices", {n: sum(1 for w in wheel_of.values() if w == n) for n in WHEELS})
mesh.parent = rig
mod = mesh.modifiers.new("Armature", "ARMATURE")
mod.object = rig

# ------------------------------------------------------------------ animations
scene = bpy.context.scene
scene.render.fps = FPS
rig.animation_data_create()
pb = rig.pose.bones
for b in pb:
    b.rotation_mode = "XYZ"
CIRC = 2 * math.pi * R


def action(name, frames, fn):
    """fn(f, t) sets the pose of frame f (t = 0..1) and returns nothing; every bone gets a key on every frame."""
    act = bpy.data.actions.new(name)
    rig.animation_data.action = act
    for f in range(frames + 1):
        for b in pb:
            b.location = (0, 0, 0)
            b.rotation_euler = (0, 0, 0)
        fn(f, f / frames)
        for b in pb:
            b.keyframe_insert("location", frame=f)
            b.keyframe_insert("rotation_euler", frame=f)
    act.use_fake_user = True
    return act


def spin(angle):
    for n in WHEELS:
        pb[n].rotation_euler.y = angle


def body_motion(t, rock=1.0):
    # two small bumps per wheel turn (the tower sits on a rough cart), slight pitch
    pb["Body"].location.z = 0.006 * H * rock * abs(math.sin(2 * math.pi * t))
    pb["Body"].rotation_euler.x = math.radians(0.8) * rock * math.sin(4 * math.pi * t)
    pb["Body"].rotation_euler.y = math.radians(0.6) * rock * math.sin(2 * math.pi * t + 0.7)


# Bone axes: Hips and Body point up (+Z): local Y = world Z, local Z = world -Y, local X = world X.
# A bone's location is in its own axes: moving the Hips forward (world -Y) = local +Z.
def idle(f, t):
    pb["Body"].rotation_euler.y = math.radians(0.4) * math.sin(2 * math.pi * t)
    pb["Body"].location.z = 0.002 * H * math.sin(2 * math.pi * t)   # local Z = world -Y: tiny creak forward/back


action("Idle", 90, idle)
action("WalkInPlace", 30, lambda f, t: (spin(2 * math.pi * t), body_motion(t)))
action("Walk", 30, lambda f, t: (spin(2 * math.pi * t), body_motion(t), setattr(pb["Hips"], "location", (0, 0, CIRC * t))))


def attack(f, t):
    # back up a little, then ram forward and roll back
    d = (-0.06 * math.sin(math.pi * t / 0.35) if t < 0.35 else
         0.22 * math.sin(math.pi * (t - 0.35) / 0.65) ** 0.6) * H
    pb["Hips"].location = (0, 0, d)
    spin(d / R)
    pb["Body"].rotation_euler.x = math.radians(6) * max(0.0, math.sin(math.pi * (t - 0.35) / 0.65)) if t > 0.35 else 0


action("Attack", 36, attack)


def impact(f, t):
    k = math.exp(-4 * t)
    pb["Body"].rotation_euler.x = math.radians(7) * k * math.sin(2 * math.pi * 5 * t)
    pb["Body"].rotation_euler.z = math.radians(5) * k * math.sin(2 * math.pi * 4 * t + 1)
    pb["Hips"].location.z = -0.04 * H * k * math.sin(math.pi * min(1, t * 3))


action("Impact", 30, impact)


def death(f, t):
    # shake, then tip over to the right (about the right wheels), small bounce at the end
    if t < 0.3:
        k = t / 0.3
        pb["Body"].rotation_euler.z = math.radians(4) * math.sin(2 * math.pi * 6 * t) * (1 - k)
        a = 0
    else:
        u = (t - 0.3) / 0.7
        a = math.radians(88) * min(1, u * u * 1.6) - math.radians(5) * max(0, math.sin(math.pi * (u - 0.8) / 0.2)) * (u > 0.8)
    pb["Tip"].rotation_euler.y = -a   # Tip points up (+Z) at +X: rotation about its Y axis (= world Z)? see below


# Tip bone points up (local Y = world Z). Tipping over to +X is a rotation about the world Y axis = the bone's local Z
# axis (world -Y) -> use rotation_euler.z with a negative sign for "over to +X".
def death_fixed(f, t):
    death(f, t)
    a = -pb["Tip"].rotation_euler.y
    pb["Tip"].rotation_euler.y = 0
    pb["Tip"].rotation_euler.z = -a   # local Z = world -Y; -a about it = +a about world Y: the top falls to +X


action("Death", 60, death_fixed)
rig.animation_data.action = bpy.data.actions["Idle"]
# linear sampling: the glTF exporter samples every frame anyway
for act in bpy.data.actions:
    for fc in act.fcurves if hasattr(act, "fcurves") else []:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="JPEG", export_image_quality=90,
                          export_yup=True, export_skins=True, export_animations=True,
                          export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_range=False)
print(f"[turm] OUT {DST} circumference {CIRC:.3f} actions {[a.name for a in bpy.data.actions]}")
