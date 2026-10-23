"""Pack a Lottie JSON (e.g. a Figma export with base64 images) into a lottie-ios friendly .lottie.

Embedded data: URIs are written out to images/ and referenced by filename, matching the
layout of our After Effects .lottie files. The JSON itself is otherwise left untouched.

usage: python3 pack_lottie.py in.json out.lottie
"""
import base64, json, re, sys, zipfile

src, dst = sys.argv[1], sys.argv[2]
anim = json.load(open(src))
anim_id = "animation"
images = {}
for a in anim.get("assets", []):
    m = re.match(r"data:image/(\w+);base64,(.*)", str(a.get("p", "")), re.S)
    if not m:
        continue
    ext = {"jpeg": "jpg"}.get(m.group(1), m.group(1))
    name = f"{a['id']}.{ext}"
    images[name] = base64.b64decode(m.group(2))
    a.update(u="/images/", p=name, e=0)

hollow = [a["id"] for a in anim.get("assets", []) for l in a.get("layers", []) if "ty" not in l]
if hollow:
    sys.exit(f"hollow layers in precomps {sorted(set(hollow))}: source JSON is already broken")

manifest = {"version": "1", "generator": "pack_lottie.py", "animations": [{"id": anim_id}]}
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifest))
    z.writestr(f"animations/{anim_id}.json", json.dumps(anim, separators=(",", ":")))
    for name, data in images.items():
        z.writestr(f"images/{name}", data)
print(f"wrote {dst}: {len(images)} images")
