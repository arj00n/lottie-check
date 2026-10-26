"""Rewrite a .lottie's zip container so lottie-android can open it. The files inside are unchanged.

Figma's .lottie export stores images uncompressed with a data descriptor, a combination
java.util.zip.ZipInputStream (used by lottie-android) rejects with
"only DEFLATED entries can have EXT descriptor". This writes every entry deflated, without descriptors.

usage: python3 rezip_lottie.py in.lottie out.lottie
"""
import sys, zipfile

src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
    for info in zin.infolist():
        zout.writestr(info.filename, zin.read(info.filename))
with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
    names = a.namelist()
    assert names == b.namelist() and all(a.read(n) == b.read(n) for n in names), "contents changed"
print(f"wrote {dst}: {len(names)} entries, contents identical")
