"""Eigene Bewegungen (Idle, WalkInPlace) und Schrittlänge für die geschnitzten Figuren, ganz ohne Mixamo-Daten.

  blender -b --python tools/anim_figur.py -- figur.glb anim_out.glb [--stride 1.83] [--frames 22]

Für jede Figur mit dem Menschen-Skelett aus rig_figur.py (Hips, UpLeg.L, ... Toe.R). Alle Längen sind am
Bauern (Beinlänge 0,284) eingestellt und werden mit der Beinlänge der Figur skaliert; --stride ist der Weg pro
Doppelschritt in Beinlängen.

Die Bewegungen werden prozedural erzeugt: Füße als IK-Ziele mit festem Bodenkontakt (Fersenaufsatz, Abrollen
über den Ballen, Schwungbogen), Hüfte mit Heben/Senken, Seitenpendeln und Drehung, Oberkörper gegengedreht,
Kopf ruhig, Arme pendeln leicht (Speer- und Schildarm verhalten). Die Beine löst eine eigene Zwei-Knochen-IK
ohne Verdrehung; gespeichert werden reine FK-Keys. Exportiert wird nur das Skelett mit den zwei Aktionen
und der Schrittlänge als Eigenschaft "stride" (Hüftweg pro Zyklus in Figurenhöhen, Extras des Skelett-Knotens);
tools/anim_splice.py setzt sie in die Figur ein, ohne Mesh und Material anzufassen.

Konventionen (Blender): oben = +Z, vorn = -Y, Figur links = +X. 24 Bilder/s. Drehung um +X mit positivem
Winkel kippt nach vorn (Oberkörper) bzw. schwingt nach hinten (hängende Knochen: Beine, Arme).
"""
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
opt = dict(zip(argv[2::2], argv[3::2]))
STRIDE_LEGS = float(opt.get("--stride", 1.83))   # Weg pro Doppelschritt (Hüfte) in Beinlängen
CYCLE = int(opt.get("--frames", 22))         # Bilder pro Doppelschritt
IDLE = 192                                  # Bilder Idle (8 s)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene
sc.render.fps = 24
# Figurenhöhe (Mesh in Ruhelage), auf die das Spiel die Schrittlänge bezieht
# (nur geriggte Meshes: der glTF-Import legt zusätzlich eine Kugel als Knochenform an)
_zs = [(o.matrix_world @ v.co).z for o in sc.objects
       if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers) for v in o.data.vertices]
FIG_HEIGHT = max(_zs) - min(_zs)
for o in list(sc.objects):
    if o.type != "ARMATURE":
        bpy.data.objects.remove(o)
arm = [o for o in sc.objects if o.type == "ARMATURE"][0]
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
arm.animation_data_clear()
bones = arm.data.bones
P = arm.pose.bones
for pb in P:
    pb.rotation_mode = "QUATERNION"

REST = {b.name: b.matrix_local.copy() for b in bones}
RQ = {n: m.to_quaternion() for n, m in REST.items()}
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
rad = math.radians


def rot(name, *axis_angles):
    """Lokale Drehung eines Knochens aus Drehungen um Achsen des Armature-Raums (in Grad, nacheinander)."""
    q = Quaternion()
    for axis, deg in axis_angles:
        q = Quaternion(axis, rad(deg)) @ q
    return RQ[name].inverted() @ q @ RQ[name]


def key_rot(name, f, q):
    P[name].rotation_quaternion = q
    P[name].keyframe_insert("rotation_quaternion", frame=f)


def key_hips(f, delta, q):
    P["Hips"].location = RQ["Hips"].inverted() @ delta
    P["Hips"].keyframe_insert("location", frame=f)
    key_rot("Hips", f, q)


# ------------------------------------------------------------------ Maße
ankle = {s: REST[f"Foot.{s}"].translation.copy() for s in "LR"}
ball = {s: REST[f"Toe.{s}"].translation.copy() for s in "LR"}
hipj = {s: REST[f"UpLeg.{s}"].translation.copy() for s in "LR"}
LEG = (bones["UpLeg.L"].length + bones["Leg.L"].length)
K = LEG / 0.284                     # Maßstab gegenüber dem Bauern
STRIDE = STRIDE_LEGS * LEG
# Größter Abstand Hüftgelenk-Knöchel beim Gehen: knapp unter gestreckt. Bei fast gestreckten Beinen beugt schon
# 1 cm weniger das Knie um 20° und mehr – an den Beinen gewichtete Röcke bauschen sich dann
REACH = 0.985 * LEG
print("Beinlänge", round(LEG, 3), "Schritt", round(STRIDE_LEGS * LEG, 3), "Hüftgelenk-Knöchel", round((hipj["L"] - ankle["L"]).length, 3))

# ------------------------------------------------------------------ Bein-IK (eigene, ohne Verdrehung)
# Blenders IK-Solver legt die Drehung der Beinknochen um ihre Längsachse über einen Polwinkel fest; bei manchen
# Figuren bleibt dabei eine Verdrehung von 70° und mehr, die an den Beinen gewichtete Röcke und Mäntel
# zusammenwickelt. Hier wird jeder Beinknochen nur geschwenkt (kürzeste Drehung von seiner mitgetragenen
# Ruherichtung zur Zielrichtung): keine Verdrehung, das Knie bleibt in der Ebene von Hüfte, Ziel und Vorwärtsrichtung.
L1 = {s: (REST[f"Leg.{s}"].translation - REST[f"UpLeg.{s}"].translation).length for s in "LR"}
L2 = {s: (REST[f"Foot.{s}"].translation - REST[f"Leg.{s}"].translation).length for s in "LR"}
pending = {}
KNEE_DIR = {}
for s_ in "LR":
    h_, k_, a_ = (REST[f"{b}.{s_}"].translation for b in ("UpLeg", "Leg", "Foot"))
    d_ = (a_ - h_).normalized()
    off_ = (k_ - h_) - d_ * (k_ - h_).dot(d_)
    KNEE_DIR[s_] = off_.normalized() if off_.length > 0.01 * (L1[s_] + L2[s_]) else None
print("Kniebeugung aus der Ruhelage:", {k: (tuple(round(x, 2) for x in v) if v else "vorn") for k, v in KNEE_DIR.items()})


def set_foot(s, f, pos, pitch, toe):
    """Knöchelziel, Fußneigung (Grad, + = Zehen hoch) und Zehenknick (+ = Zehen hoch relativ zum Fuß)."""
    pending[s] = (pos, pitch)
    key_rot(f"Toe.{s}", f, rot(f"Toe.{s}", (X, -toe)))


def carried(name, parent_matrix, parent):
    """Pose-Matrix eines Knochens, wenn er gegenüber seinem (gestellten) Elternknochen in Ruhelage bleibt."""
    return parent_matrix @ REST[parent].inverted() @ REST[name]


def aim(name, child, M, target_dir):
    """Matrix M so schwenken (um ihren Kopf), dass die Strecke zum Kopf des Kindknochens nach target_dir zeigt.
    Nicht die Knochenachse: bei unverbundenen Knochen liegt das nächste Gelenk neben ihr."""
    head = M.translation.copy()
    q = M.to_quaternion()
    seg = q @ (RQ[name].inverted() @ (REST[child].translation - REST[name].translation))
    swing = seg.normalized().rotation_difference(target_dir.normalized())
    out = (swing @ q).to_matrix().to_4x4()
    out.translation = head
    return out


def solve_legs(f):
    """Beine eines Bildes lösen und keyen. Alles analytisch aus den gerade gesetzten Hüft-Werten, ohne
    Depsgraph-Update (das würde die Keys des Bildes erneut auswerten und die neuen Werte überschreiben)."""
    Mh = REST["Hips"] @ P["Hips"].matrix_basis
    hips_rot = Mh.to_quaternion() @ RQ["Hips"].inverted()
    fwd = hips_rot @ Vector((0, -1, 0))
    for s in "LR":
        T, pitch = pending[s]
        C1 = carried(f"UpLeg.{s}", Mh, "Hips")
        H = C1.translation
        l1, l2 = L1[s], L2[s]
        d = T - H
        dist = min(d.length, (l1 + l2) * 0.9995)
        dn = d.normalized()
        # Knie: in der Ebene aus Hüfte-Ziel und Beugerichtung. Ist das Bein schon in der Ruhelage deutlich gebeugt
        # (Dame: Knie 2 cm hinter der Linie Hüfte-Knöchel), in diese Richtung, sonst nach vorn – ein Durchknicken
        # zur anderen Seite beugte das Knie schon im Stand um 30° und mehr
        bend = hips_rot @ KNEE_DIR[s] if KNEE_DIR[s] is not None else fwd
        side = bend - dn * bend.dot(dn)
        side.normalize()
        a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
        h = math.sqrt(max(l1 * l1 - a * a, 0.0))
        knee = H + dn * a + side * h
        M1 = aim(f"UpLeg.{s}", f"Leg.{s}", C1, knee - H)
        C2 = carried(f"Leg.{s}", M1, f"UpLeg.{s}")
        M2 = aim(f"Leg.{s}", f"Foot.{s}", C2, (H + dn * dist) - knee)
        C3 = carried(f"Foot.{s}", M2, f"Leg.{s}")
        M3 = (Quaternion(X, rad(-pitch)) @ RQ[f"Foot.{s}"]).to_matrix().to_4x4()
        M3.translation = C3.translation
        for name, C, M in ((f"UpLeg.{s}", C1, M1), (f"Leg.{s}", C2, M2), (f"Foot.{s}", C3, M3)):
            P[name].rotation_quaternion = (C.inverted() @ M).to_quaternion()
            P[name].keyframe_insert("rotation_quaternion", frame=f)


def smooth(t):
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ Gang
G = min(1.0, STRIDE_LEGS / 1.83)    # kleine Schritte (lange Gewänder): weniger Hub, Abrollen und Hüftbewegung
STANCE = 0.62                       # Anteil Standphase
LIFT = 0.055 * K * (0.4 + 0.6 * G)  # Fußhub im Schwung
HEEL = 14.0 * G                     # Zehen hoch beim Aufsetzen
ROLL = 32.0 * G                     # Ferse hoch beim Abstoßen (Drehung um den Ballen)


def foot_state(s, ph, root):
    """Knöchel, Neigung, Zehenknick eines Fußes bei Phase ph (0 = Fersenaufsatz) und Vorwärtsweg root der Hüfte."""
    ph %= 1.0
    half = STANCE * STRIDE / 2
    a, b = ankle[s], ball[s]
    if ph < STANCE:
        u = ph / STANCE
        # Fuß steht fest: Position in Weltkoordinaten = Aufsatzpunkt
        land_root = root - u * STANCE * STRIDE
        y = -(land_root + half)            # vorn = -Y
        pitch, toe = 0.0, 0.0
        if u < 0.15:                       # Fersenaufsatz -> Fuß flach
            pitch = HEEL * (1 - smooth(u / 0.15))
        elif u > 0.62:                     # Abrollen über den Ballen
            pitch = -ROLL * smooth((u - 0.62) / 0.38)
            toe = -pitch
        pos = Vector((a.x, a.y + y, a.z))
        if pitch < 0:                      # Ferse hebt sich: Knöchel dreht um den Ballen
            off = a - b
            pos = Vector((b.x, b.y + y, b.z)) + Quaternion(X, rad(-pitch)) @ off
        elif pitch > 0:                    # Zehen hoch: Knöchel dreht um die Ferse (etwas unter/hinter dem Knöchel)
            heel = Vector((a.x, a.y + 0.03 * K, a.z - 0.045 * K))
            pos = Vector((heel.x, heel.y + y, heel.z)) + Quaternion(X, rad(-pitch)) @ (a - heel)
        return pos, pitch, toe
    u = (ph - STANCE) / (1 - STANCE)
    start_root = root - (ph - STANCE) * STRIDE    # Hüftweg beim Abheben
    y0 = -(start_root - half)                     # Fuß hinten
    y1 = -(root + (1 - ph) * STRIDE + half)       # nächster Aufsatzpunkt
    y = y0 + (y1 - y0) * smooth(u)
    # Anfang des Schwungs schließt an das Abrollen an: Ferse noch oben, Knöchel um den Ballen gedreht
    k = 1 - smooth(min(u / 0.4, 1))
    rolled = (Vector((b.x, b.y, b.z)) + Quaternion(X, rad(ROLL)) @ (a - b)) - a
    pitch = -ROLL * k + HEEL * smooth(max((u - 0.55) / 0.45, 0))
    z = a.z + LIFT * math.sin(math.pi * u) ** 1.3
    pos = Vector((a.x, a.y + y, z)) + rolled * k
    return pos, pitch, ROLL * k + 6 * math.sin(math.pi * u)


def make_walk(name, in_place):
    act = bpy.data.actions.new(name)
    arm.animation_data_create().action = act
    for f in range(0, CYCLE + 1):
        t = f / CYCLE
        root = t * STRIDE
        w = 2 * math.pi * t
        # Hüfte: tief bei Doppelstand (t = 0, 0.5), hoch in der Mitte des Einbeinstands
        bob = (-0.022 * (0.5 + 0.5 * math.cos(2 * w)) + 0.004) * K * G
        sway = 0.014 * K * math.sin(w + 0.4)                  # zum Standbein (links bei t ~ 0.25)
        yaw = 4.5 * G * math.cos(w)                           # Becken dreht mit dem vorderen Bein
        roll = -2.0 * math.sin(w + 0.4)
        fwd = 0.0 if in_place else root
        feet = {s: foot_state(s, t + (0.5 if s == "R" else 0.0), root) for s in "LR"}
        # erreichbar halten: Hüftgelenk nie weiter als REACH vom Knöchelziel
        hz = bob
        for s in "LR":
            pos = feet[s][0]
            j = hipj[s] + Vector((sway, -root, 0))
            d = Vector((pos.x - j.x, pos.y - j.y))
            reach = math.sqrt(max(REACH ** 2 - d.length_squared, 0.0)) + pos.z
            hz = min(hz, reach - j.z)
        key_hips(f, Vector((sway, -fwd, hz)), rot("Hips", (X, 3.0 * G), (Y, roll), (Z, yaw)))
        for s in "LR":
            pos, pitch, toe = feet[s]
            if in_place:
                pos = pos + Vector((0, root, 0))
            else:
                pos = pos.copy()
            set_foot(s, f, pos, pitch, toe)
        key_rot("Spine", f, rot("Spine", (Z, -0.5 * yaw), (Y, -0.4 * roll)))
        key_rot("Chest", f, rot("Chest", (Z, -0.6 * yaw), (X, 1.0 + 0.8 * math.cos(2 * w))))
        key_rot("Neck", f, rot("Neck", (Z, 0.1 * yaw)))
        key_rot("Head", f, rot("Head", (X, 0.6 * math.cos(2 * w)), (Y, 0.5 * roll)))
        # Arme gegengleich zu den Beinen; rechts Speer, links Schild: kleiner Ausschlag, Unterarm schwingt nach
        sw = math.cos(w)                                   # +1: linkes Bein vorn -> rechter Arm vorn
        key_rot("Arm.R", f, rot("Arm.R", (X, -7 * sw)))
        key_rot("ForeArm.R", f, rot("ForeArm.R", (X, -3 * math.cos(w - 0.6))))
        key_rot("Arm.L", f, rot("Arm.L", (X, 5 * sw)))
        key_rot("ForeArm.L", f, rot("ForeArm.L", (X, 2 * math.cos(w - 0.6))))
        for b in ("Shoulder.L", "Shoulder.R", "Hand.L", "Hand.R"):
            key_rot(b, f, Quaternion())
        solve_legs(f)
    return act


def make_idle():
    act = bpy.data.actions.new("Idle")
    arm.animation_data_create().action = act
    for f in range(0, IDLE + 1, 2):
        t = f / IDLE
        w = 2 * math.pi * t
        breath = math.sin(2 * w * 2)                     # 4 Atemzüge in 8 s
        shift = math.sin(w) + 0.25 * math.sin(2 * w)     # langsames Gewichtverlagern
        look = 9 * math.sin(w + 1.0) * (0.6 + 0.4 * math.sin(3 * w)) # Umsehen
        key_hips(f, Vector((0.010 * shift, 0, -0.002 - 0.002 * abs(shift) + 0.0015 * breath)) * K,
                 rot("Hips", (X, 1.0), (Y, -1.2 * shift), (Z, 1.5 * math.sin(w + 0.5))))
        for s in "LR":
            set_foot(s, f, ankle[s].copy(), 0.0, 0.0)
        key_rot("Spine", f, rot("Spine", (Y, 0.8 * shift), (X, -0.6 * breath)))
        key_rot("Chest", f, rot("Chest", (X, -1.2 * breath), (Y, 0.4 * shift)))
        key_rot("Neck", f, rot("Neck", (Z, 0.35 * look)))
        key_rot("Head", f, rot("Head", (Z, 0.65 * look), (X, 2.0 * math.sin(2 * w + 0.3)), (Y, -0.5 * shift)))
        for s, sg in (("L", 1), ("R", -1)):
            key_rot(f"Shoulder.{s}", f, rot(f"Shoulder.{s}", (Y, sg * 0.8 * breath)))
            key_rot(f"Arm.{s}", f, rot(f"Arm.{s}", (X, 1.5 * math.sin(w + (0 if s == "L" else 2))), (Y, sg * 0.8 * breath)))
            key_rot(f"ForeArm.{s}", f, rot(f"ForeArm.{s}", (X, -1.0 * math.sin(w + 0.7))))
            key_rot(f"Hand.{s}", f, Quaternion())
        solve_legs(f)
    return act


acts = [make_idle(), make_walk("WalkInPlace", True)]
for act in acts:
    act.use_fake_user = True

# Kontrolle mit Vorwärtsweg: Fußgleiten in der Standphase (Ballen in Weltkoordinaten, sollte fest stehen) und
# Hüftweg pro Zyklus. Dieser Clip wird nicht exportiert: das Spiel bewegt die Figur selbst und braucht nur die
# Schrittlänge, die als Eigenschaft "stride" (in Figurenhöhen) am Skelett-Knoten mitgeht
check = make_walk("WalkCheck", False)
if hasattr(arm.animation_data, "action_slot") and check.slots:
    arm.animation_data.action_slot = check.slots[0]
track = []
for f in range(CYCLE + 1):
    sc.frame_set(f)
    track.append((arm.matrix_world @ P["Toe.L"].head).copy())
print("Ballen L (y, z) je Bild:", " ".join(f"{v.y:.3f}/{v.z:.3f}" for v in track))
sc.frame_set(CYCLE)
print("Hüftweg pro Zyklus:", round(-(arm.matrix_world @ P["Hips"].head).y + REST["Hips"].translation.y, 3))
arm.animation_data.action = None
bpy.data.actions.remove(check)
for pb in P:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), Quaternion(), (1, 1, 1)
arm["stride"] = round(STRIDE / FIG_HEIGHT, 5)
print("stride", arm["stride"], "Figurenhöhen (Höhe", round(FIG_HEIGHT, 3), ")")

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=False, export_animations=True,
                          export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                          export_optimize_animation_size=False, export_skins=True, export_def_bones=False,
                          export_extras=True)
print("geschrieben", OUT, [a.name for a in acts])
