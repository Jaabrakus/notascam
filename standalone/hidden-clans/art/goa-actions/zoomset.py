import sys
from PIL import Image
A=sys.argv[1]; out=sys.argv[2]; z=int(sys.argv[3]); rows=[r.split(',') for r in sys.argv[4:]]
C=64*z
im=Image.new('RGB',(max(len(r) for r in rows)*(C+6),len(rows)*(C+6)),(30,32,38))
for j,r in enumerate(rows):
  for i,p in enumerate(r):
    t=Image.new('RGBA',(64,64),(70,74,84,255)); t.alpha_composite(Image.open(f'{A}/{p}.png').convert('RGBA'))
    im.paste(t.resize((C,C),Image.NEAREST),(i*(C+6),j*(C+6)))
im.save(out); print(im.size)
