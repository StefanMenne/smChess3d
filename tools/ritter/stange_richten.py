"""Richtet das untere Ende einer geknickten Stange (Fahnenstange, Speer) gerade aus, vor dem Riggen.

  blender -b --python tools/ritter/stange_richten.py -- in.glb out.glb --start x,y,z [--fit 0.45,0.69] [--radius 0.02]
          [--boden 1]

Die Stange wird ab dem Punkt --start (Mitte der Stange, Modelleinheiten) Höhe für Höhe verfolgt (Mittelpunkt der
Punkte im Umkreis von --radius um die vorige Mitte). Aus dem geraden Abschnitt --fit (z von..bis) entsteht eine
Gerade; unterhalb dessen Unterkante werden die Punkte der Stange je Höhe um (Gerade - gemessene Mitte) verschoben.
Mit --boden 1: steht die Stange tiefer als die Füße (glb_post stellt den tiefsten Punkt auf z = 0), wird die Figur
abgesenkt, bis die Sohlen auf dem Boden stehen, und das untere Stück der Stange (unter --fit-Unterkante) entlang der
Geraden so gestaucht, dass ihre Spitze wieder bei z = 0 endet.
"""
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]
o = dict(zip(argv[2::2], argv[3::2]))
START = np.array([float(v) for v in o["--start"].split(",")])
Z0, Z1 = (float(v) for v in o.get("--fit", "0.45,0.69").split(","))
R = float(o.get("--radius", 0.02))
BODEN = o.get("--boden", "0") == "1"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
m = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"][0]
M, Mi = m.matrix_world, m.matrix_world.inverted()
W = np.array([(M @ v.co)[:] for v in m.data.vertices])


def track(zs, start):
    prev, out = start[:2].copy(), {}
    for z in zs:
        P = W[np.abs(W[:, 2] - z) < 0.004]
        Q = P[np.linalg.norm(P[:, :2] - prev, axis=1) < R]
        if len(Q):
            prev = Q[:, :2].mean(0)
            out[round(z, 3)] = prev.copy()
    return out


step = 0.01
down = track(np.arange(START[2], -0.001, -step), START)
up = track(np.arange(START[2], Z1 + 0.001, step), START)
cent = {**down, **up}
fz = np.array([z for z in cent if Z0 <= z <= Z1])
fit = [np.polyfit(fz, [cent[z][i] for z in fz], 1) for i in (0, 1)]
line = lambda z: np.array([np.polyval(fit[0], z), np.polyval(fit[1], z)])
zs = np.array(sorted(z for z in cent if z < Z0))
moved, maxoff = 0, 0.0
for i, v in enumerate(m.data.vertices):
    z = W[i, 2]
    if z >= Z0 or len(zs) == 0:
        continue
    c = np.array([np.interp(z, zs, [cent[k][j] for k in zs]) for j in (0, 1)])
    if np.linalg.norm(W[i, :2] - c) >= R * 1.3:
        continue
    off = line(z) - c
    p = Vector((W[i, 0] + off[0], W[i, 1] + off[1], z))
    v.co = Mi @ p
    moved += 1
    maxoff = max(maxoff, float(np.linalg.norm(off)))
if BODEN:
    W = np.array([(M @ v.co)[:] for v in m.data.vertices])
    pole = np.array([np.linalg.norm(W[i, :2] - line(W[i, 2])) < R * 1.3 and W[i, 2] < Z1 for i in range(len(W))])
    floor = float(W[~pole, 2].min())
    zmin = float(W[pole, 2].min()) - floor          # Stangenspitze nach dem Absenken (negativ)
    # untere Stange zwischen z = zmin und Z0 (nach dem Absenken) auf 0..Z0 strecken bzw. stauchen, entlang der Geraden
    top = Z0 - floor
    for i, v in enumerate(m.data.vertices):
        z = W[i, 2] - floor
        x, y = W[i, 0], W[i, 1]
        if pole[i] and z < top:
            z2 = top - (top - z) * top / (top - zmin)
            d = line(z2 + floor) - line(z + floor)
            x, y, z = x + d[0], y + d[1], z2
        v.co = Mi @ Vector((x, y, z))
    print(f"[stange] Figur um {floor:.4f} abgesenkt (Sohlen auf z = 0), Stangenspitze von {zmin:.4f} auf 0 gestaucht")
print(f"[stange] verfolgt {len(cent)} Höhen, gerade Linie aus z {Z0}..{Z1}, {moved} Punkte verschoben, "
      f"größte Verschiebung {maxoff:.3f}, Fuß jetzt bei {line(0.0).round(3)}")
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="AUTO", export_yup=True)
