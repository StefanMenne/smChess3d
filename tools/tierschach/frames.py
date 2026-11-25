# Frames einer Aktion eng gerahmt rendern: seitlich (von +X) und schräg vorn, als Raster
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--")+1:]
src, out, action, frames = a[0], a[1], a[2], [int(x) for x in a[3].split(",")]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
arm = next(o for o in sc.objects if o.type == 'ARMATURE')
act = bpy.data.actions[action]
arm.animation_data_create(); arm.animation_data.action = act
if hasattr(arm.animation_data, "action_slot") and act.slots: arm.animation_data.action_slot = act.slots[0]
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.88, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3; sun.rotation_euler = (0.8, 0.2, 0.6); sc.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); cam.data.type = "ORTHO"; cam.data.ortho_scale = 1.3; sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = sc.render.resolution_y = 420; sc.view_settings.view_transform = "Standard"
import os, tempfile
tmp = out; os.makedirs(tmp, exist_ok=True); paths = []
views = {"seite": ((3, 0, 0.47), (math.radians(90), 0, math.radians(90))), "vorn": ((1.8, -2.4, 1.0), (math.radians(75), 0, math.radians(37)))}
for f in frames:
    sc.frame_set(f)
    for vn, (loc, rot) in views.items():
        cam.location = loc; cam.rotation_euler = rot
        p = f"{tmp}/{vn}_{f}.png"; sc.render.filepath = p; bpy.ops.render.render(write_still=True); paths.append((vn, f, p))
print("FRAMES", tmp)
