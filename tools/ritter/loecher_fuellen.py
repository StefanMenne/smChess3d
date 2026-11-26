"""Schließt Löcher im Mesh einer Figur (z. B. nach dem Wegschneiden einer Stange), vor dem Riggen.

  blender -b --python tools/ritter/loecher_fuellen.py -- in.glb out.glb [--max 200]

Verschweißt doppelte Punkte (UV-Nähte), füllt jede offene Randschleife mit bis zu --max Kanten und gibt den neuen
Flächen die UV-Koordinaten der angrenzenden Flächen (der Flicken zeigt so die Textur ringsum, z. B. Umhangstoff).
Offene Ränder öffnen sich sonst in der Animation zu schwarzen Spalten, sobald die Seiten verschiedenen Knochen folgen.
"""
import sys

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]
opt = dict(zip(argv[2::2], argv[3::2]))
MAX = int(opt.get("--max", 200))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
mesh = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bm = bmesh.new()
bm.from_mesh(mesh.data)
n0 = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
print(f"[fill] verschweißt: {n0 - len(bm.verts)} Punkte")
uv = bm.loops.layers.uv.active
# UV je Punkt aus den vorhandenen Flächen (vor dem Füllen)
uv_of = {}
for f in bm.faces:
    for lo in f.loops:
        uv_of.setdefault(lo.vert, lo[uv].uv.copy())
edges = [e for e in bm.edges if e.is_boundary]
res = bmesh.ops.holes_fill(bm, edges=edges, sides=MAX)
new = res["faces"]
tri = bmesh.ops.triangulate(bm, faces=new)["faces"] if new else []
for f in tri:
    for lo in f.loops:
        if lo.vert in uv_of:
            lo[uv].uv = uv_of[lo.vert]
left = sum(1 for e in bm.edges if e.is_boundary)
print(f"[fill] Randkanten {len(edges)}, gefüllte Löcher {len(new)}, neue Dreiecke {len(tri)}, offen danach {left}")
bm.to_mesh(mesh.data)
bm.free()
bpy.ops.export_scene.gltf(filepath=DST, export_format="GLB", export_image_format="AUTO", export_yup=True)
