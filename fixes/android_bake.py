"""Render chosen layers with lottie-android (Robolectric, via lottie-check) and save them as one transparent PNG.

Use it to bake what only Android draws right:
  - Figma text: Android draws Figma's embedded glyphs (`chars`); lottie-ios uses system fonts, so custom fonts fall
    back to plain sans and glyphs like ₹ vanish.
  - Blur effects (ty 29): lottie-ios ignores them.
The layers are rendered at frame 0 over black and over white, and the alpha is recovered from the pair.

usage: python3 android_bake.py DIR --keep SPEC[,SPEC...] -o out.png [--scale SPEC=PCT] [--fix-tracking]
  SPEC is a root layer ind (11) or asset_id:ind for a layer inside a precomp (asset_8:2). Parents come along.
  --scale SPEC=PCT  hold that layer's scale at PCT (e.g. render pulsing text at 200 for a sharp 2x image)
  --fix-tracking    Figma writes letter spacing in After Effects units (1/1000 em); lottie-android reads it as px*10,
                    so 220 becomes 22 px per letter and the text wraps letter by letter. This converts it and widens
                    the text box so it can't wrap.
Prints "BBOX x y w h": where the PNG sits on the canvas (pixels at the layer's frame-0 placement).
"""
import argparse, copy, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--keep", required=True)
ap.add_argument("-o", "--out", required=True)
ap.add_argument("--scale", action="append", default=[])
ap.add_argument("--fix-tracking", action="store_true")
args = ap.parse_args()
D = Path(args.dir)
_, a0 = K.load(D)


def spec(s):
    return (s.split(":")[0], int(s.split(":")[1])) if ":" in s else (None, int(s))


keep = {}  # asset id (None = root) -> set of inds
for s in args.keep.split(","):
    aid, ind = spec(s)
    keep.setdefault(aid, set()).add(ind)
    if aid:
        keep.setdefault(None, set()).update(L["ind"] for L in a0["layers"] if L.get("refId") == aid)
scales = {spec(s.split("=")[0]): float(s.split("=")[1]) for s in args.scale}

pngs = {}
for bg in ("black", "white"):
    a = copy.deepcopy(a0)
    lists = dict(K.layer_lists(a))
    for aid, inds in keep.items():
        layers = lists[aid]
        by = {L["ind"]: L for L in layers}
        want = set()
        for i in inds:
            q = i
            while q:
                want.add(q); q = by[q].get("parent")
        for i in list(want):
            if by[i].get("tt"):  # keep a matted layer's matte, the layer above it
                k = layers.index(by[i]); want.add(layers[k - 1]["ind"])
        layers[:] = [L for L in layers if L["ind"] in want]
        for L in layers:
            if (aid, L["ind"]) in scales:
                v = scales[(aid, L["ind"])]
                L["ks"]["s"] = {"a": 0, "k": [v, v, 100]}
            if args.fix_tracking and L["ty"] == 5:
                for kf in L["t"]["d"]["k"]:
                    d = kf["s"]
                    d["tr"] = round(d.get("tr", 0) / 1000 * d["s"] * 10)  # must be an int: both players reject floats
                    if "sz" in d:
                        d["sz"] = [d["sz"][0] + 1000, d["sz"][1]]
    a["layers"].append(K.solid_layer(a, 0 if bg == "black" else 1))
    base = K.scratch()
    w = base / "work"
    (w / "animations").mkdir(parents=True)
    shutil.copy(D / "manifest.json", w / "manifest.json")
    if (D / "images").exists():
        shutil.copytree(D / "images", w / "images")
    K.save(w / "animations" / K.anim_path(D).name, a)
    f = base / f"bake-{bg}.lottie"
    K.pack(w, f)
    r = K.check(f)
    if not r.get("android", {}).get("ok"):
        sys.exit(f"Android render failed ({bg}): {r.get('android')}")
    pngs[bg] = sorted(Path(r["out"]).glob("android-f*.png"), key=lambda q: int(q.stem.split("-f")[1]))[0]

print(subprocess.run([K.swift_tool("matte"), str(pngs["black"]), str(pngs["white"]), args.out], check=True, capture_output=True, text=True).stdout.strip())
