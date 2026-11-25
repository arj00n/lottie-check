"""Worked example: per-banner bake step for entire-menu-dietcoke-99 (Nov 2026 export, 1080x816, 360 frames).
Run by pipeline.sh inside the work dir (cwd has fix/, bake/). Layer numbers are for THIS export only:
diff layer_summary.py output against the previous export and renumber when the designer re-exports.

1. Fees strip: a null (ind 1) scrolls a row of pills/text/icons (inds 2-25). Bake them into one wide image on a
   3600-wide copy with the null held at its first keyframe, then replace them with one image layer parented to the
   null at local = null_anchor + bbox - null_pos0, so the scroll animation is kept.
2. Static text (inds 33, 35): bake from the Android render on a 1400x400 copy at position O=(20,20), with
   --fix-tracking, then turn the text layer into an image layer with anchor = -(bbox - O).
3. Drop fonts/chars once no live text is left (this is what lets lottie-ios use the Core Animation engine)."""
import sys, os, shutil, struct, subprocess
FIXES=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,FIXES); import lottiekit as K
BAKE=os.path.join(FIXES,'android_bake.py')
def run(d, keep, out, extra=()):
    r=subprocess.run([sys.executable,'-I',BAKE,d,'--keep',keep,'-o',out,*extra],capture_output=True,text=True)
    if r.returncode: sys.exit(r.stdout+r.stderr)
    t=r.stdout.split(); i=t.index('BBOX'); return [int(x) for x in t[i+1:i+5]]
def dims(f): return struct.unpack('>II',open(f,'rb').read(24)[16:24])
p,a=K.load('fix'); R={L['ind']:L for L in a['layers']}
# 1. scrolling strip
n1=R[1]; a1=n1['ks']['a']['k']; p0=n1['ks']['p']['k'][0]['s']
shutil.rmtree('bk',ignore_errors=True); shutil.copytree('fix','bk'); bp,b=K.load('bk'); b['w']=3600
B=[L for L in b['layers'] if L['ind']==1][0]; B['ks']['p']={'a':0,'k':list(p0)}; K.save(bp,b)
bb=run('bk',','.join(str(i) for i in range(2,27)),'bake/strip.png')
q=[a1[j]+bb[j]-p0[j] for j in (0,1)]
w,h=dims('bake/strip.png'); shutil.copy('bake/strip.png','fix/images/strip.png'); K.add_image_asset(a,'strip',w,h)
L=R[26]; K.image_layer(L,'strip',q[0],q[1]); L['parent']=1; L['nm']='Fees Strip_baked'
a['layers']=[L for L in a['layers'] if L['ind'] not in range(2,26)]; print('strip bbox',bb,'local',q)
# 2. static text, 1:1
O=(20,20)
for ind in (33,35):
    shutil.rmtree('tx',ignore_errors=True); shutil.copytree('fix','tx'); tp,t=K.load('tx'); t['w'],t['h']=1400,400
    T=[L for L in t['layers'] if L['ind']==ind][0]; T.pop('parent',None)
    assert R[ind]['ks']['a']['k'][:2]==[0,0] and R[ind]['ks']['s']['k'][:2]==[100,100]
    T['ks']={'o':{'a':0,'k':100},'r':{'a':0,'k':0},'p':{'a':0,'k':list(O)},'a':{'a':0,'k':[0,0]},'s':{'a':0,'k':[100,100]}}
    K.save(tp,t)
    bb=run('tx',str(ind),f'bake/text{ind}.png',('--fix-tracking',)); off=(bb[0]-O[0],bb[1]-O[1])
    w,h=dims(f'bake/text{ind}.png'); nid=f'text_{ind}'; shutil.copy(f'bake/text{ind}.png',f'fix/images/{nid}.png'); K.add_image_asset(a,nid,w,h)
    L=R[ind]; ks=L['ks']; ks['a']['k']=[-off[0],-off[1]]+ks['a']['k'][2:]
    L.pop('t',None); L.update(ty=2,refId=nid,nm=L['nm']+'_baked'); print('text',ind,'bbox',bb,'offset',off)
# 3.
a.pop('fonts',None); a.pop('chars',None); K.save(p,a)
