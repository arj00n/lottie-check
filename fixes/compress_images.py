"""Shrink a work dir's images: drop assets nothing uses, merge byte-identical images, quantize PNGs over 50 KB
with pngquant (quality 65-95, skipped if it doesn't help), then losslessly recompress all with oxipng.
Needs `brew install pngquant oxipng`; a missing tool is skipped.

usage: python3 compress_images.py DIR
"""
import shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lottiekit as K

D = Path(sys.argv[1])
p, a = K.load(D)
alias = K.dedupe_images(D, a)
dropped = K.drop_unused_assets(D, a)
K.save(p, a)
before = sum(f.stat().st_size for f in (D / "images").glob("*.png"))
for f in sorted((D / "images").glob("*.png")):
    if f.stat().st_size > 50_000 and shutil.which("pngquant"):
        subprocess.run(["pngquant", "--quality", "65-95", "--force", "--skip-if-larger", "--output", str(f), "--", str(f)])
    if shutil.which("oxipng"):
        subprocess.run(["oxipng", "-q", "-o", "4", "--strip", "safe", str(f)], check=True)
after = sum(f.stat().st_size for f in (D / "images").glob("*.png"))
print(f"dropped {len(dropped)} unused, merged {len(alias)} duplicates; images {before // 1024} KB -> {after // 1024} KB")
