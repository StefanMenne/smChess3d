"""Eigene HDR-Umgebung für das Spiel: ein Arbeitszimmer, mit Cycles als Rundum-Bild (equirectangular) gerendert.

  (Blender) raum.py OUT.hdr [--size 2048] [--samples 512] [--preview vorschau.jpg]

Der Raum ist so gebaut, dass Metall, Lack und Glas überall etwas Sinnvolles spiegeln: Fenster mit Tageslicht und
Sonnenstrahl links vorn (passend zur Sonne im Spiel, die von links vorn oben kommt), warme Pendelleuchte über dem
Tisch, Leselampe, Bücherregal hinter der schwarzen Seite, Bild und Tür an den Seiten, Holzvertäfelung unten,
verputzte Wände oben, Eichendielen, helle Decke. Die Kamera steht auf Tischhöhe in der Raummitte, darunter eine
dunkle Tischplatte (so spiegeln die Figuren nach unten den Tisch, auf dem das Brett steht).

Koordinaten (Blender): Mitte des Tischs im Ursprung, Z oben. Die weiße Seite (die Kamera im Spiel) liegt bei -Y,
die schwarze bei +Y (glTF/three.js: +Z bzw. -Z). Das Rundum-Bild ist als Radiance-HDR in linearen Werten
gespeichert (echte Helligkeiten: das Fenster ist rund hundertmal heller als eine Wand).
"""
import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--size", type=int, default=2048)
p.add_argument("--samples", type=int, default=512)
p.add_argument("--preview", default="")
args = p.parse_args(sys.argv[1:])
random.seed(7)

scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)

W, D, H = 6.0, 5.0, 2.8          # Raum: Breite (X), Tiefe (Y), Höhe
X0, X1, Y0, Y1 = -W / 2, W / 2, -D / 2, D / 2
TABLE = 0.74                     # Tischhöhe; die Kamera schwebt knapp darüber
EYE = 0.86


# ---------------------------------------------------------------------------
# Materialien
# ---------------------------------------------------------------------------

def material(name, color, rough=0.6, metal=0.0, emit=None, strength=0.0, noise=0.0, noise_scale=8.0, stretch=None):
    """Principled-Material; noise mischt eine dunklere Variante dazu (Holz, Putz), stretch streckt das Rauschen
    in eine Achse (Maserung)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if noise:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch or (1, 1, 1)
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = noise_scale
        nz.inputs["Detail"].default_value = 8
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*color, 1)
        mix.inputs["B"].default_value = (*(c * (1 - noise) for c in color), 1)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


PUTZ = material("putz", (0.70, 0.61, 0.49), 0.9, noise=0.12, noise_scale=3)
DECKE = material("decke", (0.50, 0.47, 0.43), 0.9)
VERTAEFELUNG = material("vertaefelung", (0.16, 0.085, 0.045), 0.45, noise=0.35, noise_scale=6, stretch=(6, 6, 0.4))
LEISTE = material("leiste", (0.10, 0.055, 0.03), 0.4)
DIELEN = material("dielen", (0.30, 0.18, 0.09), 0.5, noise=0.4, noise_scale=5, stretch=(0.5, 8, 8))
TISCH = material("tisch", (0.12, 0.065, 0.035), 0.35, noise=0.3, noise_scale=6, stretch=(1, 10, 1))
RAHMEN = material("fensterrahmen", (0.75, 0.72, 0.66), 0.5)
HIMMEL = material("draussen", (0.0, 0.0, 0.0), 1.0, emit=(0.75, 0.86, 1.0), strength=14.0)
GARTEN = material("garten", (0.0, 0.0, 0.0), 1.0, emit=(0.30, 0.42, 0.22), strength=3.5)
LAMPE = material("lampe", (0.0, 0.0, 0.0), 1.0, emit=(1.0, 0.72, 0.45), strength=60.0)
# Pendelleuchte gedämpft: sie hängt groß direkt über dem Tisch; zu hell, und alles nach oben Gewandte wird blass
PENDEL = material("pendellicht", (0.0, 0.0, 0.0), 1.0, emit=(1.0, 0.76, 0.52), strength=18.0)
SCHIRM = material("schirm", (0.85, 0.78, 0.62), 0.7)
MESSING = material("messing", (0.80, 0.60, 0.30), 0.3, metal=1.0)
REGAL = material("regal", (0.20, 0.11, 0.06), 0.5, noise=0.25, noise_scale=6, stretch=(1, 1, 8))
TUER = material("tuer", (0.22, 0.12, 0.06), 0.45, noise=0.3, noise_scale=6, stretch=(1, 1, 8))
BILD = material("bild", (0.25, 0.32, 0.22), 0.8, noise=0.5, noise_scale=2)
GOLDRAHMEN = material("goldrahmen", (0.75, 0.55, 0.25), 0.35, metal=1.0)
TEPPICH = material("teppich", (0.32, 0.08, 0.06), 0.95, noise=0.45, noise_scale=12)
BUCHFARBEN = [(0.35, 0.06, 0.05), (0.08, 0.18, 0.10), (0.10, 0.12, 0.25), (0.40, 0.28, 0.12), (0.18, 0.10, 0.05),
              (0.45, 0.40, 0.30), (0.25, 0.05, 0.10), (0.05, 0.05, 0.06)]
BUECHER = [material(f"buch{i}", c, 0.6, noise=0.2, noise_scale=20) for i, c in enumerate(BUCHFARBEN)]


def box(name, mat, x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object
    o.name = name
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(mat)
    return o


T = 0.1   # Wanddicke

# ---------------------------------------------------------------------------
# Raum
# ---------------------------------------------------------------------------

box("boden", DIELEN, X0, X1, Y0, Y1, -T, 0)
box("decke", DECKE, X0, X1, Y0, Y1, H, H + T)
# Fenster links (-X) vorn: Öffnung y -1.6..-0.2, z 0.9..2.4
WY0, WY1, WZ0, WZ1 = -1.6, -0.2, 0.9, 2.4
box("wand_links_a", PUTZ, X0 - T, X0, Y0, WY0, 0, H)
box("wand_links_b", PUTZ, X0 - T, X0, WY1, Y1, 0, H)
box("wand_links_unten", PUTZ, X0 - T, X0, WY0, WY1, 0, WZ0)
box("wand_links_oben", PUTZ, X0 - T, X0, WY0, WY1, WZ1, H)
box("wand_rechts", PUTZ, X1, X1 + T, Y0, Y1, 0, H)
box("wand_vorn", PUTZ, X0, X1, Y0 - T, Y0, 0, H)
box("wand_hinten", PUTZ, X0, X1, Y1, Y1 + T, 0, H)
# Vertäfelung bis 1 m, Abschlussleiste, Sockelleiste (nicht vor dem Fenster)
for name, a in [("vorn", (X0, X1, Y0, Y0 + 0.02)), ("hinten", (X0, X1, Y1 - 0.02, Y1)),
                ("rechts", (X1 - 0.02, X1, Y0, Y1)), ("links_a", (X0, X0 + 0.02, Y0, WY0)),
                ("links_b", (X0, X0 + 0.02, WY1, Y1)), ("links_fenster", (X0, X0 + 0.02, WY0, WY1))]:
    x0, x1, y0, y1 = a
    top = 0.88 if name == "links_fenster" else 1.0
    box("vertaefelung_" + name, VERTAEFELUNG, x0, x1, y0, y1, 0, top)
    box("leiste_" + name, LEISTE, x0 - 0.01 * (x0 == X0), x1 + 0.01 * (x1 == X1), y0 - 0.01 * (y0 == Y0),
        y1 + 0.01 * (y1 == Y1), top, top + 0.05)
# Fensterrahmen mit Sprossenkreuz, draußen Himmel und Garten (leuchtende Flächen)
box("rahmen_u", RAHMEN, X0 - 0.06, X0 + 0.04, WY0, WY1, WZ0 - 0.04, WZ0)
box("rahmen_o", RAHMEN, X0 - 0.06, X0 + 0.04, WY0, WY1, WZ1, WZ1 + 0.04)
box("rahmen_v", RAHMEN, X0 - 0.06, X0 + 0.04, WY0 - 0.04, WY0, WZ0, WZ1)
box("rahmen_h", RAHMEN, X0 - 0.06, X0 + 0.04, WY1, WY1 + 0.04, WZ0, WZ1)
box("sprosse_s", RAHMEN, X0 - 0.05, X0 - 0.03, (WY0 + WY1) / 2 - 0.02, (WY0 + WY1) / 2 + 0.02, WZ0, WZ1)
box("sprosse_q", RAHMEN, X0 - 0.05, X0 - 0.03, WY0, WY1, 1.75, 1.79)
box("himmel", HIMMEL, X0 - 2.0, X0 - 1.98, -4, 3, 1.3, 6)
box("garten", GARTEN, X0 - 2.0, X0 - 1.98, -4, 3, -1, 1.3)
# Sonne durch das Fenster: warmer Lichtfleck auf Boden und Tisch
bpy.ops.object.light_add(type="SUN", location=(X0 - 3, -0.9, 4))
sun = bpy.context.object
sun.data.energy = 5.0
sun.data.color = (1.0, 0.92, 0.80)
sun.data.angle = math.radians(1.5)
sun.rotation_euler = (Vector((0.2, -0.9, TABLE)) - sun.location).to_track_quat("-Z", "Y").to_euler()

# Tür rechts (+X) hinten
box("tuer", TUER, X1 - 0.03, X1, 0.6, 1.5, 0, 2.1)
box("tuerrahmen", LEISTE, X1 - 0.05, X1, 0.52, 1.58, 2.1, 2.18)
box("klinke", MESSING, X1 - 0.09, X1 - 0.03, 1.38, 1.46, 1.02, 1.06)
# Bild rechts vorn
box("bildrahmen", GOLDRAHMEN, X1 - 0.05, X1, -1.9, -0.5, 1.3, 2.2)
box("bild", BILD, X1 - 0.06, X1 - 0.04, -1.82, -0.58, 1.38, 2.12)
# Bücherregal hinten (+Y), hinter der schwarzen Seite
RX0, RX1 = -1.8, 1.4
box("regal_rueck", REGAL, RX0, RX1, Y1 - 0.04, Y1, 0, 2.3)
box("regal_l", REGAL, RX0, RX0 + 0.04, Y1 - 0.38, Y1, 0, 2.3)
box("regal_r", REGAL, RX1 - 0.04, RX1, Y1 - 0.38, Y1, 0, 2.3)
box("regal_o", REGAL, RX0, RX1, Y1 - 0.38, Y1, 2.26, 2.3)
for z in (0.0, 0.45, 0.9, 1.35, 1.8):
    box(f"brett_{z}", REGAL, RX0, RX1, Y1 - 0.38, Y1, z, z + 0.03)
    x = RX0 + 0.06
    while x < RX1 - 0.1:
        w = random.uniform(0.025, 0.06)
        h = random.uniform(0.25, 0.38)
        if random.random() < 0.08:
            x += random.uniform(0.05, 0.2)   # Lücke
            continue
        box("buch", random.choice(BUECHER), x, x + w, Y1 - 0.32, Y1 - 0.06, z + 0.03, z + 0.03 + h)
        x += w + 0.004
# Leselampe hinten rechts (Stehlampe mit Schirm)
box("lampenfuss", MESSING, 2.1, 2.3, 1.6, 1.8, 0, 0.03)
box("lampenstange", MESSING, 2.19, 2.21, 1.69, 1.71, 0.03, 1.45)
bpy.ops.mesh.primitive_cone_add(radius1=0.24, radius2=0.14, depth=0.28, location=(2.2, 1.7, 1.55), end_fill_type="NOTHING")
bpy.context.object.data.materials.append(SCHIRM)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(2.2, 1.7, 1.5))
bpy.context.object.data.materials.append(LAMPE)
# Pendelleuchte über dem Tisch (leicht versetzt, sonst steht sie genau im Zenit)
bpy.ops.mesh.primitive_cone_add(radius1=0.32, radius2=0.08, depth=0.22, location=(0.4, 0.3, 2.05), end_fill_type="NOTHING")
bpy.context.object.data.materials.append(MESSING)
bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=0.01, location=(0.4, 0.3, 1.95))
bpy.context.object.data.materials.append(PENDEL)
box("pendel", MESSING, 0.39, 0.41, 0.29, 0.31, 2.16, H)
# Teppich und Tisch (Tischplatte etwas größer als das Brett, Beine)
box("teppich", TEPPICH, -1.6, 1.6, -1.3, 1.3, 0, 0.01)
box("tischplatte", TISCH, -0.75, 0.75, -0.75, 0.75, TABLE - 0.04, TABLE)
for sx in (-1, 1):
    for sy in (-1, 1):
        box("bein", TISCH, sx * 0.65 - 0.04, sx * 0.65 + 0.04, sy * 0.65 - 0.04, sy * 0.65 + 0.04, 0, TABLE - 0.04)

# ---------------------------------------------------------------------------
# Rundum-Kamera und Rendern
# ---------------------------------------------------------------------------

bpy.ops.object.camera_add(location=(0, 0, EYE))
cam = bpy.context.object
cam.data.type = "PANO"
cam.data.panorama_type = "EQUIRECTANGULAR"
# Blickrichtung zur schwarzen Seite (+Y) waagerecht: Bildmitte = +Y
cam.rotation_euler = (math.radians(90), 0, math.radians(180))
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:   # noqa: BLE001
    print("keine GPU:", e)
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
scene.world = world
scene.render.resolution_x = args.size
scene.render.resolution_y = args.size // 2
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "HDR"
out = os.path.abspath(args.out)
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("HDR:", out, os.path.getsize(out) // 1024, "KB")

if args.preview:
    img = bpy.data.images["Render Result"]
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    img.save_render(os.path.abspath(args.preview), scene=scene)
    print("Vorschau:", args.preview)
