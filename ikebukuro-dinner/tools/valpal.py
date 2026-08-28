import math, sys, itertools, json
BAND={'light':(0.43,0.77),'dark':(0.48,0.67)}; CHROMA_FLOOR=0.10
CVD_TARGET, CVD_FLOOR, NORMAL_FLOOR, CONTRAST_MIN = 8.0, 6.0, 15.0, 3.0
MACHADO={'protan':[[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
         'deutan':[[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]],
         'tritan':[[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]]}
def hex2srgb(h):
    h=h.strip().lstrip('#'); return [int(h[i:i+2],16)/255 for i in (0,2,4)]
def s2lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def lin(h): return [s2lin(c) for c in hex2srgb(h)]
def relLum(h):
    r,g,b=lin(h); return 0.2126*r+0.7152*g+0.0722*b
def contrast(a,b):
    x,y=sorted([relLum(a),relLum(b)],reverse=True); return (x+0.05)/(y+0.05)
def oklabFromLin(rgb):
    r,g,b=rgb
    l=(0.4122214708*r+0.5363325363*g+0.0514459929*b)**(1/3) if (0.4122214708*r+0.5363325363*g+0.0514459929*b)>=0 else 0
    m=(0.2119034982*r+0.6806995451*g+0.1073969566*b)**(1/3)
    s=(0.0883024619*r+0.2817188376*g+0.6299787005*b)**(1/3)
    return [0.2104542553*l+0.7936177850*m-0.0040720468*s,
            1.9779984951*l-2.4285922050*m+0.4505937099*s,
            0.0259040371*l+0.7827717662*m-0.8086757660*s]
def oklch(h):
    L,a,b=oklabFromLin(lin(h)); return L, math.hypot(a,b)
def simulate(h,kind):
    r,g,b=lin(h); M=MACHADO[kind]; cl=lambda c:max(0.0,min(1.0,c))
    return [cl(M[0][0]*r+M[0][1]*g+M[0][2]*b), cl(M[1][0]*r+M[1][1]*g+M[1][2]*b), cl(M[2][0]*r+M[2][1]*g+M[2][2]*b)]
def dE(h1,h2,kind=None):
    a=oklabFromLin(simulate(h1,kind) if kind else lin(h1))
    b=oklabFromLin(simulate(h2,kind) if kind else lin(h2))
    return 100*math.dist(a,b)
def validate(pal, mode='dark', surface=None, pairs='all', quiet=False):
    surface = surface or ('#1a1a19' if mode=='dark' else '#fcfcfb')
    lo,hi=BAND[mode]; ok=True; rows=[]
    off=[(c,round(oklch(c)[0],3)) for c in pal if not (lo<=oklch(c)[0]<=hi)]
    if off: ok=False
    rows.append(('Lightness band', not off, off or f'all {len(pal)} in L {lo}-{hi}'))
    lowc=[(c,round(oklch(c)[1],3)) for c in pal if oklch(c)[1]<CHROMA_FLOOR]
    if lowc: ok=False
    rows.append(('Chroma floor', not lowc, lowc or 'ok'))
    idx=list(range(len(pal)))
    pl = list(itertools.combinations(idx,2)) if pairs=='all' else [(i,i+1) for i in idx[:-1]]
    worst_cvd=(99,None); worst_norm=(99,None)
    for i,j in pl:
        c=min(dE(pal[i],pal[j],'protan'), dE(pal[i],pal[j],'deutan'))
        if c<worst_cvd[0]: worst_cvd=(c,(pal[i],pal[j]))
        nn=dE(pal[i],pal[j])
        if nn<worst_norm[0]: worst_norm=(nn,(pal[i],pal[j]))
    cvd_ok = worst_cvd[0]>=CVD_FLOOR
    if not cvd_ok: ok=False
    rows.append((f'CVD sep ({pairs})', cvd_ok, f'worst {worst_cvd[0]:.1f} {worst_cvd[1]} (target {CVD_TARGET}, floor {CVD_FLOOR})'))
    n_ok = worst_norm[0]>=NORMAL_FLOOR
    if not n_ok: ok=False
    rows.append(('Normal-vision floor', n_ok, f'worst {worst_norm[0]:.1f} {worst_norm[1]} (floor {NORMAL_FLOOR})'))
    lowct=[(c,round(contrast(c,surface),2)) for c in pal if contrast(c,surface)<CONTRAST_MIN]
    rows.append(('Contrast vs surface', not lowct, lowct or f'all >= {CONTRAST_MIN}:1'))
    if not quiet:
        print(f'--- mode={mode} surface={surface} pairs={pairs} n={len(pal)}')
        for r in rows: print(f'   [{"PASS" if r[1] else "FAIL"}] {r[0]}: {r[2]}')
        print('   =>', 'OK' if ok else 'FAIL')
    return ok, worst_cvd[0], worst_norm[0]
if __name__=='__main__':
    pal=[x for x in sys.argv[1].split(',') if x]
    mode=sys.argv[2] if len(sys.argv)>2 else 'dark'
    surf=sys.argv[3] if len(sys.argv)>3 else None
    pairs=sys.argv[4] if len(sys.argv)>4 else 'all'
    validate(pal,mode,surf,pairs)
