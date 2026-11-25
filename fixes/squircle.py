"""Give rounded rectangles iOS-style continuous corners (Figma "corner smoothing").

Lottie has no corner smoothing: Figma exports a smoothed frame as a plain circular-corner rounded rect. This rebuilds
  - every mask that is a rounded rectangle (8 vertices, static or animated), and
  - every rectangle shape (`rc`) with a radius whose size equals the canvas (the frame background)
as a smoothed path. 1.0 = 100% smoothing (iOS app-icon squircle); Figma's "iOS" preset is 0.6.
Corner math is a port of figma-squircle (MIT, github.com/phamfoo/figma-squircle), which reproduces Figma's shape.

usage: python3 squircle.py DIR [--smoothing 1.0]
"""
import argparse, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K


def corner_params(r, sm, budget):
    p = (1 + sm) * r
    if p > budget:  # not enough room for full smoothing: shrink it, as Figma does
        sm = max(0.0, min(sm, budget / r - 1))
        p = min(p, budget)
    arc = 90 * (1 - sm)
    L = math.sin(math.radians(arc / 2)) * r * math.sqrt(2)
    alpha = (90 - arc) / 2
    p34 = r * math.tan(math.radians(alpha / 2))
    beta = 45 * sm
    c = p34 * math.cos(math.radians(beta))
    d = c * math.tan(math.radians(beta))
    b = (p - L - c - d) / 3
    return dict(a=2 * b, b=b, c=c, d=d, p=p, L=L, arc=math.radians(arc))


def unit(x, y):
    n = math.hypot(x, y) or 1
    return x / n, y / n


def corner_vertices(r, sm, budget):
    """One corner in corner-local XY (X back along the incoming edge, Y along the outgoing edge).
    Returns [(v, in, out)], tangents relative."""
    q = corner_params(r, sm, budget)
    a, b, c, d, p, L = q["a"], q["b"], q["c"], q["d"], q["p"], q["L"]
    m1 = (p - a - b - c, d)
    m2 = (m1[0] - L, m1[1] + L)
    S = ((p, 0), (0, 0), (-a, 0))
    E = ((0, p), (0, -a), (0, 0))
    if L < 1e-9:
        return [S, (m1, (c, -d), (-d, c)), E]
    k = 4 / 3 * math.tan(q["arc"] / 4) * r
    tA, tB = unit(-c, d), unit(-d, c)
    return [S, (m1, (c, -d), (k * tA[0], k * tA[1])), (m2, (-k * tB[0], -k * tB[1]), (-d, c)), E]


def squircle(x0, y0, x1, y1, r, sm):
    budget = min(x1 - x0, y1 - y0) / 2
    r = min(r, budget)
    local = corner_vertices(r, sm, budget)
    frames = [((x1, y0), (-1, 0), (0, 1)), ((x1, y1), (0, -1), (-1, 0)),
              ((x0, y1), (1, 0), (0, -1)), ((x0, y0), (0, 1), (1, 0))]
    v, i, o = [], [], []
    for (cx, cy), X, Y in frames:
        f = lambda u: (u[0] * X[0] + u[1] * Y[0], u[0] * X[1] + u[1] * Y[1])
        for pt, ti, to in local:
            P = f(pt)
            v.append([cx + P[0], cy + P[1]]); i.append(list(f(ti))); o.append(list(f(to)))
    return {"i": i, "o": o, "v": v, "c": True}


def rounded_rect(shape):
    """(x0, y0, x1, y1, r) if this bezier is Figma's 8-vertex rounded rectangle, else None."""
    v = shape.get("v", [])
    if len(v) != 8:
        return None
    xs, ys = [q[0] for q in v], [q[1] for q in v]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    r = v[0][1] - y0
    want = [(x0, y0 + r), (x0 + r, y0), (x1 - r, y0), (x1, y0 + r), (x1, y1 - r), (x1 - r, y1), (x0 + r, y1), (x0, y1 - r)]
    tol = max(x1 - x0, y1 - y0) * 1e-3
    if r <= 0 or any(abs(p[0] - q[0]) > tol or abs(p[1] - q[1]) > tol for p, q in zip(v, want)):
        return None
    return x0, y0, x1, y1, r


def convert_path(prop, sm):
    """Convert a path property (static or keyframed) in place. Returns True if converted."""
    if not prop.get("a"):
        rr = rounded_rect(prop["k"])
        if rr:
            prop["k"] = squircle(*rr, sm)
        return bool(rr)
    kfs = [kf for kf in prop["k"] if "s" in kf]
    rrs = [rounded_rect(s) for kf in prop["k"] for key in ("s", "e") if key in kf for s in kf[key]]
    if not rrs or not all(rrs):
        return False
    for kf in prop["k"]:
        for key in ("s", "e"):
            if key in kf:
                kf[key] = [squircle(*rounded_rect(s), sm) for s in kf[key]]
    return bool(kfs)


def walk_shapes(items, a, sm, n):
    for it in items:
        if it.get("ty") == "gr":
            walk_shapes(it["it"], a, sm, n)
        elif it.get("ty") == "rc" and not any(it[k].get("a") for k in ("p", "s", "r")):
            (px, py), (w, h), r = it["p"]["k"], it["s"]["k"], it["r"]["k"]
            if r > 0 and abs(w - a["w"]) < 0.5 and abs(h - a["h"]) < 0.5:
                path = squircle(px - w / 2, py - h / 2, px + w / 2, py + h / 2, r, sm)
                it.clear(); it.update(ty="sh", nm="squircle", ks={"a": 0, "k": path})
                n["rc"] += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--smoothing", type=float, default=1.0)
    args = ap.parse_args()
    p, a = K.load(args.dir)
    n = {"mask": 0, "rc": 0}
    for _, layers in K.layer_lists(a):
        for L in layers:
            for m in L.get("masksProperties", []):
                n["mask"] += convert_path(m["pt"], args.smoothing)
            walk_shapes(L.get("shapes", []), a, args.smoothing, n)
    K.save(p, a)
    print(f"squircle {args.smoothing:.0%}: {n['mask']} masks, {n['rc']} frame rectangles")
