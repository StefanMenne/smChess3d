# Profile der Ritter-Läufer aus absoluten Maßen (Modelleinheiten, Höhe 1) in Anteile der Bounding Box umrechnen.
#   python3 tools/ritter/profil_laeufer.py            -> profil_laeufer.json (weiß/blau, laeufer_ritter_42_quelle.glb)
#   python3 tools/ritter/profil_laeufer.py rot        -> profil_laeufer_rot.json (schwarz/rot, laeufer_ritter_rot_42_*)
# Beide Modelle stammen aus derselben Pose (Seed 42); das rote steht in y um DY weiter vorn (glb_post zentriert die
# Bounding Box, die ohne die abstehende Stange hinten kürzer ist). Hammer und Buch sind je Modell eigens vermessen.
import json
import os
import sys

VAR = sys.argv[1] if len(sys.argv) > 1 else "blau"
if VAR == "rot":
    MN, MX, DY = (-0.30644, -0.39612), (0.30644, 0.06476), -0.055
    # Stielachse (beim Abschneiden der Stange vermessen): Punkt C + t * D
    C, D = (-0.022, 0.2789, 0.5612), (0.2952, 0.9067, 0.3012)
    on = lambda t: [round(C[i] + t * D[i], 4) for i in range(3)]
    PROPS = [
        {"normal": [0, -1], "d": 0.12, "z": [0.10, 0.37], "x_max": -0.14, "bone": "ForeArm.R"},   # Hammerkopf
        {"a": on(-0.62), "b": on(-0.33), "radius": 0.02, "t_min": 0.0, "bone": "ForeArm.R"},       # Stiel bis Faust
        {"normal": [0, -1], "d": 0.195, "z": [0.43, 0.575], "x_min": 0.07, "x_max": 0.17, "bone": "ForeArm.L"}]  # Buch
    OUT = "profil_laeufer_rot.json"
else:
    MN, MX, DY = (-0.30322, -0.39580), (0.30322, 0.09717), 0.0
    PROPS = [
        {"normal": [0, -1], "d": 0.19, "z": [0.10, 0.43], "x_max": -0.14, "bone": "ForeArm.R"},
        {"a": [-0.215, -0.215, 0.34], "b": [-0.175, -0.10, 0.47], "radius": 0.02, "t_min": 0.0, "bone": "ForeArm.R"},
        {"normal": [0, -1], "d": 0.165, "z": [0.435, 0.58], "x_min": 0.07, "x_max": 0.17, "bone": "ForeArm.L"}]
    OUT = "profil_laeufer.json"

cx = (MN[0] + MX[0]) / 2; hx = (MX[0] - MN[0]) / 2; cy = (MN[1] + MX[1]) / 2; hy = (MX[1] - MN[1]) / 2
f = lambda p, sx=1: [round(sx * (p[0] - cx) / hx, 4), round((p[1] + DY - cy) / hy, 4), p[2]]
C_ = {"Hips": ((0.02, -0.09, 0.42), (0.01, -0.09, 0.52)), "Spine": ((0.01, -0.09, 0.52), (0, -0.09, 0.62)),
      "Chest": ((0, -0.09, 0.62), (0, -0.08, 0.72)), "Neck": ((0, -0.08, 0.72), (0.005, -0.09, 0.77)),
      "Head": ((0.005, -0.09, 0.77), (0.01, -0.10, 0.99))}
L = {"Shoulder": ((0.03, -0.08, 0.72), (0.13, -0.08, 0.72)), "Arm": ((0.13, -0.08, 0.72), (0.21, -0.12, 0.57)),
     "ForeArm": ((0.21, -0.12, 0.57), (0.18, -0.18, 0.47)), "Hand": ((0.18, -0.18, 0.47), (0.17, -0.22, 0.46)),
     "UpLeg": ((0.11, -0.09, 0.42), (0.12, -0.115, 0.24)), "Leg": ((0.12, -0.115, 0.24), (0.13, -0.10, 0.07)),
     "Foot": ((0.13, -0.10, 0.07), (0.13, -0.17, 0.02)), "Toe": ((0.13, -0.17, 0.02), (0.13, -0.22, 0.01))}
R = {"Shoulder": ((-0.03, -0.08, 0.72), (-0.12, -0.08, 0.72)), "Arm": ((-0.12, -0.08, 0.72), (-0.16, -0.08, 0.57)),
     "ForeArm": ((-0.16, -0.08, 0.57), (-0.175, -0.08, 0.465)), "Hand": ((-0.175, -0.08, 0.465), (-0.18, -0.12, 0.44)),
     "UpLeg": ((-0.04, -0.09, 0.42), (-0.045, -0.115, 0.24)), "Leg": ((-0.045, -0.115, 0.24), (-0.05, -0.10, 0.07)),
     "Foot": ((-0.05, -0.10, 0.07), (-0.05, -0.17, 0.02)), "Toe": ((-0.05, -0.17, 0.02), (-0.05, -0.22, 0.01))}
prof = {"center_x": cx,
        "bones_center": {k: [f(a), f(b)] for k, (a, b) in C_.items()},
        "bones_side": {k: [f(a), f(b)] for k, (a, b) in L.items()},
        "bones_side_R": {k: [f(a, -1), f(b, -1)] for k, (a, b) in R.items()},
        "leg_top": 0.40, "belly": 0.33,
        "back_layers": [{"z": [0.30, 0.70], "ymin": round(-0.04 + DY, 4), "xmax": 0.23},
                        {"z": [0.42, 0.70], "ymin": round(-0.09 + DY, 4), "xmax": 0.13}],
        "robe": {"zmin": 0.075, "zmax": 0.40, "r0": 0.05, "r1": 0.075},
        "props": PROPS}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT)
json.dump(prof, open(path, "w"), indent=1)
print("geschrieben", path)
