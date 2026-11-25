#!/bin/zsh
# Full fix for a Figma promo banner, in one work dir that holds src/ (unpacked original) and orig.lottie.
# usage: pipeline.sh WORKDIR BAKE_SCRIPT "MOVE_INDS" ABOVE_IND "BLEND_INDS"
#   BAKE_SCRIPT  per-banner python script run inside WORKDIR (bakes strip/text into fix/); "-" to skip
#   MOVE_INDS    animated layers under a blend layer, moved to just above ABOVE_IND before blends are baked
#   BLEND_INDS   blend-mode layers to bake, bottom-up order
# env: WEBP="85 100 15" adds the WebP-or-PNG step (size target < 200 KB); FR = frame list (default 0..359 every 30)
# out: WORKDIR/fixed.lottie, rz.lottie (original rezipped as the baseline), check-fix.json, check-rz.json
set -e; export F
F=${0:A:h}; LC=${F:h}/lottie-check
cd $1; rm -rf fix bake tx bk; cp -R src fix; mkdir bake
[ "$2" != "-" ] && python3 -I $2
python3 -I $F/flatten_shapes.py fix --min-paths 100
if [ -n "$3" ]; then python3 -I - "$3" "$4" <<'PY'
import sys, os; sys.path.insert(0, os.environ['F']); import lottiekit as K
mv=[int(x) for x in sys.argv[1].split()]; above=int(sys.argv[2])
p,a=K.load('fix'); Ls=a['layers']; moved=[L for L in Ls if L['ind'] in mv]; rest=[L for L in Ls if L['ind'] not in mv]
i=[L['ind'] for L in rest].index(above); a['layers']=rest[:i]+moved+rest[i:]; K.save(p,a); print('order',[L['ind'] for L in a['layers']])
PY
fi
for i in ${=5}; do python3 -I $F/bake_blend.py fix $i; done
python3 -I $F/clamp_opacity.py fix
[ -n "$WEBP" ] && python3 -I $F/webp_images.py fix ${=WEBP}
python3 -I $F/compress_images.py fix
python3 -I $F/lottie_work.py pack fix fixed.lottie
python3 -I $F/rezip_lottie.py orig.lottie rz.lottie >/dev/null
FR=${FR:-0,30,60,90,120,150,180,210,240,270,300,359}
$LC fixed.lottie --no-open --json --force --frames $FR > check-fix.json 2>/dev/null || true
$LC rz.lottie --no-open --json --force --frames $FR > check-rz.json 2>/dev/null || true
ls -l fixed.lottie
