"""Unpack a .lottie into a work dir, or pack a work dir into a .lottie lottie-android can open.

usage: python3 lottie_work.py unpack in.lottie DIR
       python3 lottie_work.py pack DIR out.lottie
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

cmd, a, b = sys.argv[1:4]
if cmd == "unpack":
    K.unpack(a, b)
elif cmd == "pack":
    K.pack(a, b)
else:
    sys.exit(__doc__)
print(f"{cmd}ed {a} -> {b}")
