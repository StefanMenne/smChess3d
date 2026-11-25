"""GB10-Kette (blender-Tool, code=diese Datei): glb_post -> tex_eyes (Augen finden) -> tex_eyecover -> eye_geo.

  args: prep.glb out_prefix [--eyes-json eyes.json] [--cover-opts "..."] [--geo-opts "..."] [--find-opts "..."] [--skip-cover]
  schreibt <prefix>_post.glb, <prefix>_eyes.json, <prefix>_found.glb (gemalte Augen markiert), <prefix>_eyes.glb

Ruft die mitgelieferten Skripte des Servers (/app/tools/blender/scripts) per runpy auf.
"""
import argparse
import runpy
import shlex
import sys

S = "/app/tools/blender/scripts/"
sys.path.insert(0, S)

p = argparse.ArgumentParser(prog="eyes_chain")
p.add_argument("src")
p.add_argument("prefix")
p.add_argument("--find-opts", default="")
p.add_argument("--cover-opts", default="")
p.add_argument("--geo-opts", default="")
p.add_argument("--skip-cover", action="store_true")
p.add_argument("--eyes-json", default=None, help="Augen aus dieser Datei statt tex_eyes (exakt reproduzierbar / von Hand)")
a = p.parse_args(sys.argv[1:])


def run(name, *args):
    print(f"[chain] {name} {' '.join(args)}", flush=True)
    sys.argv = [name + ".py", *args]
    try:
        runpy.run_path(S + name + ".py", run_name="__main__")
    except SystemExit as e:
        if e.code:
            raise


P = a.prefix
run("glb_post", a.src, f"{P}_post.glb", "--emission", "0", "--tex", "1024")
if a.eyes_json:
    import shutil
    shutil.copy(a.eyes_json, f"{P}_eyes.json")
else:
    run("tex_eyes", f"{P}_post.glb", f"{P}_found.glb", "--style", "black", "--save-eyes", f"{P}_eyes.json",
        *shlex.split(a.find_opts))
print("[chain] eyes:", open(f"{P}_eyes.json").read())
src = f"{P}_post.glb"
if not a.skip_cover:
    run("tex_eyecover", src, f"{P}_cov.glb", "--eyes", f"{P}_eyes.json", *shlex.split(a.cover_opts))
    src = f"{P}_cov.glb"
run("eye_geo", src, f"{P}_eyes.glb", "--eyes", f"{P}_eyes.json", *shlex.split(a.geo_opts))
