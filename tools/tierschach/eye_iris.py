"""Augen aus eye_geo verschönern: Pupille -> farbige Iris mit kleinerer Pupille davor, optional ein dunkler Rand
hinter dem Augenweiß (--rim-scale > 1; bisher verdeckte er auf der gewölbten Kuppel das Weiß -> Standard aus).

  blender -b --factory-startup --python tools/tierschach/eye_iris.py -- in.glb out.glb
          [--iris 0.30,0.15,0.06] [--pupil 0.58] [--rim 0.30,0.22,0.20] [--rim-scale 0]

Eingabe: Ausgabe von eye_geo (Objekte Eye<N>_white, Eye<N>_pupil, Eye<N>_glint*). Neue Objekte heißen
Eye<N>_iris_pupil und Eye<N>_rim, damit die Rigs sie wie die anderen Eye*-Teile an den Kopf hängen.
--pupil: Pupillenradius als Anteil der Iris; --rim-scale: Randradius als Vielfaches des Augenweiß-Radius.
"""
import argparse
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
p = argparse.ArgumentParser(prog="eye_iris")
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--iris", default="0.30,0.15,0.06")
p.add_argument("--pupil", type=float, default=0.58)
p.add_argument("--rim", default="0.30,0.22,0.20")
p.add_argument("--rim-scale", type=float, default=0.0)
p.add_argument("--rim-back", type=float, default=0.05, help="Rand nach hinten (x Tiefe der Augenkuppel)")
a = p.parse_args(argv)


def rgb(s):
    return [float(x) for x in s.split(",")] + [1.0]


def material(name, color, rough=0.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    return m


def frame(o):
    """Mittelpunkt und Normale (kleinste Hauptachse, nach vorn = -Y) der Weltkoordinaten."""
    v = np.array([tuple(o.matrix_world @ x.co) for x in o.data.vertices])
    c = v.mean(0)
    w, vec = np.linalg.eigh(np.cov((v - c).T))
    n = vec[:, 0]
    if n[1] > 0:
        n = -n
    return c, n


def transform_copy(o, name, mat, scale, push, center, normal):
    """Kopie von o, in der Ebene senkrecht zu normal um center skaliert und entlang normal verschoben."""
    me = o.data.copy()
    c2 = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(c2)
    c2.matrix_world = o.matrix_world.copy()
    mw, mi = c2.matrix_world, c2.matrix_world.inverted()
    n = Vector(normal)
    ctr = Vector(center)
    for v in me.vertices:
        w = mw @ v.co
        d = w - ctr
        along = d.dot(n)
        w = ctr + (d - along * n) * scale + along * n + push * n
        v.co = mi @ w
    me.materials.clear()
    me.materials.append(mat)
    return c2


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
objs = {o.name: o for o in bpy.context.scene.objects if o.type == "MESH"}
m_iris = material("Eye_iris", rgb(a.iris))
m_pup = material("Eye_pupil_dark", [0.0, 0.0, 0.01, 1.0], 0.2)
m_rim = material("Eye_rim", rgb(a.rim), 0.6)

ids = sorted({n.split("_")[0] for n in objs if n.startswith("Eye") and n.endswith("_pupil")})
for e in ids:
    pupil, white = objs[f"{e}_pupil"], objs[f"{e}_white"]
    pc, pn = frame(pupil)
    wc, wn = frame(white)
    thick = float(np.ptp([(pupil.matrix_world @ v.co - Vector(pc)).dot(Vector(pn)) for v in pupil.data.vertices]))
    pupil.data.materials.clear()
    pupil.data.materials.append(m_iris)
    pupil.name = f"{e}_iris"
    print(f"[eye_iris] {e}: iris {a.iris}, pupil {a.pupil}, rim {a.rim_scale or 'aus'}")
    push = max(thick, 0.002) * 0.6
    transform_copy(pupil, f"{e}_iris_pupil", m_pup, a.pupil, push, pc, pn)
    for g in [o for n, o in objs.items() if n.startswith(f"{e}_glint")]:   # Glanzpunkte vor die neue Pupille
        g.location += Vector(pn) * (push + 0.001)
    # Rand: flache Kopie des Augenweiß, etwas größer und ein Stück nach hinten
    if a.rim_scale <= 0:
        continue
    depth = float(np.ptp([(white.matrix_world @ v.co - Vector(wc)).dot(Vector(wn)) for v in white.data.vertices]))
    transform_copy(white, f"{e}_rim", m_rim, a.rim_scale, -depth * a.rim_back, wc, wn)

bpy.ops.export_scene.gltf(filepath=a.dst, export_format="GLB")
print("[eye_iris] OUT", a.dst)
