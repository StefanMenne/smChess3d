"""Gleicht die Farbtextur einer Figur an eine Bezugsfarbe an (Mittelwert und Streuung je Kanal).

  (Blender) color_match.py in.glb out.glb --ref REF.png|REF.glb [--contrast 0.5]

REF ist ein Bild (z. B. Holztextur) oder eine andere Figur (deren Farbtextur). Ungenutzte, fast schwarze Flächen
des Texturatlas werden nicht mitgezählt. --contrast mischt die Streuung: 0 = eigene behalten, 1 = ganz die der
Referenz. Form, Maserung, Patina und Schnitzdetails bleiben erhalten, nur der Farbton wird angeglichen.
"""
import argparse
import sys

import bpy
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--ref", required=True)
p.add_argument("--contrast", type=float, default=0.5)
a = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

LUM = np.array([0.2126, 0.7152, 0.0722])


def base_image():
    ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    nt = ob.active_material.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    return bsdf.inputs["Base Color"].links[0].from_node.image


def pixels(img):
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(-1, 4)


if a.ref.lower().endswith(".glb"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=a.ref)
    ref = pixels(base_image())[:, :3]
else:
    from PIL import Image
    ref = np.asarray(Image.open(a.ref).convert("RGB")).reshape(-1, 3).astype(np.float32) / 255
ref = ref[(ref @ LUM) > 0.02]
rm, rs = ref.mean(0), ref.std(0)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
img = base_image()
px = pixels(img)
rgb = px[:, :3]
m = (rgb @ LUM) > 0.02
sm, ss = rgb[m].mean(0), rgb[m].std(0)
k = a.contrast * (rs / np.maximum(ss, 1e-4)) + (1 - a.contrast)
rgb[m] = np.clip((rgb[m] - sm) * k + rm, 0, 1)
px[:, :3] = rgb
img.pixels.foreach_set(px.ravel())
img.update()
print(f"[color] {a.src}: mean {sm.round(3)} -> {rm.round(3)} (ref {a.ref}), scale {k.round(2)}")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=a.dst, export_format="GLB", export_image_format="JPEG",
                          export_image_quality=92, export_yup=True)
print(f"[color] OUT {a.dst}")
