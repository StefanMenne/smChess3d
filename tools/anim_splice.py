"""Ersetzt die Animationen einer Figur-GLB durch die einer anderen GLB (Zuordnung der Knochen über den Namen)
und übernimmt deren Knoten-Eigenschaften (Extras, z. B. die Schrittlänge "stride").

  python3 tools/anim_splice.py figur.glb animationen.glb ausgabe.glb

Mesh, Skin, Material und Texturen der Figur bleiben byte-genau erhalten; alle alten Animationen (z. B. die von
Mixamo) werden entfernt und ihre Daten aus dem Binärteil gelöscht. Prüft, dass die Ruhelagen der Knochen in
beiden Dateien übereinstimmen, sonst würden die Bewegungen verdreht wirken.
"""
import json
import struct
import sys


def read_glb(path):
    data = open(path, "rb").read()
    magic, _ver, _len = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", path
    off, js, bin_ = 12, None, b""
    while off < len(data):
        n, kind = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + n]
        if kind == 0x4E4F534A:
            js = json.loads(chunk)
        elif kind == 0x004E4942:
            bin_ = chunk
        off += 8 + n
    return js, bin_


def write_glb(path, js, bin_):
    j = json.dumps(js, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    bin_ += b"\0" * (-len(bin_) % 4)
    out = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(j) + 8 + len(bin_))
    out += struct.pack("<II", len(j), 0x4E4F534A) + j + struct.pack("<II", len(bin_), 0x004E4942) + bin_
    open(path, "wb").write(out)


def view_bytes(js, bin_, vi):
    v = js["bufferViews"][vi]
    o = v.get("byteOffset", 0)
    return bin_[o:o + v["byteLength"]]


def main(fig_path, anim_path, out_path):
    fig, fbin = read_glb(fig_path)
    ani, abin = read_glb(anim_path)
    fnode = {n.get("name"): i for i, n in enumerate(fig["nodes"])}

    # Ruhelagen vergleichen
    worst = 0.0
    for n in ani["nodes"]:
        i = fnode.get(n.get("name"))
        if i is None:
            continue
        m = fig["nodes"][i]
        for key, dflt in (("translation", [0, 0, 0]), ("rotation", [0, 0, 0, 1])):
            a, b = n.get(key, dflt), m.get(key, dflt)
            d = max(abs(x - y) for x, y in zip(a, b))
            if key == "rotation":
                d = min(d, max(abs(x + y) for x, y in zip(a, b)))
            worst = max(worst, d)
    print("größte Abweichung der Ruhelagen:", round(worst, 5))
    if worst > 1e-3:
        sys.exit("Ruhelagen passen nicht zusammen – Animation wurde für ein anderes Skelett erzeugt")

    # Alte Animationen und nur von ihnen benutzte Daten entfernen, Binärteil neu packen
    old_acc = {s[k] for a in fig.get("animations", []) for s in a["samplers"] for k in ("input", "output")}
    keep_acc = [i for i in range(len(fig["accessors"])) if i not in old_acc]
    acc_map = {o: n for n, o in enumerate(keep_acc)}
    used_views = sorted({fig["accessors"][i]["bufferView"] for i in keep_acc if "bufferView" in fig["accessors"][i]}
                        | {im["bufferView"] for im in fig.get("images", []) if "bufferView" in im})
    view_map, views, chunks, pos = {}, [], [], 0

    def add_view(view, raw):
        nonlocal pos
        pad = -pos % 16
        chunks.append(b"\0" * pad)
        pos += pad
        v = {k: x for k, x in view.items() if k not in ("byteOffset", "buffer")}
        v.update(buffer=0, byteOffset=pos)
        chunks.append(raw)
        pos += len(raw)
        views.append(v)
        return len(views) - 1

    for vi in used_views:
        view_map[vi] = add_view(fig["bufferViews"][vi], view_bytes(fig, fbin, vi))
    accessors = []
    for i in keep_acc:
        a = dict(fig["accessors"][i])
        if "bufferView" in a:
            a["bufferView"] = view_map[a["bufferView"]]
        accessors.append(a)
    for im in fig.get("images", []):
        if "bufferView" in im:
            im["bufferView"] = view_map[im["bufferView"]]

    def remap(obj, key):
        if key in obj:
            obj[key] = acc_map[obj[key]]

    for m in fig.get("meshes", []):
        for p in m["primitives"]:
            for k in list(p["attributes"]):
                p["attributes"][k] = acc_map[p["attributes"][k]]
            remap(p, "indices")
            for t in p.get("targets", []):
                for k in list(t):
                    t[k] = acc_map[t[k]]
    for s in fig.get("skins", []):
        remap(s, "inverseBindMatrices")

    # Neue Animationen übernehmen
    anims = []
    aview_map = {}
    for a in ani.get("animations", []):
        samplers, channels, smap = [], [], {}
        for c in a["channels"]:
            name = ani["nodes"][c["target"]["node"]].get("name")
            if name not in fnode:
                continue
            si = c["sampler"]
            if si not in smap:
                s = dict(a["samplers"][si])
                for k in ("input", "output"):
                    src = dict(ani["accessors"][s[k]])
                    bv = src["bufferView"]
                    if bv not in aview_map:
                        aview_map[bv] = add_view(ani["bufferViews"][bv], view_bytes(ani, abin, bv))
                    src["bufferView"] = aview_map[bv]
                    accessors.append(src)
                    s[k] = len(accessors) - 1
                samplers.append(s)
                smap[si] = len(samplers) - 1
            channels.append({"sampler": smap[si], "target": {"node": fnode[name], "path": c["target"]["path"]}})
        anims.append({"name": a["name"], "samplers": samplers, "channels": channels})
        print(f"  {a['name']}: {len(channels)} Kanäle")

    # Eigenschaften der Knoten (glTF-Extras, z. B. "stride" am Skelett) übernehmen
    for n in ani["nodes"]:
        i = fnode.get(n.get("name"))
        if i is not None and n.get("extras"):
            fig["nodes"][i].setdefault("extras", {}).update(n["extras"])
            print(f"  Extras {n['name']}: {n['extras']}")

    fig["accessors"], fig["bufferViews"], fig["animations"] = accessors, views, anims
    bin_new = b"".join(chunks)
    fig["buffers"] = [{"byteLength": len(bin_new) + (-len(bin_new) % 4)}]
    write_glb(out_path, fig, bin_new)
    print("geschrieben", out_path, f"({pos / 1e6:.2f} MB Daten)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
