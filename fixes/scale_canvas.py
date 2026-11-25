"""Scale a work dir's canvas to WIDTH (e.g. a 1440-wide export down to 1080). A root null scales the whole comp;
each image bitmap is resampled with sips to its new on-screen size, with layer anchor x r and scale / r, so it draws 1:1.
Refuses masked image layers. usage: python3 scale_canvas.py DIR WIDTH"""
import sys, os, subprocess
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import lottiekit as K
D,W=sys.argv[1],int(sys.argv[2]); p,a=K.load(D); f=W/a['w']
A={x['id']:x for x in a['assets'] if 'p' in x and 'layers' not in x}; ratio={}
for aid,x in A.items():
    nw,nh=round(x['w']*f),round(x['h']*f); fn=f"{D}/images/{x['p']}"
    subprocess.run(['sips','-z',str(nh),str(nw),fn,'--out',fn],check=True,capture_output=True)
    ratio[aid]=(nw/x['w'],nh/x['h']); x['w'],x['h']=nw,nh
def scal(v,rx,ry,mul):
    if v['a']:
        for k in v['k']:
            for key in ('s','e'):
                if key in k: k[key]=[k[key][0]*(rx if mul else 1/rx),k[key][1]*(ry if mul else 1/ry)]+k[key][2:]
    else: v['k']=[v['k'][0]*(rx if mul else 1/rx),v['k'][1]*(ry if mul else 1/ry)]+v['k'][2:]
for _,Ls in K.layer_lists(a):
    for L in Ls:
        if L['ty']==2 and L['refId'] in ratio:
            assert not L.get('masksProperties'), L['nm']
            rx,ry=ratio[L['refId']]; scal(L['ks']['a'],rx,ry,True); scal(L['ks']['s'],rx,ry,False)
ind=max(L['ind'] for L in a['layers'])+1
for L in a['layers']:
    if not L.get('parent'): L['parent']=ind
a['layers'].append({'ty':3,'ind':ind,'nm':'canvas scale','ip':a['ip'],'op':a['op'],'st':0,'sr':1,'ao':0,'bm':0,
  'ks':{'o':{'a':0,'k':100},'r':{'a':0,'k':0},'p':{'a':0,'k':[0,0,0]},'a':{'a':0,'k':[0,0,0]},'s':{'a':0,'k':[f*100,f*100,100]}}})
a['w'],a['h']=W,round(a['h']*f); K.save(p,a); print('canvas',a['w'],a['h'],'scale',f)
