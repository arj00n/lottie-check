"""Shared helpers for the fix scripts. A "work dir" is an unpacked .lottie: manifest.json, animations/*.json, images/."""
import hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path

FIXES = Path(__file__).resolve().parent
ROOT = FIXES.parent


def rasterize_bin():
    for b in (ROOT / "bin/Rasterize", ROOT / "ios-harness/.build/release/Rasterize"):
        if b.exists():
            return str(b)
    sys.exit("Rasterize not built: run lottie-check once (it builds ios-harness), or `swift build -c release` in ios-harness")


def swift_tool(name):
    """Compile fixes/swift/<name>.swift on first use (needs Xcode command line tools)."""
    src, out = FIXES / "swift" / f"{name}.swift", FIXES / ".bin" / name
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", str(src), "-o", str(out)], check=True)
    return str(out)


def anim_path(d):
    return next((Path(d) / "animations").glob("*.json"))


def load(d):
    p = anim_path(d)
    return p, json.load(open(p))


def save(p, a):
    json.dump(a, open(p, "w"), separators=(",", ":"))


def unpack(lottie, d):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(lottie) as z:
        for n in z.namelist():
            t = (d / n).resolve()
            assert str(t).startswith(str(d.resolve())), f"unsafe zip entry {n}"
        z.extractall(d)


def pack(d, out):
    """Write a .lottie lottie-android can open: every entry DEFLATED, no data descriptors, no dotfiles."""
    d = Path(d)
    assert (d / "manifest.json").exists(), "no manifest.json"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if not f.startswith("."):
                    p = Path(root) / f
                    z.write(p, p.relative_to(d))


def animated(o):
    return '"a":1' in json.dumps(o, separators=(",", ":"))


def layer_lists(a):
    """(asset id or None, layers) for the root and every precomp."""
    yield None, a["layers"]
    for x in a["assets"]:
        if "layers" in x:
            yield x["id"], x["layers"]


def referenced_assets(a):
    refs, todo = set(), [a["layers"]]
    by_id = {x["id"]: x for x in a["assets"]}
    while todo:
        for L in todo.pop():
            r = L.get("refId")
            if r and r not in refs:
                refs.add(r)
                if "layers" in by_id.get(r, {}):
                    todo.append(by_id[r]["layers"])
    return refs


def drop_unused_assets(d, a):
    used = referenced_assets(a)
    dropped = [x for x in a["assets"] if x["id"] not in used]
    for x in dropped:
        if x.get("p") and not x["p"].startswith("data:"):
            (Path(d) / "images" / x["p"]).unlink(missing_ok=True)
    a["assets"] = [x for x in a["assets"] if x["id"] in used]
    return [x["id"] for x in dropped]


def dedupe_images(d, a):
    """Point layers at one copy of byte-identical image files."""
    seen, alias = {}, {}
    for x in a["assets"]:
        if x.get("p") and not x["p"].startswith("data:"):
            h = hashlib.sha256((Path(d) / "images" / x["p"]).read_bytes()).hexdigest()
            if h in seen:
                alias[x["id"]] = seen[h]
            else:
                seen[h] = x["id"]
    for _, layers in layer_lists(a):
        for L in layers:
            if L.get("refId") in alias:
                L["refId"] = alias[L["refId"]]
    return alias


def image_layer(L, asset_id, x, y, sx=100, sy=100, opacity=None):
    """Turn layer L (any type) into a static image layer at (x, y) in its parent's space. Keeps ind, parent, ip/op, matte flags."""
    for k in ("t", "shapes", "w", "h", "ef", "masksProperties", "hasMask", "tm"):
        L.pop(k, None)
    L.update(ty=2, refId=asset_id, bm=0, nm=(L.get("nm") or "") + "_baked")
    o = {"a": 0, "k": 100} if opacity is None else opacity
    L["ks"] = {"o": o, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [x, y]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [sx, sy]}}


def add_image_asset(a, asset_id, w, h):
    a["assets"].append({"id": asset_id, "w": w, "h": h, "u": "images/", "p": f"{asset_id}.png", "e": 0})


def solid_layer(a, v, ind=99999):
    return {"ty": 4, "ind": ind, "nm": "bg", "ip": a["ip"], "op": a["op"], "st": 0, "sr": 1, "ao": 0, "bm": 0,
            "ks": {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]}},
            "shapes": [{"ty": "gr", "it": [
                {"ty": "rc", "d": 1, "p": {"a": 0, "k": [a["w"] / 2, a["h"] / 2]}, "s": {"a": 0, "k": [a["w"], a["h"]]}, "r": {"a": 0, "k": 0}},
                {"ty": "fl", "c": {"a": 0, "k": [v, v, v, 1]}, "o": {"a": 0, "k": 100}, "r": 1},
                {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}}]}]}


def check(lottie):
    """Run lottie-check on a file; returns its result dict (with "out", the folder of frame PNGs)."""
    r = subprocess.run([str(ROOT / "lottie-check"), str(lottie), "--no-open", "--json", "--force"], capture_output=True, text=True)
    i = r.stdout.find("[\n")
    if i < 0:
        sys.exit(f"lottie-check gave no JSON for {lottie}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return json.loads(r.stdout[i:])[0]


def scratch():
    return Path(tempfile.mkdtemp(prefix="lottiefix-"))
