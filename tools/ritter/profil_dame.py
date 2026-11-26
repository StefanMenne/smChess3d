# Profile der Ritter-Damen aus absoluten Maßen (Modelleinheiten, Höhe 1) in Anteile der Bounding Box umrechnen:
#   python3 tools/ritter/profil_dame.py [rot]  -> profil_dame.json bzw. profil_dame_rot.json
# Langes Gewand bis zum Boden (Füße verdeckt): robe ab z = 0, Umhang hinten mit back_layers; Zepter rechts schräg
# nach vorn (Stange), Reichsapfel links vor dem Körper (Halbraum).
import json
import os

import sys

# weiß: dame_ritter_blau_44_saum.glb, rot (Schwarz): dame_ritter_rot_43_saum.glb (gleiche Pose, Maße auf wenige mm gleich)
VAR = sys.argv[1] if len(sys.argv) > 1 else "blau"
MN, MX = ((-0.30368, -0.31828), (0.30186, 0.22613)) if VAR == "rot" else ((-0.30280, -0.30993), (0.30131, 0.22498))
OUT = "profil_dame_rot.json" if VAR == "rot" else "profil_dame.json"
cx = (MN[0] + MX[0]) / 2; hx = (MX[0] - MN[0]) / 2; cy = (MN[1] + MX[1]) / 2; hy = (MX[1] - MN[1]) / 2
CX = -0.005   # Körpermitte
f = lambda p, sx=1: [round(sx * (p[0] - CX) / hx, 4), round((p[1] - cy) / hy, 4), p[2]]
C = {"Hips": ((0, -0.02, 0.45), (0, -0.02, 0.55)), "Spine": ((0, -0.02, 0.55), (0, -0.03, 0.64)),
     "Chest": ((0, -0.03, 0.64), (0, -0.03, 0.73)), "Neck": ((0, -0.03, 0.73), (0, -0.05, 0.78)),
     "Head": ((0, -0.05, 0.78), (0, -0.07, 0.97))}
# je Seite x nach außen positiv (rechts gespiegelt)
L = {"Shoulder": ((0.03, -0.03, 0.72), (0.12, -0.03, 0.72)), "Arm": ((0.12, -0.03, 0.72), (0.155, -0.07, 0.63)),
     "ForeArm": ((0.155, -0.07, 0.63), (0.115, -0.17, 0.565)), "Hand": ((0.115, -0.17, 0.565), (0.105, -0.20, 0.56)),
     "UpLeg": ((0.05, -0.02, 0.45), (0.05, -0.045, 0.25)), "Leg": ((0.05, -0.045, 0.25), (0.05, -0.03, 0.06)),
     "Foot": ((0.05, -0.03, 0.06), (0.05, -0.08, 0.015)), "Toe": ((0.05, -0.08, 0.015), (0.05, -0.12, 0.01))}
R = dict(L, **{"Arm": ((0.12, -0.03, 0.72), (0.16, -0.08, 0.63)), "ForeArm": ((0.16, -0.08, 0.63), (0.195, -0.22, 0.585)),
               "Hand": ((0.195, -0.22, 0.585), (0.20, -0.26, 0.58))})
# Zepter: Achse aus den Querschnitten (z 0,22: -0.145|-0.170, z 0,82: -0.224|-0.293), unten bis z 0,04 verlängert
za, zb = 0.15, 0.84   # unterhalb von 0,15 steckt der Zepterfuß im Pelzsaum
ax = lambda z: [round(-0.145 + (z - 0.22) * (-0.079 / 0.60), 4), round(-0.170 + (z - 0.22) * (-0.123 / 0.60), 4), z]
prof = {"center_x": CX,
        "bones_center": {k: [f(a), f(b)] for k, (a, b) in C.items()},
        "bones_side": {k: [f(a), f(b)] for k, (a, b) in L.items()},
        "bones_side_R": {k: [f(a), f(b)] for k, (a, b) in R.items()},
        "leg_top": 0.50, "belly": 0.42,
        "robe": {"zmin": 0.0, "zmax": 0.50, "r0": 0.04, "r1": 0.06},
        "back_layers": [{"z": [0.25, 0.72], "ymin": 0.0, "xmax": 0.25}],
        "props": [
            {"a": ax(0.04), "b": ax(zb), "radius": 0.016, "t_min": (za - 0.04) / (zb - 0.04), "bone": "ForeArm.R",
             "base_bone": "Hips"},                                                                         # Zepter
            {"normal": [0, -1], "d": 0.15, "z": [0.52, 0.63], "x_min": 0.06, "x_max": 0.17, "bone": "ForeArm.L"}]}  # Reichsapfel
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT)
json.dump(prof, open(path, "w"), indent=1)
print("geschrieben", path)
