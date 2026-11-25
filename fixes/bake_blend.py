"""Bake a blend-mode layer into a normal image layer, so it looks right on lottie-ios's Core Animation engine
(which ignores blend modes; the Main Thread engine and lottie-android honour some of them).

The layers below the target are rendered at frame 0 as a static backdrop (lottie-ios, via Rasterize). The
target is rendered alone. The image keeps the target's alpha and gets the blended colour, so drawing it normally
over the backdrop gives the blended result. Bake from the bottom up when several layers blend.

usage: python3 bake_blend.py DIR IND [--mode MODE]
  IND   root layer index (must be static, with no children)
  MODE  defaults to the layer's own bm: multiply, screen, overlay, darken, lighten, hardlight
Everything below IND must be static, or it gets frozen into the image where the layer covers it. Move animated
layers that sit under the blend above it first, if they don't overlap anything in between.
"""
import argparse, base64, copy, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

MODES = {1: "multiply", 2: "screen", 3: "overlay", 4: "darken", 5: "lighten", 8: "hardlight"}
ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("ind", type=int)
ap.add_argument("--mode")
args = ap.parse_args()
D, IND = Path(args.dir), args.ind
p, a = K.load(D)
byind = {L["ind"]: L for L in a["layers"]}
T = byind[IND]
mode = args.mode or MODES.get(T.get("bm", 0))
if not mode:
    sys.exit(f"layer {IND} has bm {T.get('bm', 0)}; pass --mode")
assert not any(L.get("parent") == IND for L in a["layers"]), "layer has children"
assert not T.get("tt") and not T.get("td"), "layer is matted or a matte"
assert not K.animated(T["ks"]), "layer transform is animated"
tmp = K.scratch()


def embedded_assets():
    out = []
    for x in copy.deepcopy(a["assets"]):
        if x.get("p") and not x["p"].startswith("data:"):
            x["p"] = "data:image/png;base64," + base64.b64encode((D / "images" / x["p"]).read_bytes()).decode()
            x["u"], x["e"] = "", 1
        out.append(x)
    return out


def render(inds, name):
    keep = set(inds)
    for i in inds:
        q = byind[i].get("parent")
        while q:
            keep.add(q); q = byind[q].get("parent")
    for i in list(keep):
        if byind[i].get("tt"):
            k = a["layers"].index(byind[i]); keep.add(a["layers"][k - 1]["ind"])
    m = dict(a)
    m["layers"] = [copy.deepcopy(L) for L in a["layers"] if L["ind"] in keep]
    for L in m["layers"]:
        L["ip"], L["op"] = 0, 1
        if L["ind"] == IND:
            L["bm"] = 0
    m["assets"], m["ip"], m["op"] = embedded_assets(), 0, 1
    f = tmp / f"{name}.json"; f.write_text(json.dumps(m))
    out = subprocess.run([K.rasterize_bin(), str(f)], capture_output=True, text=True).stdout.split()
    i = out.index("BBOX")
    return f.with_suffix(".png"), tuple(int(v) for v in out[i + 2:i + 6])


order = [L["ind"] for L in a["layers"]]
below = order[order.index(IND) + 1:]
bpng, bb = render(below, "backdrop")
assert bb == (0, 0, a["w"], a["h"]), f"backdrop doesn't cover the canvas {bb}; blend needs an opaque backdrop"
lpng, (x, y, w, h) = render([IND], "layer")
aid = f"blend_{IND}"
subprocess.run([K.swift_tool("blend"), str(bpng), str(lpng), str(x), str(y), mode, str(D / "images" / f"{aid}.png")], check=True)
T.pop("parent", None)
K.image_layer(T, aid, x, y, opacity={"a": 0, "k": 100})
K.add_image_asset(a, aid, w, h)
K.drop_unused_assets(D, a)
K.save(p, a)
print(f"baked layer {IND} ({mode}) at {x},{y} {w}x{h} over {len(below)} layers")
