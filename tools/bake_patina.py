"""Patina für Schnitzfiguren: Ambient Occlusion (Abdunklung der Vertiefungen) in die Farbtextur einbrennen.

  (Blender) bake_patina.py in.glb out.glb [--strength 0.75] [--distance 0.02] [--samples 64] [--size 4096]

Die AO wird mit Cycles auf der GPU in eine eigene Textur gebacken und mit der Grundfarbe multipliziert:
farbe * mix(1, ao, strength). Vertiefungen (Kettenhemd, Falten, Gesicht) werden dunkler, erhabene Stellen
bleiben hell, wie Patina in den Ritzen von altem Elfenbein. --distance ist der Radius in Metern
(bezogen auf die Figurenhöhe nach glb_post, ~1 m): klein = feine Ritzen, groß = großflächige Schatten.
"""
import argparse
import sys

import bpy
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--strength", type=float, default=0.75)
p.add_argument("--distance", type=float, default=0.02)
p.add_argument("--samples", type=int, default=64)
p.add_argument("--size", type=int, default=4096)
a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
for d in prefs.devices:
    d.use = True
scene.cycles.device = "GPU"
scene.cycles.samples = a.samples
scene.world = scene.world or bpy.data.worlds.new("w")
scene.world.light_settings.distance = a.distance

for ob in [o for o in scene.objects if o.type == "MESH"]:
    mat = ob.active_material
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    link = bsdf.inputs["Base Color"].links[0]
    base_node = link.from_node
    base_img = base_node.image
    # AO in eine eigene Textur backen (gleiche UVs)
    ao_img = bpy.data.images.new("ao", a.size, a.size, float_buffer=False)
    ao_node = nt.nodes.new("ShaderNodeTexImage")
    ao_node.image = ao_img
    for n in nt.nodes:
        n.select = False
    ao_node.select = True
    nt.nodes.active = ao_node
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    scene.render.bake.margin = 8
    bpy.ops.object.bake(type="AO")
    # Farbtextur * mix(1, ao, strength)
    w, h = base_img.size
    base = np.empty(w * h * 4, dtype=np.float32)
    base_img.pixels.foreach_get(base)
    base = base.reshape(h, w, 4)
    ao = np.empty(a.size * a.size * 4, dtype=np.float32)
    ao_img.pixels.foreach_get(ao)
    ao = ao.reshape(a.size, a.size, 4)[..., 0]
    if (w, h) != (a.size, a.size):
        ys = (np.arange(h) * a.size / h).astype(int)
        xs = (np.arange(w) * a.size / w).astype(int)
        ao = ao[ys][:, xs]
    # Kontrast der AO strecken: der hellste Bereich (freie Flächen) bleibt unverändert
    ao = np.clip(ao / max(np.percentile(ao, 98), 1e-3), 0, 1)
    k = 1.0 - a.strength * (1.0 - ao)
    base[..., :3] *= k[..., None]
    base_img.pixels.foreach_set(base.ravel())
    base_img.update()
    nt.nodes.remove(ao_node)
    print(f"[patina] {ob.name}: texture {w}x{h}, AO mean {ao.mean():.3f}, darkening mean {1 - k.mean():.3f}")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=a.dst, export_format="GLB", export_image_format="JPEG",
                          export_image_quality=92, export_yup=True)
print(f"[patina] OUT {a.dst}")
