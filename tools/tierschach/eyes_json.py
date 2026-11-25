"""eyes.json für eye_geo/tex_eyecover von Hand erzeugen (wenn tex_eyes die gemalten Augen nicht findet).

  blender -b --python schach/tools/eyes_json.py -- post.glb eyes.json --pick "0.36,0.64;0.61,0.64" [--r 0.03]

--pick: je Auge (x-Anteil, Höhen-Anteil) der BBox in der Frontansicht (tools/eyepick.py zeigt das Raster);
der Punkt wird per Raycast von vorn (-Y) auf die Oberfläche gelegt. --r: Augenradius als Anteil der Höhe.
Ausgabe wie tex_eyes --save-eyes: lokale Mesh-Koordinaten in glTF-Achsen (x, oben, vorn), Radius r.
"""
import argparse
import json
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
p = argparse.ArgumentParser(prog="eyes_json")
p.add_argument("src")
p.add_argument("out")
p.add_argument("--pick", required=True)
p.add_argument("--r", type=float, default=0.035, help="Radius als Anteil der Höhe")
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
sc = bpy.context.scene
o = [x for x in sc.objects if x.type == "MESH"][0]
P = [o.matrix_world @ v.co for v in o.data.vertices]
mn = Vector([min(q[i] for q in P) for i in range(3)])
mx = Vector([max(q[i] for q in P) for i in range(3)])
ext = mx - mn
dg = bpy.context.evaluated_depsgraph_get()
inv = o.matrix_world.inverted()
eyes = []
for pair in a.pick.split(";"):
    fx, fh = (float(t) for t in pair.split(","))
    org = Vector((mn.x + fx * ext.x, mn.y - 1.0, mn.z + fh * ext.z))
    hit, loc, *_ = sc.ray_cast(dg, org, Vector((0, 1, 0)))
    if not hit:
        sys.exit(f"[eyes_json] kein Treffer bei {fx},{fh}")
    l = inv @ loc
    s = o.matrix_world.to_scale()[0]
    eyes.append({"c": [l.x, l.z, -l.y], "r": a.r * ext.z / s})
    print(f"[eyes_json] Auge bei {fx},{fh}: Welt {tuple(round(v, 3) for v in loc)}")
json.dump(eyes, open(a.out, "w"))
print(f"[eyes_json] -> {a.out}: {eyes}")
