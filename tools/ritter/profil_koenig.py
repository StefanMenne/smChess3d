# Profil des Ritter-Königs (koenig_ritter_blau_44_gerade.glb: Fahnenstange unten geradegerichtet, Figur mit
# stange_richten.py --boden 1 auf die Sohlen abgesenkt) aus absoluten Maßen in Anteile der Bounding Box:
#   python3 tools/ritter/profil_koenig.py
# Die Maße unten stammen vom Modell vor dem Absenken (Stangenspitze z = 0, Höhe 1); Z() rechnet sie um: um DZ
# abgesenkt, neue Höhe H1 (Sohlen auf z = 0, Fahnenspitze oben).
# Rechte Hand hält die Fahnenstange, die Fahne weht hinter dem Kopf (starr mit der Stange), links hängt das Schwert.
import json
import os
import sys

VAR = sys.argv[1] if len(sys.argv) > 1 else "blau"
MN, MX = (-0.26605, -0.14274), (0.26605, 0.14274)
OUT = "profil_koenig.json"
cx = (MN[0] + MX[0]) / 2; hx = (MX[0] - MN[0]) / 2; cy = (MN[1] + MX[1]) / 2; hy = (MX[1] - MN[1]) / 2
CX = 0.01
DZ, H1 = 0.0507, 0.94933
Z = lambda z: round(max(0.0, (z - DZ) / H1), 4)
f = lambda p: [round((p[0] - CX) / hx, 4), round((p[1] - cy) / hy, 4), Z(p[2])]
fs = lambda p, sx: [round(sx * (p[0] - CX) / hx, 4), round((p[1] - cy) / hy, 4), Z(p[2])]
C = {"Hips": ((0.01, -0.02, 0.48), (0.01, -0.02, 0.56)), "Spine": ((0.01, -0.02, 0.56), (0.01, -0.025, 0.64)),
     "Chest": ((0.01, -0.025, 0.64), (0.01, -0.03, 0.71)), "Neck": ((0.01, -0.03, 0.71), (0.015, -0.04, 0.76)),
     "Head": ((0.015, -0.04, 0.76), (0.02, -0.045, 0.92))}
# absolute x-Werte; links (+x) und rechts (-x) getrennt, weil die Figur nicht symmetrisch steht
L = {"Shoulder": ((0.04, -0.02, 0.70), (0.15, -0.02, 0.69)), "Arm": ((0.15, -0.02, 0.69), (0.19, -0.03, 0.567)),
     "ForeArm": ((0.19, -0.03, 0.567), (0.17, -0.10, 0.46)), "Hand": ((0.17, -0.10, 0.46), (0.165, -0.12, 0.44)),
     "UpLeg": ((0.08, -0.01, 0.48), (0.11, -0.04, 0.27)), "Leg": ((0.11, -0.04, 0.27), (0.13, -0.02, 0.087)),
     "Foot": ((0.13, -0.02, 0.087), (0.135, -0.07, 0.02)), "Toe": ((0.135, -0.07, 0.02), (0.135, -0.115, 0.01))}
R = {"Shoulder": ((-0.02, -0.02, 0.70), (-0.13, -0.02, 0.69)), "Arm": ((-0.13, -0.02, 0.69), (-0.18, 0.0, 0.607)),
     "ForeArm": ((-0.18, 0.0, 0.607), (-0.205, -0.065, 0.595)), "Hand": ((-0.205, -0.065, 0.595), (-0.215, -0.085, 0.59)),
     "UpLeg": ((-0.04, -0.01, 0.48), (-0.05, -0.035, 0.27)), "Leg": ((-0.05, -0.035, 0.27), (-0.055, 0.005, 0.087)),
     "Foot": ((-0.055, 0.005, 0.087), (-0.055, -0.05, 0.02)), "Toe": ((-0.055, -0.05, 0.02), (-0.055, -0.09, 0.01))}
prof = {"center_x": CX,
        "bones_center": {k: [f(a), f(b)] for k, (a, b) in C.items()},
        "bones_side": {k: [fs(a, 1), fs(b, 1)] for k, (a, b) in L.items()},
        "bones_side_R": {k: [fs(a, -1), fs(b, -1)] for k, (a, b) in R.items()},
        "leg_top": Z(0.48), "belly": Z(0.40),
        # gepanzerte Beine (Schienen bis 6 cm um die Achse): nur der Umhang folgt der Hüfte – hinter den Beinen
        # (Waden enden hinten bei y = 0,055 bzw. 0,073, der Umhang beginnt bei 0,097) und an den Seiten (weiter als 9–12 cm von den Beinknochen)
        "to_hips": [{"zmin": Z(0.10), "zmax": Z(0.42), "ymin": 0.08}],
        "robe": {"zmin": Z(0.10), "zmax": Z(0.50), "r0": 0.09 / H1, "r1": 0.12 / H1},
        # Rücken: ab 0,40 gemittelt (stufenloser Übergang zur Hüftzone), unter 0,50 nur hinter den Beinen
        "back_layers": [{"z": [Z(0.40), Z(0.50)], "ymin": 0.08, "xmax": 0.22},
                        {"z": [Z(0.50), Z(0.72)], "ymin": 0.0, "xmax": 0.22, "arm_r": 0.06 / H1}],
        "props": [
            # Fahnenstange: Fuß nach dem Stauchen bei (-0.161 | 0.024) auf dem Boden, oben wie zuvor
            {"a": [-0.161, 0.024, 0.0], "b": [-0.251, -0.131, 1.0], "radius": 0.02, "t_min": -0.05, "bone": "ForeArm.R"},
            {"outside": {"center": [0.02, -0.04], "radius": 0.065}, "z": [Z(0.775), 1.01], "bone": "ForeArm.R"},
            {"outside": {"center": [0.02, -0.02], "radius": 0.16}, "z": [Z(0.745), Z(0.775)], "bone": "ForeArm.R"},
            {"a": [0.267, -0.055, Z(0.20)], "b": [0.167, -0.11, Z(0.455)], "radius": 0.013, "t_min": -0.06,
             "bone": "ForeArm.L"}]}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT)
json.dump(prof, open(path, "w"), indent=1)
print("geschrieben", path)
