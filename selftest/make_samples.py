"""Generate the installer's self-test lotties, so no real artwork ships with the tool.

  good.lottie    precomp + image layer + gradient + animated transforms; must play on iOS and Android
  broken.lottie  the same file with its precomp layers emptied, the way dotlottie-js 1.8.0 breaks
                 Figma exports; must fail on both

usage: python3 make_samples.py OUT_DIR
"""
import json, struct, sys, zipfile, zlib
from pathlib import Path


def png(width, height, rgba):
    """Solid-colour RGBA PNG."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + bytes(rgba) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def static(value):
    return {"a": 0, "k": value}


def transform(p=(0, 0), s=(100, 100), r=0, o=100):
    return {"p": static(list(p)), "a": static([0, 0]), "s": static(list(s)), "r": static(r), "o": static(o)}


def shape_layer(ind, shapes, ks, parent=None):
    layer = {"ind": ind, "ty": 4, "ip": 0, "op": 60, "st": 0, "ks": ks, "shapes": shapes}
    if parent:
        layer["parent"] = parent
    return layer


def animation():
    spin = {"a": 1, "k": [{"t": 0, "s": [0], "i": {"x": [0.5], "y": [1]}, "o": {"x": [0.5], "y": [0]}}, {"t": 60, "s": [360]}]}
    square = [{"ty": "gr", "it": [
        {"ty": "rc", "p": static([0, 0]), "s": static([120, 120]), "r": static(16)},
        {"ty": "gf", "t": 1, "s": static([-60, 0]), "e": static([60, 0]), "o": static(100), "r": 1,
         "g": {"p": 2, "k": static([0, 0.05, 0.55, 0.25, 1, 1, 0.85, 0])}},
        {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0), "o": static(100)},
    ]}]
    dot = [{"ty": "gr", "it": [
        {"ty": "el", "p": static([0, 0]), "s": static([40, 40])},
        {"ty": "fl", "c": static([1, 1, 1]), "o": static(100), "r": 1},
        {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0), "o": static(100)},
    ]}]
    precomp_layers = [
        {"ind": 1, "ty": 3, "ip": 0, "op": 60, "st": 0, "ks": {**transform((100, 100)), "r": spin}},
        shape_layer(2, square, transform(), parent=1),
        shape_layer(3, dot, transform((95, 0)), parent=1),
    ]
    return {
        "v": "5.7.0", "fr": 30, "ip": 0, "op": 60, "w": 400, "h": 300, "nm": "lottie-check self-test",
        "assets": [
            {"id": "card", "w": 64, "h": 64, "u": "/images/", "p": "card.png", "e": 0},
            {"id": "spinner", "w": 200, "h": 200, "layers": precomp_layers},
        ],
        "layers": [
            {"ind": 1, "ty": 0, "refId": "spinner", "w": 200, "h": 200, "ip": 0, "op": 60, "st": 0, "ks": transform((100, 50))},
            {"ind": 2, "ty": 2, "refId": "card", "ip": 0, "op": 60, "st": 0,
             "ks": {**transform((300, 200)), "o": {"a": 1, "k": [{"t": 0, "s": [0], "i": {"x": [0.5], "y": [1]}, "o": {"x": [0.5], "y": [0]}}, {"t": 30, "s": [100]}]}}},
            shape_layer(3, [{"ty": "gr", "it": [
                {"ty": "rc", "p": static([200, 150]), "s": static([400, 300]), "r": static(0)},
                {"ty": "fl", "c": static([0.07, 0.52, 0.22]), "o": static(100), "r": 1},
                {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0), "o": static(100)},
            ]}], transform()),
        ],
    }


def write_lottie(path, anim):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({"version": "1", "generator": "lottie-check selftest", "animations": [{"id": "animation"}]}))
        z.writestr("animations/animation.json", json.dumps(anim))
        z.writestr("images/card.png", png(64, 64, (255, 213, 0, 255)))


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    good = animation()
    write_lottie(out / "good.lottie", good)
    broken = animation()
    precomp = next(a for a in broken["assets"] if "layers" in a)
    precomp["layers"] = [{} for _ in precomp["layers"]]  # what dotlottie-js 1.8.0 leaves behind
    write_lottie(out / "broken.lottie", broken)


if __name__ == "__main__":
    main()
