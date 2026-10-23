"""Flatten the LED dot-matrix text precomps of Medium_HM_mobile into per-letter image layers.

Each letter group (dozens of vector dots) becomes one image layer that keeps the letter's opacity
keyframes. The precomp's null chain (bounce) and the root precomp layer (flicker) are untouched.

usage: python3 fixes/flatten_led_example.py in.json out.json workdir bin/Rasterize (or ios-harness/.build/release/Rasterize)
"""
import base64, copy, json, subprocess, sys
from pathlib import Path

src, dst, work, rasterizer = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
LED_PRECOMPS = ("asset_3", "asset_4")
CANVAS = 240  # mini comp per letter; the letter is centred in it

anim = json.loads(src.read_text())
assets = {a["id"]: a for a in anim["assets"]}
jobs = []  # (precomp id, group index, mini json path)

for pid in LED_PRECOMPS:
    shape_layer = assets[pid]["layers"][3]
    assert shape_layer["ty"] == 4 and shape_layer["ks"]["s"]["k"] == [100, 100] and shape_layer["ks"]["r"]["k"] == 0
    for gi, group in enumerate(shape_layer["shapes"]):
        g = copy.deepcopy(group)
        tr = g["it"][-1]
        assert tr["ty"] == "tr" and tr["p"]["a"] == 0
        tr["o"] = {"a": 0, "k": 100}  # opacity stays animated on the image layer instead
        px, py = tr["p"]["k"]
        mini = {
            "v": anim["v"], "fr": anim["fr"], "ip": 0, "op": 1, "w": CANVAS, "h": CANVAS, "assets": [],
            "layers": [{
                "ind": 1, "ty": 4, "ip": 0, "op": 1, "st": 0, "shapes": [g],
                "ks": {"p": {"a": 0, "k": [CANVAS / 2 - px, CANVAS / 2 - py]}, "a": {"a": 0, "k": [0, 0]},
                       "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}},
            }],
        }
        path = work / f"{pid}_{gi:02d}.json"
        path.write_text(json.dumps(mini))
        jobs.append((pid, gi, path))

out = subprocess.run([rasterizer, *[str(j[2]) for j in jobs]], capture_output=True, text=True).stdout
bbox = {}
for line in out.splitlines():
    parts = line.split()
    if parts[0] == "BBOX":
        bbox[parts[1]] = tuple(int(v) for v in parts[2:6])
    else:
        sys.exit(f"rasterizer: {line}")

for pid in LED_PRECOMPS:
    precomp = assets[pid]
    shape_layer = precomp["layers"][3]
    sl_p, sl_a = shape_layer["ks"]["p"]["k"], shape_layer["ks"]["a"]["k"]
    image_layers = []
    for gi, group in enumerate(shape_layer["shapes"]):
        path = work / f"{pid}_{gi:02d}.json"
        x, y, w, h = bbox[str(path)]
        px, py = group["it"][-1]["p"]["k"]
        # canvas pixel -> shape-layer local -> shape layer's parent space
        local = (x - CANVAS / 2 + px, y - CANVAS / 2 + py)
        pos = [round(sl_p[0] + local[0] - sl_a[0], 3), round(sl_p[1] + local[1] - sl_a[1], 3)]
        asset_id = f"{pid}_led_{gi:02d}"
        png = path.with_suffix(".png").read_bytes()
        anim["assets"].append({"id": asset_id, "w": w, "h": h, "u": "", "e": 1,
                               "p": "data:image/png;base64," + base64.b64encode(png).decode()})
        image_layers.append({
            "ind": 100 + gi, "ty": 2, "refId": asset_id, "parent": shape_layer["parent"],
            "ip": shape_layer["ip"], "op": shape_layer["op"], "st": shape_layer["st"],
            "ks": {"p": {"a": 0, "k": pos}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]},
                   "r": {"a": 0, "k": 0}, "o": copy.deepcopy(group["it"][-1]["o"])},
        })
    precomp["layers"] = precomp["layers"][:3] + image_layers

dst.write_text(json.dumps(anim, separators=(",", ":")))
print(f"flattened {len(jobs)} letters -> {dst}")
