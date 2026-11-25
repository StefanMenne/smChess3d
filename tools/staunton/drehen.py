"""Staunton-Figuren als Rotationskörper (gedrechselt), mit gebackener Holzmaserung, als GLB.

  (Blender) drehen.py OUT_DIR [--only bauer,turm] [--knight springer_kopf.glb] [--tex 2048] [--preview lineup.png]

Jede Figur ist ein Profil (Radius über der Höhe, in Feldbreiten), das um die senkrechte Achse gedreht wird;
nicht rotationssymmetrische Teile kommen als kleine Zusatzkörper dazu (Zinnen des Turms als Schnitte, Schlitz
der Läufer-Mitra, Zacken der Damenkrone, Kreuz des Königs). Der Springer bekommt einen gedrechselten Sockel;
sein Kopf kommt aus --knight (aus image_to_3d, siehe LIESMICH.md), dessen Textur verworfen wird.

Holz: prozedurale 3D-Maserung (Jahresringe um eine weit seitlich liegende Achse, also fast gerade, senkrechte
Streifen wie bei längs gemasertem Holz, mit Verwirbelung), mit Cycles in eine Farbtextur gebacken. Weil die
Maserung räumlich ist, laufen die Streifen über UV-Nähte und zwischen Sockel und Springerkopf durch.
Weiß: Buchsbaum, Schwarz: Ebenholz/Palisander. Ergebnis: OUT_DIR/<art>_<weiss|schwarz>.glb, Fußpunkt im
Ursprung, Höhe in Feldbreiten, vorn = -Y (glTF +Z).
"""
import argparse
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--only", default="")
p.add_argument("--knight", default="")
p.add_argument("--tex", type=int, default=2048)
p.add_argument("--preview", default="")
p.add_argument("--segments", type=int, default=96)
args = p.parse_args(sys.argv[1:])
args.out = os.path.abspath(args.out)
os.makedirs(args.out, exist_ok=True)

# ---------------------------------------------------------------------------
# Profile: Liste von Segmenten ab (0, 0) unten in der Mitte bis r = 0 oben
#   ("L", r, z)              Strecke
#   ("Q", cr, cz, r, z)      quadratische Bezierkurve mit Kontrollpunkt
#   ("A", cz, R, a1)         Kreisbogen um (0, cz) mit Radius R bis zum Winkel a1 (Grad, 90 = oben)
# ---------------------------------------------------------------------------


DZ = 0.05   # der Fuß ist um so viel höher als in der ersten Fassung; alles darüber rückt nach oben


def base(r):
    """Klassischer Staunton-Fuß (Podest): senkrechte Fußplatte mit gerundeter Kante, Stufe, großer Wulst,
    Kehle und kleiner Rundstab; endet bei (r - 0.09, 0.19), dort setzt der Körper der Figur an."""
    return [("L", r, 0.0), ("L", r, 0.05), ("Q", r, 0.068, r - 0.018, 0.068), ("L", r - 0.035, 0.068),
            ("Q", r - 0.008, 0.075, r - 0.01, 0.105), ("Q", r - 0.012, 0.135, r - 0.05, 0.14),
            ("L", r - 0.07, 0.15), ("Q", r - 0.052, 0.158, r - 0.058, 0.172),
            ("Q", r - 0.062, 0.186, r - 0.09, 0.19)]


def up(segs, dz=DZ):
    """Profilteile über dem Fuß um dz anheben."""
    out = []
    for s in segs:
        if s[0] == "L":
            out.append(("L", s[1], s[2] + dz))
        elif s[0] == "Q":
            out.append(("Q", s[1], s[2] + dz, s[3], s[4] + dz))
        else:
            out.append(("A", s[1] + dz, s[2], s[3]))
    return out


def collar(r, z, h=0.035):
    """Kragen: zwei Wülste übereinander."""
    return [("L", r * 0.82, z), ("Q", r, z, r, z + h * 0.5), ("Q", r, z + h, r * 0.86, z + h),
            ("Q", r * 0.95, z + h * 1.1, r * 0.95, z + h * 1.5), ("Q", r * 0.95, z + h * 2, r * 0.6, z + h * 2)]


PROFILES = {
    # Bauer: Kugelkopf auf schlankem Schaft
    "bauer": base(0.33) + up([("Q", 0.15, 0.17, 0.125, 0.32), ("Q", 0.10, 0.45, 0.10, 0.50)]
    + collar(0.19, 0.50, 0.03) + [("L", 0.09, 0.565), ("A", 0.715, 0.16, 90)]),
    # Turm: leicht konischer Rumpf, ausladender Kranz, hohl mit Boden
    "turm": base(0.36) + up([("Q", 0.25, 0.17, 0.235, 0.26), ("L", 0.21, 0.62), ("Q", 0.20, 0.70, 0.25, 0.74),
                          ("L", 0.27, 0.76), ("L", 0.27, 1.0), ("L", 0.205, 1.0), ("L", 0.205, 0.90),
                          ("L", 0.0, 0.90)]),
    # Läufer: Mitra (Ei) auf Kragen, kleine Kugel oben
    "laeufer": base(0.36) + up([("Q", 0.17, 0.18, 0.14, 0.36), ("Q", 0.09, 0.56, 0.10, 0.66)]
    + collar(0.20, 0.66, 0.035) + [("L", 0.10, 0.74), ("Q", 0.20, 0.82, 0.175, 0.98),
                                   ("Q", 0.15, 1.10, 0.04, 1.19), ("L", 0.03, 1.20), ("A", 1.245, 0.05, 90)]),
    # Dame: Kelch mit Zackenkrone, Kuppel und Kugel
    "dame": base(0.38) + up([("Q", 0.18, 0.18, 0.15, 0.38), ("Q", 0.10, 0.64, 0.105, 0.76)]
    + collar(0.21, 0.76, 0.035) + [("L", 0.10, 0.84), ("Q", 0.10, 1.05, 0.21, 1.22), ("L", 0.225, 1.24),
                                   ("L", 0.20, 1.27), ("Q", 0.17, 1.30, 0.13, 1.30),
                                   ("Q", 0.12, 1.40, 0.035, 1.41), ("A", 1.455, 0.05, 90)]),
    # König: wie die Dame, höher, mit Kuppel; das Kreuz kommt als eigener Körper dazu
    "koenig": base(0.39) + up([("Q", 0.19, 0.18, 0.155, 0.40), ("Q", 0.105, 0.70, 0.11, 0.84)]
    + collar(0.22, 0.84, 0.035) + [("L", 0.105, 0.92), ("Q", 0.10, 1.12, 0.20, 1.27), ("L", 0.215, 1.29),
                                   ("L", 0.19, 1.31), ("Q", 0.20, 1.40, 0.07, 1.43), ("L", 0.045, 1.44),
                                   ("L", 0.0, 1.44)]),
    # Springer: nur der Sockel, oben flach (der Kopf sitzt darauf)
    "springer": base(0.37) + up([("Q", 0.25, 0.16, 0.235, 0.20)] + collar(0.27, 0.20, 0.03) + [("L", 0.0, 0.26)]),
}


def profile_points(segs, step=0.006):
    pts = [(0.0, 0.0)]
    for s in segs:
        r0, z0 = pts[-1]
        if s[0] == "L":
            _, r, z = s
            n = max(1, int(math.hypot(r - r0, z - z0) / 0.05))   # Strecken: wenige Punkte (Kanten bleiben scharf)
            pts += [(r0 + (r - r0) * i / n, z0 + (z - z0) * i / n) for i in range(1, n + 1)]
        elif s[0] == "Q":
            _, cr, cz, r, z = s
            length = math.hypot(cr - r0, cz - z0) + math.hypot(r - cr, z - cz)
            n = max(4, int(length / step))
            for i in range(1, n + 1):
                t = i / n
                pts.append(((1 - t) ** 2 * r0 + 2 * (1 - t) * t * cr + t * t * r,
                            (1 - t) ** 2 * z0 + 2 * (1 - t) * t * cz + t * t * z))
        else:   # Kreisbogen
            _, cz, R, a1 = s
            a0 = math.degrees(math.atan2(z0 - cz, r0))
            n = max(6, int(abs(math.radians(a1 - a0)) * R / step))
            for i in range(1, n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                pts.append((max(0.0, R * math.cos(a)), cz + R * math.sin(a)))
    pts[-1] = (0.0, pts[-1][1])
    return pts


def lathe(name, pts, segments):
    """Dreht das Profil um Z; Punkte mit r = 0 werden zu einem Pol."""
    bm = bmesh.new()
    rings = []
    for r, z in pts:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segments),
                                        r * math.sin(2 * math.pi * k / segments), z)) for k in range(segments)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for k in range(segments):
            k1 = (k + 1) % segments
            if len(a) == 1:
                bm.faces.new((a[0], b[k1], b[k]))
            elif len(b) == 1:
                bm.faces.new((a[k], a[k1], b[0]))
            else:
                bm.faces.new((a[k], a[k1], b[k1], b[k]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def box(name, size, loc, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 3
        bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def sphere(name, r, loc):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    ob = bpy.context.object
    ob.name = name
    return ob


def cut(target, cutter):
    m = target.modifiers.new("cut", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter)


def join(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def knight_head(path, base_top):
    """Kopf aus image_to_3d (nach glb_post: Fuß bei z = 0, Höhe 1): drehen, den generierten Sockel unterhalb von
    KNIGHT_CUT abschneiden, das Loch schließen, auf Sockelmaß skalieren und auf den gedrechselten Sockel setzen."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    head = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for o in new:
        if o != head and o.name in bpy.data.objects:
            bpy.data.objects.remove(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    head.data.materials.clear()
    bm = bmesh.new()
    bm.from_mesh(head.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, KNIGHT_CUT), plane_no=(0, 0, 1), clear_inner=True)
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
    ring = [v.co.copy() for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]
    centre = sum(ring, Vector()) / len(ring)
    # Schnauze nach vorn (-Y); KNIGHT_YAW dreht bei Bedarf um Z
    m = Matrix.Translation((0, 0, base_top - 0.005)) @ Matrix.Scale(KNIGHT_SCALE, 4) \
        @ Matrix.Rotation(math.radians(KNIGHT_YAW), 4, "Z") @ Matrix.Translation((-centre.x, -centre.y, -KNIGHT_CUT))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(head.data)
    bm.free()
    dec = head.modifiers.new("dec", "DECIMATE")
    dec.ratio = KNIGHT_FACES / max(1, len(head.data.polygons))
    bpy.context.view_layer.objects.active = head
    if dec.ratio < 1:
        bpy.ops.object.modifier_apply(modifier=dec.name)
    else:
        head.modifiers.remove(dec)
    return head


KNIGHT_CUT = 0.29      # Höhe (Anteil) über dem Fuß des generierten Modells, wo der Kopf beginnt
KNIGHT_SCALE = 1.4     # Kopf passend zum Sockel (Radius 0,37 statt 0,25 im generierten Modell)
KNIGHT_YAW = 45.0        # Vorlage in Dreiviertelansicht: Schnauze nach glb_post 45° schräg, so genau nach vorn
KNIGHT_FACES = 40000


# ---------------------------------------------------------------------------
# Holz
# ---------------------------------------------------------------------------

WOODS = {   # Grundfarben (linear) hell/dunkel, Rauheit
    "weiss": ((0.80, 0.61, 0.36), (0.68, 0.48, 0.25), 0.38),
    "schwarz": ((0.030, 0.017, 0.011), (0.075, 0.040, 0.024), 0.28),
}


def wood_material(color, seed):
    """Längsmaserung: Rauschen, quer fein und längs (Z) stark gestreckt, dazu großflächige Farbschwankung."""
    light, dark, rough = WOODS[color]
    mat = bpy.data.materials.new(f"holz_{color}_{seed}")
    mat.use_nodes = True
    nt = mat.node_tree
    n = nt.nodes
    n.clear()
    links = nt.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    coord = n.new("ShaderNodeTexCoord")

    def noise(scale, detail, rough_, offset):
        mp = n.new("ShaderNodeMapping")
        mp.inputs["Location"].default_value = (offset, -offset, 0.37 * offset)
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Rotation"].default_value = (0.04, 0.02 * (seed % 3 - 1), 0.0)
        nz = n.new("ShaderNodeTexNoise")
        nz.inputs["Detail"].default_value = detail
        nz.inputs["Roughness"].default_value = rough_
        links.new(coord.outputs["Object"], mp.inputs["Vector"])
        links.new(mp.outputs["Vector"], nz.inputs["Vector"])
        return nz.outputs["Fac"]

    fine = noise((70.0, 70.0, 3.0), 8.0, 0.62, 1.3 * seed)     # feine Fasern längs
    broad = noise((9.0, 9.0, 1.2), 3.0, 0.5, 2.1 * seed + 5)   # breitere Streifen
    blot = noise((2.5, 2.5, 2.5), 2.0, 0.5, 3.7 * seed + 9)    # Farbschwankung
    m1 = n.new("ShaderNodeMix")
    m1.data_type = "FLOAT"
    m1.inputs["Factor"].default_value = 0.45
    links.new(fine, m1.inputs["A"])
    links.new(broad, m1.inputs["B"])
    m2 = n.new("ShaderNodeMix")
    m2.data_type = "FLOAT"
    m2.inputs["Factor"].default_value = 0.3
    links.new(m1.outputs["Result"], m2.inputs["A"])
    links.new(blot, m2.inputs["B"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = 0.36
    ramp.color_ramp.elements[0].color = (*light, 1)
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = (*dark, 1)
    links.new(m2.outputs["Result"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def bake_wood(ob, color, seed, size):
    """Prozedurales Holz in eine Farbtextur backen und das Material darauf umstellen."""
    mat = wood_material(color, seed)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new(f"{ob.name}_farbe", size, size)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.nodes.active = tex
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8)
    # Material für den Export: nur Bild, Rauheit
    nt = mat.node_tree
    bsdf = next(x for x in nt.nodes if x.type == "BSDF_PRINCIPLED")
    for x in list(nt.nodes):
        if x not in (bsdf, tex) and x.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(x)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    img.pack()


# ---------------------------------------------------------------------------
# Figuren bauen
# ---------------------------------------------------------------------------

def build(kind):
    ob = lathe(kind, profile_points(PROFILES[kind]), args.segments)
    if kind == "turm":
        # vier Zinnenlücken: zwei Kästen kreuzweise durch den Kranz
        for rot in (0, math.pi / 2):
            cut(ob, box("luecke", (0.8, 0.10, 0.26), (0, 0, 1.05 + DZ), (0, 0, rot)))
    elif kind == "laeufer":
        # schräger Schlitz in der Mitra, von vorn bis etwas über die Mitte
        cut(ob, box("schlitz", (0.5, 0.26, 0.03), (0, -0.13, 1.0 + DZ), (0, math.radians(-40), 0)))
    elif kind == "dame":
        pts = [sphere("zacke", 0.03, (0.215 * math.cos(a), 0.215 * math.sin(a), 1.262 + DZ))
               for a in (2 * math.pi * k / 8 + math.pi / 8 for k in range(8))]
        ob = join([ob] + pts)
    elif kind == "koenig":
        cross = box("kreuz_s", (0.06, 0.06, 0.24), (0, 0, 1.55 + DZ))
        bar = box("kreuz_q", (0.17, 0.06, 0.06), (0, 0, 1.585 + DZ))
        m = cross.modifiers.new("u", "BOOLEAN")
        m.operation, m.solver, m.object = "UNION", "EXACT", bar
        bpy.context.view_layer.objects.active = cross
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(bar)
        bv = cross.modifiers.new("bevel", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.01, 3, "ANGLE"
        bpy.ops.object.modifier_apply(modifier=bv.name)
        ob = join([ob, cross])
    elif kind == "springer" and args.knight:
        head = knight_head(args.knight, 0.26 + DZ)
        ob = join([ob, head])
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    return ob


scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 16
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:   # noqa: BLE001
    print("keine GPU:", e)

kinds = [k for k in PROFILES if not args.only or k in args.only.split(",")]
if "springer" in kinds and not args.knight:
    print("springer: ohne --knight nur der Sockel")
done = []
for i, kind in enumerate(kinds):
    shape = build(kind)
    for j, color in enumerate(("weiss", "schwarz")):
        bpy.ops.object.select_all(action="DESELECT")
        shape.select_set(True)
        bpy.context.view_layer.objects.active = shape
        bpy.ops.object.duplicate()
        ob = bpy.context.object
        ob.name = f"{kind}_{color}"
        ob.data = ob.data.copy()
        bake_wood(ob, color, 2 * i + j, args.tex)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        path = os.path.join(args.out, f"{kind}_{color}.glb")
        bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_image_format="JPEG",
                                  export_jpeg_quality=90)
        dims = ob.dimensions
        print(f"{ob.name}: {len(ob.data.polygons)} Flächen, Höhe {dims.z:.3f}, Breite {dims.x:.3f}/{dims.y:.3f}")
        done.append(ob)
    bpy.data.objects.remove(shape)

if args.preview:
    # Aufstellung: Weiß vorn, Schwarz dahinter, Kamera schräg von vorn oben
    for k, ob in enumerate(done):
        col = k // 2
        ob.location = (col * 0.85 - (len(done) // 2 - 1) * 0.425, 0.0 if ob.name.endswith("weiss") else 1.0, 0)
    bpy.ops.mesh.primitive_plane_add(size=30)
    floor = bpy.context.object
    fm = bpy.data.materials.new("boden")
    fm.diffuse_color = (0.35, 0.33, 0.31, 1)
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.30, 0.28, 1)
    floor.data.materials.append(fm)
    bpy.ops.object.light_add(type="AREA", location=(-3, -4, 6))
    lamp = bpy.context.object
    lamp.data.energy = 900
    lamp.data.size = 4
    lamp.rotation_euler = (math.radians(40), 0, math.radians(-35))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    bpy.ops.object.camera_add(location=(0, -7.8, 3.4))
    cam = bpy.context.object
    cam.data.lens = 46
    direction = Vector((0, 0.45, 0.65)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 1800, 900
    scene.cycles.samples = 96
    scene.render.filepath = os.path.abspath(os.path.join(args.out, args.preview))
    bpy.ops.render.render(write_still=True)
    print("Vorschau:", scene.render.filepath)
