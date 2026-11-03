# Carve a voxel model out of a unit's four facings (S, N, E, W) so that seen straight
# from each side it is exactly that facing's sprite (visual hull + coverage patches).
import numpy as np
from PIL import Image

def arr(im): return np.asarray(im.convert('RGBA')).astype(np.int32)

def best_shift(a, b, rng=6):
    # a, b: (rows, cols) bool silhouettes; shift of b's columns that best matches a
    best=(-1,0)
    for s in range(-rng,rng+1):
        bb=np.roll(b,s,axis=1); sc=(a&bb).sum()-(a^bb).sum()
        if sc>best[0]: best=(sc,s)
    return best[1]

def segs(row):
    out=[];i=0;n=len(row)
    while i<n:
        if row[i]:
            j=i
            while j+1<n and row[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out

def rounded(front, side, p):
    # each (front run x side run) in a row becomes a superellipse slice, not a box: seen straight on
    # from any of the four sides it still fills exactly the same pixels
    V,n=front.shape; vox=np.zeros((V,n,n),bool)
    xs=np.arange(n)+0.5
    for v in range(V):
        for a,b in segs(front[v]):
            cx=(a+b+1)/2; rx=(b-a+1)/2
            for c,d in segs(side[v]):
                cz=(c+d+1)/2; rz=(d-c+1)/2
                ex=np.abs((xs[a:b+1,None]-cx)/rx)**p+np.abs((xs[None,c:d+1]-cz)/rz)**p
                vox[v,a:b+1,c:d+1]|=ex<=1.0001
    return vox

def carve(views, patch=True, p=None):
    S,N,E,W=(arr(views[d]) for d in 'SNEW')
    n=S.shape[0]
    aS,aN,aE,aW=(v[:,:,3]>0 for v in (S,N,E,W))
    # N and W are mirror views: line them up with S and E
    Nm=aN[:,::-1]; sN=best_shift(aS,Nm); Nm=np.roll(Nm,sN,axis=1); Ncol=np.roll(N[:,::-1],sN,axis=1)
    Em=aE[:,::-1]; Ecol=E[:,::-1]                 # E: front at screen right -> column = depth z
    Wm=aW; sW=best_shift(Em,Wm); Wm=np.roll(Wm,sW,axis=1); Wcol=np.roll(W,sW,axis=1)
    # vox[v, x, z]
    front=aS&Nm; side=Em&Wm
    vox=front[:,:,None]&side[:,None,:] if p is None else rounded(front,side,p)
    if patch:
        for _ in range(2):
            for silo,axis in ((aS,2),(Nm,2),(Em,1),(Wm,1)):
                cov=vox.any(axis=axis)
                miss=silo&~cov
                for v,c in zip(*np.nonzero(miss)):
                    # copy the depth span of the nearest covered column in this row
                    row=cov[v]; idx=np.nonzero(row)[0]
                    if len(idx):
                        j=idx[np.argmin(abs(idx-c))]
                        span=vox[v,j,:] if axis==2 else vox[v,:,j]
                    else:
                        other=(side if axis==2 else front)[v]
                        span=other if other.any() else np.zeros(n,bool)
                        if not span.any(): span=np.zeros(n,bool); span[n//2]=True
                    if axis==2: vox[v,c,:]|=span
                    else: vox[v,:,c]|=span
    cols={'S':S,'N':Ncol,'E':Ecol,'W':Wcol}
    return vox,cols,(aS,Nm,Em,Wm)

def exactness(vox,sil):
    aS,Nm,Em,Wm=sil
    pS=vox.any(axis=2); pE=vox.any(axis=1)
    out={}
    for k,a,p in (('S',aS,pS),('N',Nm,pS),('E',Em,pE),('W',Wm,pE)):
        out[k]=(a==p).mean()
    return out
