"""Print one line per layer (root and precomps) and per asset of a work dir, to read a new export
or diff it against the previous export of the same banner.
usage: python3 layer_summary.py DIR > summ.txt
  diff <(grep -oE 'ind[0-9]+ ty[0-9]+|par=[0-9]*' old.txt) <(grep -oE 'ind[0-9]+ ty[0-9]+|par=[0-9]*' new.txt)
  empty diff = same layer numbers, so the previous bake script and pipeline args still apply."""
import json,sys,glob
f=glob.glob(sys.argv[1]+'/animations/*.json')[0]; a=json.load(open(f))
print('canvas',a['w'],a['h'],'fr',a['fr'],'ip/op',a['ip'],a['op'],'fonts',len(a.get('fonts',{}).get('list',[])),'chars',len(a.get('chars',[])))
def desc(L):
    ks=L['ks']; an=[k for k in ('o','p','s','r','a') if ks.get(k,{}).get('a')]
    s=f"  ind{L['ind']} ty{L['ty']} '{L.get('nm','')}' ref={L.get('refId','')} par={L.get('parent','')} ip/op={L['ip']}/{L['op']} anim={an} masks={len(L.get('masksProperties',[]))} tt={L.get('tt','')} ef={[e.get('ty') for e in L.get('ef',[])]} bm={L.get('bm',0)}"
    if L['ty']==5:
        d=L['t']['d']['k'][0]['s']; s+=f" text={d['t']!r} j={d.get('j')} tr={d.get('tr')} s={d.get('s')} f={d.get('f')}"
    if 's' in an: s+=f" smax={max(k['s'][0] for k in ks['s']['k'] if 's' in k)}"
    return s
print('root'); [print(desc(L)) for L in a['layers']]
for x in a['assets']:
    if 'layers' in x: print(x['id'],x.get('nm','')); [print(desc(L)) for L in x['layers']]
    else: print(x['id'],'img',x['w'],x['h'],x.get('p'))
