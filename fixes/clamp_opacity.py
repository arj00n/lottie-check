"""Clamp animated opacity keyframes to 0..100 in a work dir. Figma bakes easing overshoot into opacity
(values like 104), which can make image layers flicker on device.

usage: python3 clamp_opacity.py DIR
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

p, a = K.load(sys.argv[1])
n = 0


def clamp(o):
    global n
    if isinstance(o, dict):
        op = o.get("o")
        if isinstance(op, dict) and op.get("a") == 1:
            for kf in op["k"]:
                for key in ("s", "e"):
                    if key in kf:
                        v = [min(100, max(0, x)) for x in kf[key]]
                        n += v != kf[key]
                        kf[key] = v
        for v in o.values():
            clamp(v)
    elif isinstance(o, list):
        for v in o:
            clamp(v)


for _, layers in K.layer_lists(a):
    for L in layers:
        clamp(L.get("ks", {}))
K.save(p, a)
print("clamped", n)
