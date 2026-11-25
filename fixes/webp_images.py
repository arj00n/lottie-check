"""For each PNG image asset >= MINKB, encode lossy WebP and pngquant+oxipng PNG, keep whichever is smaller.
Photos usually win as WebP (about half); flat art, strips and soft light beams stay PNG.
WebP inside .lottie needs iOS 14+ for lottie-ios; lottie-android 6.5.2 reads it.
usage: python3 webp_images.py DIR Q AQ MINKB     (banners: 85 100 15; alpha_q below 100 bands soft gradients)"""
import sys, os, subprocess, shutil
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import lottiekit as K
d,Q,AQ,MIN=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])*1000
p,a=K.load(d)
for x in a['assets']:
    if not x.get('p','').endswith('.png'): continue
    src=f"{d}/images/{x['p']}"
    if os.path.getsize(src)<MIN: continue
    dst=src[:-4]+'.webp'; pq=src[:-4]+'.pq.png'
    subprocess.run(['cwebp','-quiet','-q',Q,'-alpha_q',AQ,'-m','6','-sharp_yuv','-exact',src,'-o',dst],check=True)
    subprocess.run(['pngquant','--quality','65-95','--force','--output',pq,'--',src])
    if not os.path.exists(pq): shutil.copy(src,pq)
    subprocess.run(['oxipng','-q','-o','4','--strip','safe',pq],check=True)
    w,q=os.path.getsize(dst),os.path.getsize(pq)
    if w<q: os.remove(src); os.remove(pq); x['p']=x['p'][:-4]+'.webp'; k='webp'
    else: os.remove(dst); os.replace(pq,src); k='png'
    print(x['id'],'png',q//1000,'webp',w//1000,'->',k)
K.save(p,a)
