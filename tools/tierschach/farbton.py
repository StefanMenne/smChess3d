"""Hauptfarbe in der Basistextur umfärben (z. B. Wolle auf das Springer-Braun): Pixel mit Farbton in [h0,h1], Sättigung >= smin, Helligkeit <= vmax
werden auf Zielfarbton/-sättigung gezogen (Helligkeit bleibt, mal vfac). --dump schreibt nur die Textur als PNG.

  blender -b --factory-startup --python tools/tierschach/farbton.py -- in.glb out.glb [--h 22,46] [--smin 0.58]
          [--smax 1] [--vmin 0] [--vmax 0.72] [--to-h 19] [--sfac 0.66] [--vfac 1.1] [--mask maske.png] | --dump textur.png
Werte prüfen: Median der braunen Pixel in views.py-Renderings vergleichen (Springer schwarz: H19 S0.53 V0.44).
"""
import bpy, sys, numpy as np, argparse
a=argparse.ArgumentParser(); [a.add_argument(x) for x in ("src","dst")]
a.add_argument("--h", default="22,46"); a.add_argument("--smin", type=float, default=0.45); a.add_argument("--smax", type=float, default=1.0); a.add_argument("--vmin", type=float, default=0.0); a.add_argument("--vmax", type=float, default=0.85)
a.add_argument("--to-h", type=float, default=19); a.add_argument("--sfac", type=float, default=0.66); a.add_argument("--vfac", type=float, default=1.0)
a.add_argument("--dump", action="store_true"); a.add_argument("--mask", default=None)
o=a.parse_args(sys.argv[sys.argv.index("--")+1:])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=o.src)
img=None
for m in bpy.data.materials:
    if not m.node_tree: continue
    b=next((n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED"),None)
    l=b.inputs["Base Color"].links if b else []
    if l and l[0].from_node.type=="TEX_IMAGE": img=l[0].from_node.image
w,h=img.size; px=np.array(img.pixels[:],dtype=np.float32).reshape(h,w,4)
if o.dump:
    out=bpy.data.images.new("d",w,h); out.pixels=px.ravel(); out.filepath_raw=o.dst; out.file_format="PNG"; out.save(); print("[farbton] dump",w,h); sys.exit()
# sRGB-Werte: Blender liefert für Byte-Bilder sRGB-kodierte pixels? -> Bild-Farbraum prüfen
print("[farbton] colorspace", img.colorspace_settings.name)
rgb=px[...,:3]; mx=rgb.max(-1); mn=rgb.min(-1); d=mx-mn+1e-6
r,g,b_=rgb[...,0],rgb[...,1],rgb[...,2]
hh=np.where(mx==r,((g-b_)/d)%6,np.where(mx==g,(b_-r)/d+2,(r-g)/d+4))*60
s=np.where(mx>0,d/np.maximum(mx,1e-6),0); v=mx
h0,h1=[float(x) for x in o.h.split(",")]
sel=(hh>=h0)&(hh<=h1)&(s>=o.smin)&(s<=o.smax)&(v>=o.vmin)&(v<=o.vmax)
print("[farbton] Pixel gewählt", sel.sum(), "von", sel.size)
nh=np.full_like(hh,o.to_h); ns=np.clip(s*o.sfac,0,1); nv=np.clip(v*o.vfac,0,1)
hp=nh/60; c=nv*ns; x=c*(1-np.abs(hp%2-1)); m_=nv-c
z=np.zeros_like(c); k=(np.floor(hp).astype(int))%6
parts=[(c,x,z),(x,c,z),(z,c,x),(z,x,c),(x,z,c),(c,z,x)]
new=np.zeros(c.shape+(3,),np.float32)
for i,(a1,a2,a3) in enumerate(parts):
    mk=k==i; new[mk]=np.stack([a1[mk],a2[mk],a3[mk]],-1)
new+=m_[...,None]
rgb[sel]=new[sel]; px[...,:3]=rgb
img.pixels=px.ravel(); img.update()
if o.mask:
    mk=np.zeros((h,w,4),np.float32); mk[...,3]=1; mk[sel,0]=1; mk[sel,1]=1; mk[sel,2]=1
    mi=bpy.data.images.new("m",w,h); mi.pixels=mk.ravel(); mi.filepath_raw=o.mask; mi.file_format="PNG"; mi.save()
img.pack()
bpy.ops.export_scene.gltf(filepath=o.dst, export_format="GLB")
print("[farbton] OUT", o.dst)
