# Profil des Ritter-Springers (springer_ritter_blau_45.glb: Ritter mit Pferdekopf-Helmzier, Lanze rechts, Schild
# links) aus absoluten Maßen (Modelleinheiten, Höhe 1) in Anteile der Bounding Box:
#   python3 tools/ritter/profil_springer.py      -> profil_springer.json (weiß/blau, springer_ritter_blau_45.glb)
#   python3 tools/ritter/profil_springer.py rot  -> profil_springer_rot.json (schwarz/rot, springer_ritter_rot_42.glb)
# Beide Modelle haben dieselbe Pose (rot per edit_image aus Bild 2112); Körper und Schild liegen gleich, beim roten
# sitzt der Kopf 2 cm weiter hinten und die Lanze ist in Handhöhe leicht geknickt (zwei Abschnitte).
import json
import os
import sys

VAR = sys.argv[1] if len(sys.argv) > 1 else "blau"
if VAR == "rot":
    MN, MX, HY = (-0.27670, -0.18467), (0.27670, 0.18467), 0.02
    LANZE = [{"a": [-0.145, -0.163, 0.03], "b": [-0.187, -0.170, 0.55], "radius": 0.022, "t_min": -0.1,
              "bone": "ForeArm.R"},
             {"a": [-0.187, -0.170, 0.55], "b": [-0.236, -0.142, 1.0], "radius": 0.022, "t_min": 0.0,
              "bone": "ForeArm.R"}]
    OUT = "profil_springer_rot.json"
else:
    MN, MX, HY = (-0.27750, -0.19853), (0.27750, 0.19853), 0.0
    LANZE = [{"a": [-0.1493, -0.1381, 0.0], "b": [-0.2355, -0.1688, 1.0], "radius": 0.022, "t_min": -0.02,
              "bone": "ForeArm.R"}]
    OUT = "profil_springer.json"
hx, hy = MX[0], MX[1]
CX = 0.0
fs = lambda p, sx=1: [round(sx * (p[0] - CX) / hx, 4), round(p[1] / hy, 4), p[2]]
C = {"Hips": ((0.0, 0.0, 0.42), (0.0, 0.0, 0.52)), "Spine": ((0.0, 0.0, 0.52), (0.0, 0.01, 0.61)),
     "Chest": ((0.0, 0.01, 0.61), (0.0, 0.02, 0.71)), "Neck": ((0.0, 0.02, 0.71), (0.0, 0.02 + HY, 0.77)),
     "Head": ((0.0, 0.02 + HY, 0.77), (0.0, 0.02 + HY, 1.0))}
L = {"Shoulder": ((0.03, 0.02, 0.70), (0.12, 0.02, 0.70)), "Arm": ((0.12, 0.02, 0.70), (0.15, 0.0, 0.57)),
     "ForeArm": ((0.15, 0.0, 0.57), (0.15, -0.05, 0.47)), "Hand": ((0.15, -0.05, 0.47), (0.15, -0.07, 0.45)),
     "UpLeg": ((0.07, 0.0, 0.42), (0.07, -0.02, 0.23)), "Leg": ((0.07, -0.02, 0.23), (0.07, 0.03, 0.07)),
     "Foot": ((0.07, 0.03, 0.07), (0.08, -0.02, 0.02)), "Toe": ((0.08, -0.02, 0.02), (0.09, -0.06, 0.01))}
R = {"Shoulder": ((-0.03, 0.02, 0.70), (-0.12, 0.02, 0.70)), "Arm": ((-0.12, 0.02, 0.70), (-0.16, 0.0, 0.58)),
     "ForeArm": ((-0.16, 0.0, 0.58), (-0.18, -0.12, 0.50)), "Hand": ((-0.18, -0.12, 0.50), (-0.19, -0.15, 0.49)),
     "UpLeg": ((-0.07, 0.0, 0.42), (-0.0775, -0.02, 0.23)), "Leg": ((-0.0775, -0.02, 0.23), (-0.085, 0.0, 0.07)),
     "Foot": ((-0.085, 0.0, 0.07), (-0.09, -0.06, 0.02)), "Toe": ((-0.09, -0.06, 0.02), (-0.09, -0.11, 0.01))}
prof = {"center_x": CX,
        "bones_center": {k: [fs(a), fs(b)] for k, (a, b) in C.items()},
        "bones_side": {k: [fs(a), fs(b)] for k, (a, b) in L.items()},
        "bones_side_R": {k: [fs(a, -1), fs(b, -1)] for k, (a, b) in R.items()},
        "leg_top": 0.42, "belly": 0.35,
        # Umhang hinten (Beine enden hinten bei y = 0,12): Schichten am Rücken gemeinsam, unten ab 9 cm nur Hüfte
        "back_layers": [{"z": [0.45, 0.72], "ymin": 0.03, "xmax": 0.14}],
        "robe": {"zmin": 0.10, "zmax": 0.42, "r0": 0.07, "r1": 0.10},
        "split_robe": {"zmax": 0.20},
        "props": LANZE + [{"normal": [1, 0], "d": 0.165, "z": [0.24, 0.67], "bone": "ForeArm.L"}]}   # Schild
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT)
json.dump(prof, open(path, "w"), indent=1)
print("geschrieben", path)
