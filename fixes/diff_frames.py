"""Compare frame PNGs from two lottie-check out/ folders (or two PNGs).

usage: python3 diff_frames.py OUT_A OUT_B          same platform/frame pairs (ios-f0 vs ios-f0, ...)
       python3 diff_frames.py OUT_A OUT_B --cross  OUT_A's android frames vs OUT_B's ios and android frames
       python3 diff_frames.py a.png b.png
Prints the mean channel difference (out of 255) and the share of pixels off by more than 40 in any channel.
Rule of thumb: mean under ~1.5 with ~0% pixels off looks identical; check anything else by eye.
"""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

tool = K.swift_tool("diff")
A, B = Path(sys.argv[1]), Path(sys.argv[2])
if A.is_file():
    pairs = [(A, B)]
elif "--cross" in sys.argv:
    pairs = [(f, B / f.name.replace("android-", plat)) for f in sorted(A.glob("android-f*.png")) for plat in ("ios-", "android-")]
else:
    pairs = [(f, B / f.name) for f in sorted(A.glob("*-f*.png"))]
for x, y in pairs:
    if y.exists():
        r = subprocess.run([tool, str(x), str(y)], capture_output=True, text=True).stdout.strip()
        print(f"{x.stem:14s} vs {y.stem:14s} {r}")
