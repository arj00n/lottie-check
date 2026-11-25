"""Replace static shape layers (Figma halftone textures, dot grids, outlined text) with image layers rendered by
lottie-ios (Rasterize). Each layer keeps its own transform and opacity animation, parent, and matte flags. Static
masks are baked into the image. Byte-identical results share one image file.

usage: python3 flatten_shapes.py DIR [--min-paths N] [--scale K] [--max-area A]
  --min-paths N   only layers with at least N vector paths (default 20)
  --scale K       render at K x the canvas, e.g. 3 for a 1x (360-wide) export, so images stay sharp on 3x phones
  --max-area A    skip layers whose bounds exceed A px^2 (default 1440*900)
Layers with animated shapes or an animated anchor are skipped. With --scale != 1 a flattened layer must have no children.
"""
import argparse, copy, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--min-paths", type=int, default=20)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--max-area", type=float, default=1440 * 900)
args = ap.parse_args()
D, S = Path(args.dir), args.scale
p, a = K.load(D)
work = K.scratch()


def paths(s):
    n = 0
    for x in s:
        if x["ty"] == "gr":
            n += paths(x["it"])
        elif x["ty"] in ("sh", "rc", "el", "sr"):
            n += 1
    return n


def bounds(items, m=(1, 0, 0, 1, 0, 0), acc=None):
    acc = acc if acc is not None else [1e9, 1e9, -1e9, -1e9]
    tr = next((x for x in items if x["ty"] == "tr"), None)
    if tr:
        px, py = tr["p"]["k"][:2]; ax, ay = tr["a"]["k"][:2]; sx, sy = (v / 100 for v in tr["s"]["k"][:2]); r = math.radians(tr["r"]["k"])
        cs, sn = math.cos(r), math.sin(r)
        g = (cs * sx, sn * sx, -sn * sy, cs * sy)
        g = g + (px - (g[0] * ax + g[2] * ay), py - (g[1] * ax + g[3] * ay))
        a0, b0, c0, d0, e0, f0 = m
        m = (a0 * g[0] + c0 * g[1], b0 * g[0] + d0 * g[1], a0 * g[2] + c0 * g[3], b0 * g[2] + d0 * g[3], a0 * g[4] + c0 * g[5] + e0, b0 * g[4] + d0 * g[5] + f0)
    for x in items:
        pts = []
        if x["ty"] == "gr":
            bounds(x["it"], m, acc)
        elif x["ty"] == "sh":
            k = x["ks"]["k"]
            pts = list(k["v"]) + [[v[0] + i[0], v[1] + i[1]] for v, i in zip(k["v"], k["i"])] + [[v[0] + o[0], v[1] + o[1]] for v, o in zip(k["v"], k["o"])]
        elif x["ty"] in ("el", "rc"):
            (cx, cy), (w, h) = x["p"]["k"][:2], x["s"]["k"][:2]
            pts = [[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx - w / 2, cy + h / 2], [cx + w / 2, cy + h / 2]]
        for vx, vy in pts:
            X = m[0] * vx + m[2] * vy + m[4]; Y = m[1] * vx + m[3] * vy + m[5]
            acc[0] = min(acc[0], X); acc[1] = min(acc[1], Y); acc[2] = max(acc[2], X); acc[3] = max(acc[3], Y)
    return acc


targets, skipped, layers_of = [], {"anim": 0, "big": 0, "matte": 0, "few": 0}, {}
for _, layers in K.layer_lists(a):
    for L in layers:
        if L["ty"] != 4:
            continue
        if L.get("td"):
            skipped["matte"] += 1; continue
        if paths(L["shapes"]) < args.min_paths:
            skipped["few"] += 1; continue
        if K.animated(L["shapes"]) or L["ks"].get("a", {}).get("a", 0) == 1:
            skipped["anim"] += 1; continue
        x0, y0, x1, y1 = bounds(L["shapes"])
        if (x1 - x0) * (y1 - y0) > args.max_area:
            skipped["big"] += 1; continue
        targets.append((L, (x0, y0, x1, y1))); layers_of[id(L)] = layers
print("flattening", len(targets), "layers,", sum(paths(L["shapes"]) for L, _ in targets), "paths; skipped", skipped)
if not targets:
    sys.exit(0)

MARGIN = 60
jobs = []
for i, (L, (x0, y0, x1, y1)) in enumerate(targets):
    M = copy.deepcopy(L)
    bake = bool(L.get("masksProperties")) and not K.animated(L["masksProperties"])
    for k in ("parent", "tt", "td", "tp") + (() if bake else ("masksProperties", "hasMask")):
        M.pop(k, None)
    if bake:
        L.pop("masksProperties"); L.pop("hasMask", None)
    M.update(ind=1, ip=0, op=1, st=0)
    M["ks"] = {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "s": {"a": 0, "k": [S * 100, S * 100, 100]},
               "a": {"a": 0, "k": [0, 0, 0]}, "p": {"a": 0, "k": [(MARGIN - x0) * S, (MARGIN - y0) * S, 0]}}
    mini = {"v": a["v"], "fr": a["fr"], "ip": 0, "op": 1, "w": int((x1 - x0 + 2 * MARGIN) * S), "h": int((y1 - y0 + 2 * MARGIN) * S), "assets": [], "layers": [M]}
    f = work / f"L{i:03d}.json"; f.write_text(json.dumps(mini))
    jobs.append((L, f, (MARGIN - x0) * S, (MARGIN - y0) * S))

out = subprocess.run([K.rasterize_bin(), *[str(j[1]) for j in jobs]], capture_output=True, text=True).stdout
bbox = {}
for line in out.splitlines():
    f = line.split()
    if f and f[0] == "BBOX":
        bbox[f[1]] = tuple(int(v) for v in f[2:6])
    elif f:
        sys.exit("rasterizer: " + line)
taken = {x["id"] for x in a["assets"]}
n = 0
for L, f, offx, offy in jobs:
    bx, by, bw, bh = bbox[str(f)]
    while f"flat_{n:03d}" in taken:
        n += 1
    aid = f"flat_{n:03d}"; taken.add(aid)
    (D / "images" / f"{aid}.png").write_bytes(f.with_suffix(".png").read_bytes())
    K.add_image_asset(a, aid, bw, bh)
    ax, ay = L["ks"].get("a", {"k": [0, 0]})["k"][:2]
    L.pop("shapes"); L["ty"] = 2; L["refId"] = aid; L["nm"] = (L.get("nm") or "") + "_flat"
    L["ks"]["a"] = {"a": 0, "k": [ax * S + offx - bx, ay * S + offy - by, 0]}
    if S != 1:
        assert not any(x.get("parent") == L.get("ind") for x in layers_of[id(L)]), f"layer {L.get('ind')} has children; flatten it at --scale 1"
        sc = L["ks"].setdefault("s", {"a": 0, "k": [100, 100, 100]})
        g = lambda v: [v[0] / S, v[1] / S] + list(v[2:])
        if sc.get("a") == 1:
            for kf in sc["k"]:
                for key in ("s", "e"):
                    if key in kf:
                        kf[key] = g(kf[key])
        else:
            sc["k"] = g(sc["k"])
alias = K.dedupe_images(D, a)
dropped = K.drop_unused_assets(D, a)
K.save(p, a)
print(f"flattened {len(jobs)} layers; {len(alias)} duplicate images merged")
