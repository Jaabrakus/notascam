// ===== 3D view (WebGL) =====
const V3={iso:true,ISOPITCH:0.65,ISOFOV:0.28,models:true,STOREY:2.3,mode:'stack',on:false,gl:null,yaw:0,pitch:0.9,dist:15,cx:0,cy:0,tcx:0,tcy:0,z:0,night:false,terrain:null,tmesh:[],things:[],disp:new Map(),tex:new Map(),ring:null,mouse:null,drag:null,lastPan:0,keys:new Set(),vp:null,inv:null,eye:[0,0,0]};
const M4={
 persp(f,a,n,fa){const t=1/Math.tan(f/2);return [t/a,0,0,0,0,t,0,0,0,0,(fa+n)/(n-fa),-1,0,0,2*fa*n/(n-fa),0]},
 look(e,c,u){let z=[e[0]-c[0],e[1]-c[1],e[2]-c[2]];let l=Math.hypot(...z);z=z.map(v=>v/l);let x=[u[1]*z[2]-u[2]*z[1],u[2]*z[0]-u[0]*z[2],u[0]*z[1]-u[1]*z[0]];l=Math.hypot(...x);x=x.map(v=>v/l);const y=[z[1]*x[2]-z[2]*x[1],z[2]*x[0]-z[0]*x[2],z[0]*x[1]-z[1]*x[0]];
  return [x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-(x[0]*e[0]+x[1]*e[1]+x[2]*e[2]),-(y[0]*e[0]+y[1]*e[1]+y[2]*e[2]),-(z[0]*e[0]+z[1]*e[1]+z[2]*e[2]),1]},
 mul(a,b){const o=new Array(16);for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+j]*b[i*4+k];o[i*4+j]=s}return o},
 inv(m){const inv=new Array(16);
  inv[0]=m[5]*m[10]*m[15]-m[5]*m[11]*m[14]-m[9]*m[6]*m[15]+m[9]*m[7]*m[14]+m[13]*m[6]*m[11]-m[13]*m[7]*m[10];
  inv[4]=-m[4]*m[10]*m[15]+m[4]*m[11]*m[14]+m[8]*m[6]*m[15]-m[8]*m[7]*m[14]-m[12]*m[6]*m[11]+m[12]*m[7]*m[10];
  inv[8]=m[4]*m[9]*m[15]-m[4]*m[11]*m[13]-m[8]*m[5]*m[15]+m[8]*m[7]*m[13]+m[12]*m[5]*m[11]-m[12]*m[7]*m[9];
  inv[12]=-m[4]*m[9]*m[14]+m[4]*m[10]*m[13]+m[8]*m[5]*m[14]-m[8]*m[6]*m[13]-m[12]*m[5]*m[10]+m[12]*m[6]*m[9];
  inv[1]=-m[1]*m[10]*m[15]+m[1]*m[11]*m[14]+m[9]*m[2]*m[15]-m[9]*m[3]*m[14]-m[13]*m[2]*m[11]+m[13]*m[3]*m[10];
  inv[5]=m[0]*m[10]*m[15]-m[0]*m[11]*m[14]-m[8]*m[2]*m[15]+m[8]*m[3]*m[14]+m[12]*m[2]*m[11]-m[12]*m[3]*m[10];
  inv[9]=-m[0]*m[9]*m[15]+m[0]*m[11]*m[13]+m[8]*m[1]*m[15]-m[8]*m[3]*m[13]-m[12]*m[1]*m[11]+m[12]*m[3]*m[9];
  inv[13]=m[0]*m[9]*m[14]-m[0]*m[10]*m[13]-m[8]*m[1]*m[14]+m[8]*m[2]*m[13]+m[12]*m[1]*m[10]-m[12]*m[2]*m[9];
  inv[2]=m[1]*m[6]*m[15]-m[1]*m[7]*m[14]-m[5]*m[2]*m[15]+m[5]*m[3]*m[14]+m[13]*m[2]*m[7]-m[13]*m[3]*m[6];
  inv[6]=-m[0]*m[6]*m[15]+m[0]*m[7]*m[14]+m[4]*m[2]*m[15]-m[4]*m[3]*m[14]-m[12]*m[2]*m[7]+m[12]*m[3]*m[6];
  inv[10]=m[0]*m[5]*m[15]-m[0]*m[7]*m[13]-m[4]*m[1]*m[15]+m[4]*m[3]*m[13]+m[12]*m[1]*m[7]-m[12]*m[3]*m[5];
  inv[14]=-m[0]*m[5]*m[14]+m[0]*m[6]*m[13]+m[4]*m[1]*m[14]-m[4]*m[2]*m[13]-m[12]*m[1]*m[6]+m[12]*m[2]*m[5];
  inv[3]=-m[1]*m[6]*m[11]+m[1]*m[7]*m[10]+m[5]*m[2]*m[11]-m[5]*m[3]*m[10]-m[9]*m[2]*m[7]+m[9]*m[3]*m[6];
  inv[7]=m[0]*m[6]*m[11]-m[0]*m[7]*m[10]-m[4]*m[2]*m[11]+m[4]*m[3]*m[10]+m[8]*m[2]*m[7]-m[8]*m[3]*m[6];
  inv[11]=-m[0]*m[5]*m[11]+m[0]*m[7]*m[9]+m[4]*m[1]*m[11]-m[4]*m[3]*m[9]-m[8]*m[1]*m[7]+m[8]*m[3]*m[5];
  inv[15]=m[0]*m[5]*m[10]-m[0]*m[6]*m[9]-m[4]*m[1]*m[10]+m[4]*m[2]*m[9]+m[8]*m[1]*m[6]-m[8]*m[2]*m[5];
  let d=m[0]*inv[0]+m[1]*inv[4]+m[2]*inv[8]+m[3]*inv[12];if(!d)return null;d=1/d;return inv.map(v=>v*d)}};
function hexrgb(h,mul=1){h=(h||'#667766').replace('#','');return [parseInt(h.slice(0,2),16)/255*mul,parseInt(h.slice(2,4),16)/255*mul,parseInt(h.slice(4,6),16)/255*mul]}
// hexrgb plus an alpha of 1, parsed once a colour: the unit loop asked for it for every unit every frame (never change it)
const RGBA1=new Map();function v3rgba(h){let c=RGBA1.get(h);if(!c){c=[...hexrgb(h),1];if(RGBA1.size<4096)RGBA1.set(h,c)}return c}
function v3init(){if(V3.gl)return true;const c=$('world3d');const gl=c.getContext('webgl',{antialias:true,alpha:false});if(!gl){toast('3D needs WebGL, which is not available here.');return false}V3.gl=gl;
 const vs='attribute vec3 p;attribute vec3 n;attribute vec2 uv;attribute vec4 col;attribute vec4 i0;attribute vec4 i1;attribute vec4 i2;attribute vec2 ic;uniform float inst;uniform vec3 iright;uniform vec3 ilean;uniform vec4 ishadow;uniform mat4 mvp;uniform vec3 eye;uniform float lift;varying vec2 vuv;varying vec4 vc;varying float vl;varying float vdl;varying float vd;varying vec3 wp;varying vec3 vn;varying vec3 ve;uniform vec3 light;uniform float fill;uniform float tmv;void main(){vec3 P=p;vec3 N=n;vec2 U=uv;vec4 C=col;'+
  // GPU unit drawing (v3drawInst): one record a picture, shadow or ring (i0, i1, colour i2), its corners built here from
  // the corner attribute ic and the camera's right and lean, as the old per-vertex code built them
  (typeof G3VS==='string'?G3VS:'')+'if(inst>0.5){C=i2;N=vec3(0.0);if(inst<1.5){P=i0.xyz+iright*(ic.x*i0.w+ic.y*i1.y)+ilean*(ic.y*i1.x);U=vec2(ic.x<0.0?i1.z:i1.w,1.0-ic.y);}'+
  'else if(inst<2.5){P=vec3(i0.x+ishadow.x*i0.w*ic.x+ishadow.z*i1.x*ic.y,i0.y,i0.z+ishadow.y*i0.w*ic.x+ishadow.w*i1.x*ic.y);U=vec2(ic.x<0.0?i1.z:i1.w,1.0-ic.y);}'+
  'else if(inst<3.5){P=vec3(i0.x+ic.x*i0.w,i0.y,i0.z+(1.0-2.0*ic.y)*i1.x);U=vec2((ic.x+1.0)*0.5,1.0-ic.y);}'+
  'else{float w=ic.x,k=ic.y;if(w>=i1.z)k=0.0;float qa=k<0.5?0.0:i1.x+(i1.y-i1.x)*(w+(k>1.5?1.0:0.0))/i1.z,an=(qa+0.5)*6.2832,R=i0.w/cos(3.14159265/40.0),s=sin(an),o=cos(an),cy=iright.x,sy=-iright.z;vec2 d=k<0.5?vec2(0.0):R*vec2(s*cy-o*sy,-s*sy-o*cy);P=vec3(i0.x+d.x,i0.y,i0.z+d.y);U=d*(0.5/i0.w)+0.5;}}'+
  'vuv=U;vc=C;vec3 q=P+vec3(0.0,lift,0.0);if(C.a>0.955&&C.a<0.975&&P.y>0.5){float h=min(P.y-0.5,2.5);q.xz+=vec2(sin(tmv*1.3+P.x*0.7+P.z*0.4)+0.4*sin(tmv*2.9+P.z*1.3),cos(tmv*1.1+P.z*0.6))*0.016*h;}wp=q;vn=N;ve=eye-q;float ln=length(N);vl=ln<0.5?1.0:0.5+fill;vdl=ln<0.5?0.0:0.55*max(dot(N,light),0.0);vd=distance(q,eye);gl_Position=mvp*vec4(q,1.0);}';
 // Painted detail (art/pipeline/make_ground.py): grass on green ground, earth/stone elsewhere, projected on the
 // face's main axis and multiplied into its colour. Then the mood: warm sun and cool shade by day, moonlit blue
 // at night, plus the warm light of nearby fires (lp: position + reach, lc: colour).
 const fs=((V3.sdx=!!gl.getExtension('OES_standard_derivatives'))?'#extension GL_OES_standard_derivatives : enable\n':'')+'#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n'+
  'uniform float gfl;uniform float clk;uniform float addm;uniform float tm;uniform vec3 lightf;varying vec3 ve;uniform vec3 sunc;uniform vec3 skyc;uniform vec3 unl;uniform vec3 seas;uniform sampler2D t;uniform sampler2D gtex;uniform sampler2D etex;uniform sampler2D stex;uniform float gon;uniform vec2 gorg;uniform float night;uniform vec4 lp[8];uniform vec3 lc[8];uniform float useTex;uniform vec3 fogc;uniform float fogn;uniform float fogf;uniform float amb;uniform float alpha;uniform float soft;uniform vec4 tint;uniform vec3 tpx;uniform vec4 cut;uniform float cutMode;uniform vec4 mcut;uniform vec2 mcdir;uniform float mcslope;uniform sampler2D fogt;uniform vec4 fogr;uniform float fogon;uniform vec2 fogout;uniform sampler2D farfog;uniform vec4 farr;uniform float faron;uniform vec4 fp[12];uniform vec4 rp[6];uniform float rpw[6];uniform int rpn;uniform float fnear;uniform sampler2D smap;uniform mat4 lvp;uniform float son;varying vec2 vuv;varying vec4 vc;varying float vl;varying float vdl;varying float vd;varying vec3 wp;varying vec3 vn;'+
  // In the sun's shadow? Depth from the sun (packed in RGBA): a 3x3-texel box filter placed between texels (16 taps,
  // weighted by where the point falls), so edges are soft and smooth with no stair-steps; fading out at the map's border.
  // Shade keeps a quarter of the sunlight (light off the sky), so nothing in it goes dark.
  'float wn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);vec4 h=fract(sin(vec4(dot(i,vec2(127.1,311.7)),dot(i+vec2(1.0,0.0),vec2(127.1,311.7)),dot(i+vec2(0.0,1.0),vec2(127.1,311.7)),dot(i+vec2(1.0,1.0),vec2(127.1,311.7))))*43758.5453);return mix(mix(h.x,h.y,f.x),mix(h.z,h.w,f.x),f.y);}'+
  'vec2 wg(vec2 p,float s){return vec2(sin(p.x*2.7+s*1.3+sin(p.y*1.3+s*0.7))+0.6*sin(p.x*5.3-p.y*3.1+s*2.1),cos(p.y*2.5-s*1.1+sin(p.x*1.7-s*0.5))+0.6*cos(p.y*4.7+p.x*3.7-s*1.9));}'+
  'float unpk(vec4 c){return dot(c,vec4(1.0,1.0/255.0,1.0/65025.0,1.0/16581375.0));}'+
  'float sunlit(){if(son<0.5)return 1.0;vec4 q=lvp*vec4(wp+vn*0.05,1.0);vec3 s=q.xyz/q.w*0.5+0.5;float e=max(abs(s.x-0.5),abs(s.y-0.5))*2.0;if(e>=1.0||s.z>=1.0)return 1.0;vec2 u=s.xy*2048.0-0.5,fu=fract(u),b=(floor(u)+0.5)/2048.0;float z=s.z-0.0007;'+
  // the footprint's four corners first: all lit or all in shadow (most of the screen) needs no more taps
  'float k4=(z>unpk(texture2D(smap,b+vec2(-1.0,-1.0)/2048.0))?0.0:1.0)+(z>unpk(texture2D(smap,b+vec2(2.0,-1.0)/2048.0))?0.0:1.0)+(z>unpk(texture2D(smap,b+vec2(-1.0,2.0)/2048.0))?0.0:1.0)+(z>unpk(texture2D(smap,b+vec2(2.0,2.0)/2048.0))?0.0:1.0);float l=k4>3.5?9.0:0.0;'+
  'if(k4>0.5&&k4<3.5)for(int i=-1;i<=2;i++)for(int j=-1;j<=2;j++){float w=(i==-1?1.0-fu.x:i==2?fu.x:1.0)*(j==-1?1.0-fu.y:j==2?fu.y:1.0);l+=w*(z>unpk(texture2D(smap,b+vec2(float(i),float(j))/2048.0))?0.0:1.0);}return mix(l/9.0,1.0,smoothstep(0.8,1.0,e));}'+
  // Pixel-art pictures (units, gear, things; tpx: their size, z 1, or 2 when drawn with alpha-to-coverage) defined, not
  // blurred (the owner, 10-27: "no smooth but defined", "defined no blur please"): each art pixel a crisp block, only its
  // edge blended, over at most one screen pixel, at every zoom (the texture filtered and kept premultiplied, v3texUpload);
  // nearest sampling gave uneven doubled pixels between zoom steps and dropped ones further out.
  'vec4 txp(vec2 u){vec2 p=u*tpx.xy;\n#ifdef GL_OES_standard_derivatives\nvec2 s=floor(p+0.5);p=s+clamp((p-s)/max(fwidth(p),vec2(0.0001)),-0.5,0.5);\n#else\np=floor(p)+0.5;\n#endif\nvec4 c=texture2D(t,p/tpx.xy);return c.a>0.002?vec4(c.rgb/c.a,c.a):vec4(0.0);}'+
  'void main(){if(mcut.z>0.0&&wp.y>mcut.w){vec2 dm=floor(wp.xz-vn.xz*0.03+0.5)-mcut.xy;float ll=max(dot(mcdir,mcdir),0.0001),tm=clamp(dot(dm,mcdir)/ll,0.0,1.0);if(length(dm-mcdir*tm)<=mcut.z-0.6&&wp.y>mcut.w+max(0.0,tm*sqrt(ll)-mcut.z*0.5)*mcslope)discard;}if(cutMode>0.5){float fr=dot(wp.xz-cut.xy,cut.zw);if(fr>0.0&&(cutMode<1.5||wp.y>-3.6))discard;}vec4 c=useTex>0.5?(tpx.z>0.5?txp(vuv):texture2D(t,vuv))*vc:vc;if(c.a<(soft>0.5||tpx.z>1.5?0.01:0.5))discard;'+
  // trees (colour alpha 0.97) thin out to a dither over your units (fp: screen position, radius, depth) and near the eye;
  // rock (0.94, v3rockTag) the same way where it stands in front of one of them or of the point looked at: the slots where
  // it fades, packed (rp: screen position, radius, depth; rpw: how much; rpn: how many, up to 6), and right at the eye
  'if(vc.a>0.955&&vc.a<0.975){float k=fnear>0.0?1.0-smoothstep(fnear*0.7,fnear,vd):0.0;for(int i=0;i<12;i++){if(fp[i].z>0.0&&gl_FragCoord.z<fp[i].w){vec2 dd=(gl_FragCoord.xy-fp[i].xy)/fp[i].z;dd.y*=0.7;k=max(k,0.72*(1.0-smoothstep(0.55,1.0,length(dd))));}}if(k>0.0){vec2 fa=floor(gl_FragCoord.xy),fb=floor(fa*0.5);float d4=fract(dot(fb,vec2(0.5,fb.y*0.75)))*0.25+fract(dot(fa,vec2(0.5,fa.y*0.75)));if(d4<k)discard;}}'+
  'if(vc.a>0.932&&vc.a<0.948&&useTex<0.5&&soft<0.5&&addm<0.5&&(rpn>0||vd<0.7)){float k=1.0-smoothstep(0.35,0.7,vd);for(int i=0;i<6;i++){if(i>=rpn)break;if(gl_FragCoord.z<rp[i].w){vec2 dd=(gl_FragCoord.xy-rp[i].xy)/rp[i].z;dd.y*=0.7;k=max(k,0.72*rpw[i]*(1.0-smoothstep(0.55,1.0,length(dd))));}}if(k>0.0){vec2 fa=floor(gl_FragCoord.xy),fb=floor(fa*0.5);float d4=fract(dot(fb,vec2(0.5,fb.y*0.75)))*0.25+fract(dot(fa,vec2(0.5,fa.y*0.75)));if(d4<k)discard;}}'+
  'if(tint.a>0.0){gl_FragColor=tint;return;}'+
  // Water's surface (vertex alpha 0.915): ripples moving over it and the sky in it (more at a glancing look); no sun
  // glints or sparkles on it (the owner, 10-27: "i do not like the water glint").
  // A river's water runs (its flow, tiles a second, comes in as the uv; v3drawLiquids): the ripples are carried
  // downstream in two phases faded into each other so they never jump, with long streaks drifting along with it.
  // A cloud (vertex alpha 0.88, v3clouds): wisps made from the cloud shadows' own drifting pattern (below), so each
  // floats over its shadow; vc.r is how far they have faded in with the zoom, vc.g how thick the sky is.
  'bool cld=vc.a>0.875&&vc.a<0.885;if(cld){vec2 cw=wp.xz+vec2(tm*0.22,tm*0.09);float cn=wn(cw*0.045)*0.65+wn(cw*0.11+3.1)*0.35,fz=wn(cw*0.31+5.7);c=vec4(0.97,0.98,1.0,smoothstep(0.6,0.86,cn+(fz-0.5)*0.12)*vc.r*vc.g);if(c.a<0.01)discard;}'+
  'bool wat=vc.a>0.905&&vc.a<0.925;float wsp=0.0;if(wat){vec2 p=wp.xz;float s=tm;vec2 fl=vuv;float fs=dot(fl,fl),f1=fract(s*0.3),f2=fract(s*0.3+0.5),w1=1.0-abs(1.0-2.0*f1),rs=0.0;vec2 p1=p,p2=p;'+
  'if(fs>0.0004){p1=p-fl*f1*3.333;p2=p-fl*f2*3.333;vec2 fd=fl*inversesqrt(fs),fq=vec2(-fd.y,fd.x);vec2 q1=vec2(dot(p1,fd),dot(p1,fq)),q2=vec2(dot(p2,fd),dot(p2,fq));rs=mix(wn(q2*vec2(0.7,3.2)+7.3),wn(q1*vec2(0.7,3.2)),w1);rs=smoothstep(0.58,0.86,rs)*clamp(sqrt(fs)*1.6,0.0,1.0);}'+
  'vec2 g=mix(wg(p2,s),wg(p1,s),w1);'+
  'vec3 N=normalize(vec3(g.x*0.075,1.0,g.y*0.075)),V=normalize(ve);float fr=pow(1.0-max(dot(N,V),0.0),4.0);c.rgb=mix(c.rgb,fogc*vec3(0.8,0.94,1.1),clamp(0.1+fr*0.6,0.0,0.52));float hs=max(dot(N,normalize(lightf+V)),0.0);'+
  'float wv=sin(p.x*3.1+p.y*1.7+s*1.6)*sin(p.y*2.6-p.x*0.9-s*1.2)+0.5*sin(p.x*6.3-p.y*5.1+s*2.4);c.rgb*=1.0+wv*0.06;c.rgb=mix(c.rgb,fogc*vec3(0.9,0.97,1.05)+0.08,rs*0.22);c.a=1.0;}'+
  'bool face=length(vn)>0.5;if(gon>0.5&&useTex<0.5&&face&&!wat&&!cld){vec3 an=abs(vn);vec2 q=(an.y>0.7?wp.xz:(an.x>an.z?wp.zy:wp.xy))-gorg;vec3 g=texture2D(gtex,q*0.25).rgb,e=texture2D(etex,q*0.25).rgb;float gr=an.y>0.7?clamp((c.g-max(c.r,c.b))*7.0,0.0,1.0):0.0;float m=dot(texture2D(gtex,q*0.0625).rgb,vec3(0.6667));if(vc.a>0.985&&vc.a<0.995){vec2 sq=an.y>0.7?q*0.5:vec2((an.x>an.z?wp.z:wp.x)-(an.x>an.z?gorg.y:gorg.x),wp.y)*0.5;c.rgb*=texture2D(stex,sq).rgb*1.99*clamp(0.64+0.42*wp.y,0.64,1.0);}else{c.rgb*=mix(e,g,gr)*1.99*mix(1.0,m,0.5);'+
  // meadows vary over tens of tiles: drier, yellower patches and darker lush ones (grass on open ground only)
  'if(gr>0.0&&vc.a>0.995){float mv=wn(wp.xz*0.055+3.7)*0.65+wn(wp.xz*0.13+9.1)*0.35;c.rgb=mix(c.rgb,c.rgb*mix(vec3(0.9,1.0,0.9),vec3(1.08,1.05,0.88),smoothstep(0.3,0.75,mv)),gr*0.8);}}}'+
  // The season on green ground and leaves (lit faces, never the units' pictures): autumn turns greens toward olive
  // and gold, winter drains and cools them, spring freshens them.
  'if(face&&useTex<0.5&&dot(seas,seas)>0.0){float gd=clamp((c.g-max(c.r,c.b))*5.0,0.0,1.0);if(gd>0.0){float l0=dot(c.rgb,vec3(0.3,0.59,0.11));vec3 fa=vec3(c.g*0.95+c.r*0.25,c.g*0.82+c.r*0.06,c.b*0.5);float sk=0.62;if(vc.a>0.955&&vc.a<0.975){sk=mix(0.12,1.6,smoothstep(0.52,0.62,vc.r/max(vc.g,0.01)));fa=mix(fa,vec3(c.g*1.12+0.04,c.g*0.56,c.b*0.34),smoothstep(0.5,0.72,wn(wp.xz*0.3+7.0)));}c.rgb=mix(c.rgb,fa,min(1.0,gd*seas.x*sk));c.rgb=mix(c.rgb,vec3(l0)*vec3(0.92,0.97,1.04),gd*seas.y);c.rgb=mix(c.rgb,c.rgb*vec3(0.94,1.08,0.9),gd*seas.z);}}'+
  'float sl=sunlit(),cl=1.0;if(clk>0.0){vec2 cw=wp.xz+vec2(tm*0.22,tm*0.09);float cn=wn(cw*0.045)*0.65+wn(cw*0.11+3.1)*0.35;cl=1.0-clk*smoothstep(0.64,0.8,cn);}vec3 lit=vl>0.9?unl*mix(1.0,cl,0.5):skyc*vl+sunc*(vdl*mix(0.25,1.0,sl)*cl);vec3 rgb=c.rgb*lit*amb;'+
  // upright faces (cliffs, walls, trunks) a little darker toward the ground they stand on
  'if(face&&vl<0.9&&abs(vn.y)<0.6&&!wat){float hb=wp.y-gfl;if(hb>-0.2&&hb<0.9)rgb*=mix(0.66,1.0,smoothstep(-0.05,0.9,hb));}float lum=dot(rgb,vec3(0.3,0.59,0.11));'+
  'if(night>1.5)rgb=mix(vec3(lum),rgb,0.78)*vec3(1.02,0.93,0.84);else{vec3 dg=mix(vec3(lum),rgb,0.9)*vec3(1.03,1.0,0.94)+vec3(0.0,0.008,0.028)*(1.0-clamp(lum*1.4,0.0,1.0));'+
  // moonlit: blue, but each colour keeps some of itself (grass stays a dark blue-green, not grey)
  'vec3 ng=mix(vec3(lum)*vec3(0.62,0.78,1.14),rgb*vec3(0.66,0.8,1.06),0.5);rgb=mix(dg,ng,clamp(night,0.0,1.0)*(vl>0.9?0.62:1.0));}'+
  'if(addm>0.5)rgb=c.rgb*lit*amb;vec3 wgl=wat?wsp*sunc*sl*clamp(1.0-night*0.5,0.0,1.0):vec3(0.0);if(wat){float gL=dot(wgl,vec3(0.3,0.59,0.11)),hr=max(0.72-dot(rgb,vec3(0.3,0.59,0.11)),0.0);wgl*=gL>0.0001?hr/(gL+hr):0.0;}rgb+=wgl;vec3 add=vec3(0.0);for(int i=0;i<8;i++){if(lp[i].w>0.0){vec3 dv=lp[i].xyz-wp;float a=max(0.0,1.0-length(dv)/lp[i].w);float nd=face?max(dot(normalize(dv),vn),0.0)*0.75+0.25:0.7;add+=lc[i]*a*a*(3.0-2.0*a)*nd;}}rgb+=c.rgb*add;'+
  // Fog of war (v3fogData): r in sight, g explored, soft between tiles and fading in. Never seen: a dim blue-grey with a
  // hint of the land's shading; explored: lightly greyed and a little darker; in sight: as it is. Water's sun glints
  // only as far as it is in sight (else they showed through the tint, pale like snow).
  'if(fogon>0.5&&addm<0.5&&!cld){vec2 fc=(vec2(wp.x,-wp.z)-fogr.xy+0.5)/fogr.zw;vec2 sv=(fc.x<0.0||fc.y<0.0||fc.x>1.0||fc.y>1.0)?(faron>0.5?texture2D(farfog,(vec2(wp.x,-wp.z)-farr.xy+0.5)/farr.zw).rg:fogout):texture2D(fogt,fc).rg;rgb-=wgl;float lu=dot(rgb,vec3(0.3,0.59,0.11));'+
  // a drifting mist over what you don't see: soft, slowly moving swirls
  'float ms=wn(wp.xz*0.11+vec2(tm*0.045,tm*0.03))*0.6+wn(wp.xz*0.27-vec2(tm*0.03,-tm*0.05))*0.4;vec3 mc=vec3(0.62,0.68,0.76)*(0.55+0.45*ms);'+
  'vec3 ex=mix(mix(vec3(lu),rgb,0.6)*0.64,mc*0.5,0.26+0.14*ms),nv=mix(vec3(0.15,0.18,0.24)+vec3(lu)*0.22,mc*0.42,0.35+0.2*ms);rgb=mix(mix(nv,ex,max(sv.g,sv.r)),rgb,sv.r)+wgl*sv.r;}'+
  'float f=clamp((vd-fogn)/(fogf-fogn),0.0,1.0);gl_FragColor=vec4(mix(rgb,fogc*(1.0-addm),f),soft>0.5||tpx.z>1.5?alpha*c.a:alpha);}';
 const sh=(t,src)=>{const s=gl.createShader(t);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))console.error(gl.getShaderInfoLog(s));return s};
 const pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,vs));gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);gl.useProgram(pr);V3.pr=pr;
 V3.loc={p:gl.getAttribLocation(pr,'p'),n:gl.getAttribLocation(pr,'n'),uv:gl.getAttribLocation(pr,'uv'),col:gl.getAttribLocation(pr,'col'),i0:gl.getAttribLocation(pr,'i0'),i1:gl.getAttribLocation(pr,'i1'),i2:gl.getAttribLocation(pr,'i2'),ic:gl.getAttribLocation(pr,'ic')};
 ['mvp','eye','light','t','useTex','fogc','fogn','fogf','amb','lift','alpha','tint','cut','cutMode','mcut','mcdir','mcslope','gtex','etex','stex','gon','gorg','night','lp','lc','fp','rp','rpw','rpn','fogt','fogr','fogon','fogout','farfog','farr','faron','fnear','smap','lvp','son','fill','soft','sunc','skyc','unl','seas','tm','lightf','addm','tmv','clk','gfl','inst','iright','ilean','ishadow','tpx'].forEach(k=>V3.loc[k]=gl.getUniformLocation(pr,k));gl.uniform1i(V3.loc.smap,4);gl.uniform1i(V3.loc.fogt,5);gl.uniform1i(V3.loc.farfog,6);
 gl.uniform1i(V3.loc.gtex,1);gl.uniform1i(V3.loc.etex,2);gl.uniform1i(V3.loc.stex,3);
 V3.dyn=gl.createBuffer();
 // GPU unit drawing: ANGLE_instanced_arrays (in every WebGL1 we run on; without it v3drawInst spreads the records into
 // triangles itself). Corners: a quad's six (x -1/1, y 0/1, as quad() splits it), a ring's 40 wedges (wedge, 0 centre 1 2 rim).
 {const x=gl.getExtension('ANGLE_instanced_arrays'),L=V3.loc;if(x&&L.i0>=0&&L.i1>=0&&L.i2>=0&&L.ic>=0){V3.ix=x;V3.ibuf=gl.createBuffer();const ac=[];for(let s=0;s<40;s++)ac.push(s,0,s,1,s,2);
  V3.iq=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,V3.iq);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,0,1,0,1,1,-1,0,1,1,-1,1]),gl.STATIC_DRAW);V3.ia=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,V3.ia);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(ac),gl.STATIC_DRAW)}}
 // The sun's shadow map: depth seen from the sun, packed into RGBA (any WebGL1 has that), 2048 square over the area
 // round the camera. Alpha-tested like the main pass so leaves and cut-outs cast the right shapes.
 {const svs='attribute vec3 p;attribute vec2 uv;attribute vec4 col;uniform mat4 lmvp;uniform float lift;varying vec2 vuv;varying float va;void main(){vuv=uv;va=col.a;gl_Position=lmvp*vec4(p+vec3(0.0,lift,0.0),1.0);}';
  const sfs='#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\nuniform sampler2D t;uniform float useTex;varying vec2 vuv;varying float va;void main(){if(va*(useTex>0.5?texture2D(t,vuv).a:1.0)<0.5)discard;vec4 e=fract(gl_FragCoord.z*vec4(1.0,255.0,65025.0,16581375.0));e-=e.yzww*vec4(1.0/255.0,1.0/255.0,1.0/255.0,0.0);gl_FragColor=e;}';
  const sp=gl.createProgram();gl.attachShader(sp,sh(gl.VERTEX_SHADER,svs));gl.attachShader(sp,sh(gl.FRAGMENT_SHADER,sfs));for(const k of ['p','uv','col'])if(V3.loc[k]>=0)gl.bindAttribLocation(sp,V3.loc[k],k);gl.linkProgram(sp);
  if(gl.getProgramParameter(sp,gl.LINK_STATUS)){const S=V3.SHADOW=2048,tx=gl.createTexture();gl.activeTexture(gl.TEXTURE4);gl.bindTexture(gl.TEXTURE_2D,tx);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,S,S,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
   for(const k of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,k,gl.NEAREST);for(const k of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,k,gl.CLAMP_TO_EDGE);
   const rb=gl.createRenderbuffer();gl.bindRenderbuffer(gl.RENDERBUFFER,rb);gl.renderbufferStorage(gl.RENDERBUFFER,gl.DEPTH_COMPONENT16,S,S);const fb=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fb);
   gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tx,0);gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.RENDERBUFFER,rb);const ok=gl.checkFramebufferStatus(gl.FRAMEBUFFER)===gl.FRAMEBUFFER_COMPLETE;gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.activeTexture(gl.TEXTURE0);
   if(ok)V3.sh={pr:sp,fb,tx,lmvp:gl.getUniformLocation(sp,'lmvp'),lift:gl.getUniformLocation(sp,'lift'),t:gl.getUniformLocation(sp,'t'),useTex:gl.getUniformLocation(sp,'useTex')}}}
 // The sky: a gradient from the fog colour at the horizon up to blue, the sun's disc and glow, slow clouds; at night
 // a dark sky, the moon and stars. One triangle over the screen, drawn first.
 {const kvs='attribute vec2 p;varying vec2 v;void main(){v=p;gl_Position=vec4(p,0.9999,1.0);}';
  const kfs='#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\nuniform mat4 inv;uniform vec3 eye;uniform vec3 sun;uniform vec3 hz;uniform vec3 zen;uniform float night;uniform float time;varying vec2 v;'+
   'float hh(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}float vno(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hh(i),hh(i+vec2(1.0,0.0)),f.x),mix(hh(i+vec2(0.0,1.0)),hh(i+vec2(1.0,1.0)),f.x),f.y);}'+
   'float fbm(vec2 p){float s=0.0,a=0.5;for(int i=0;i<5;i++){s+=a*vno(p);p=p*2.03+vec2(1.7,9.2);a*=0.5;}return s;}'+
   'void main(){vec4 q=inv*vec4(v,1.0,1.0);vec3 d=normalize(q.xyz/q.w-eye);float up=d.y,sd=dot(d,sun);vec3 c=mix(hz,zen,smoothstep(0.0,0.5,up));'+
   'float nb=smoothstep(0.35,0.85,night);if(nb<1.0){float low=1.0-smoothstep(0.2,0.6,sun.y);c+=(1.0-nb)*(vec3(1.0,0.85,0.6)*pow(max(sd,0.0),16.0)*0.22+vec3(1.0,0.55,0.25)*pow(max(sd,0.0),5.0)*0.3*low*(1.0-smoothstep(0.0,0.35,up))+vec3(1.0,0.97,0.88)*smoothstep(0.9990,0.9995,sd));}'+
   'if(nb>0.0){c+=nb*vec3(0.85,0.9,1.0)*smoothstep(0.9993,0.9996,sd)*0.9+nb*vec3(0.28,0.32,0.45)*pow(max(sd,0.0),40.0)*0.5;c+=nb*vec3(0.9)*step(0.996,hh(floor(d.xz/(abs(up)+0.25)*160.0)))*smoothstep(0.05,0.3,up);}'+
   'if(up>0.01){float k=smoothstep(0.5,0.85,fbm(d.xz/(up+0.08)*0.9+vec2(time*0.006,time*0.002)));c=mix(c,mix(vec3(mix(0.86,1.0,smoothstep(0.0,0.4,up)))*mix(vec3(1.0),hz*1.4,0.35),vec3(0.13,0.15,0.22),nb),k*0.8*smoothstep(0.01,0.18,up));}'+
   'gl_FragColor=vec4(c,1.0);}';
  const kp=gl.createProgram();gl.attachShader(kp,sh(gl.VERTEX_SHADER,kvs));gl.attachShader(kp,sh(gl.FRAGMENT_SHADER,kfs));gl.linkProgram(kp);
  if(gl.getProgramParameter(kp,gl.LINK_STATUS)){const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);V3.skyp={pr:kp,buf:b,p:gl.getAttribLocation(kp,'p')};for(const k of ['inv','eye','sun','hz','zen','night','time'])V3.skyp[k]=gl.getUniformLocation(kp,k)}}
 gl.useProgram(pr);
 // ring texture
 // a crisp band with a faint halo, drawn blended (soft) so its edge is smooth at any zoom
 const rc=document.createElement('canvas');rc.width=rc.height=128;const rx=rc.getContext('2d');rx.strokeStyle='rgba(255,255,255,.22)';rx.lineWidth=22;rx.beginPath();rx.arc(64,64,50,0,7);rx.stroke();rx.strokeStyle='rgba(255,255,255,.45)';rx.lineWidth=15;rx.beginPath();rx.arc(64,64,51,0,7);rx.stroke();rx.strokeStyle='#fff';rx.lineWidth=10;rx.beginPath();rx.arc(64,64,52,0,7);rx.stroke();V3.ring=v3texFromCanvas(rc);
 {const sc=document.createElement('canvas');sc.width=sc.height=64;const sx=sc.getContext('2d'),g=sx.createRadialGradient(32,32,0,32,32,31);g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(0.35,'rgba(255,255,255,0.82)');g.addColorStop(0.7,'rgba(255,255,255,0.32)');g.addColorStop(1,'rgba(255,255,255,0)');sx.fillStyle=g;sx.fillRect(0,0,64,64);V3.soft=v3texFromCanvas(sc)}   // a unit's contact shadow
 {const bc=document.createElement('canvas');bc.width=bc.height=64;const bx=bc.getContext('2d');bx.fillStyle='#fff';bx.beginPath();bx.arc(32,32,30,0,7);bx.fill();V3.blob=v3texFromCanvas(bc)}
 v3wire();v3kick();
 // While recording a trailer the window may be covered and WebKit then stops animation
 // frames; a timer keeps the 3D view drawing (only when the recorder asks for it).
 if(window.dmRecording)setInterval(()=>{if(performance.now()-(V3.lastFrameAt||0)>100)v3frame(performance.now())},33);return true}
function v3repeatTex(file,unit){const e={ok:false};const img=new Image();img.onload=()=>{const gl=V3.gl,t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);gl.activeTexture(gl.TEXTURE0);e.t=t;e.ok=true};img.onerror=()=>{e.failed=true;setTimeout(()=>{if(!e.ok){e.failed=false;img.src=file+'?r='+Date.now()}},3000)};img.src=file;return e}
function v3texFromCanvas(cv){const gl=V3.gl,t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,cv);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return {t,ok:true}}
// A loaded picture goes to the GPU from v3bgWork (V3.texQ): small ones many a frame, a big sheet (a beast's, 4-16 ms
// each) one a frame; uploaded as they came in, 16 dragon sheets stalled one frame for 80-90 ms.
function v3tex(file){if(!file)return null;let e=V3.tex.get(file);if(e)return e;e={t:null,ok:false};V3.tex.set(file,e);const img=new Image();img.onload=()=>(V3.texQ||(V3.texQ=[])).push([img,e]);img.src=file;return e}
function v3texUpload(img,e){const gl=V3.gl,t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);const soft=img.width>=128&&!(img.width&(img.width-1))&&!(img.height&(img.height-1));if(soft)gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,soft?gl.LINEAR_MIPMAP_LINEAR:gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);e.t=t;e.ok=true;e.px=[img.width,img.height];V3.tdirty=true}   /* px: a pixel-art picture, drawn smooth but defined (txp) */
// geometry helpers: vertex = p3 n3 uv2 c4
// They push straight into the array with no temporary arrays (the 3D view rebuilds much of this every frame).
const QUV=[0,0,1,0,1,1,0,1],QN0=[0,0,0],QBLK=[0,0,0,1],QUVB=[0,1,1,1,1,0,0,0],QWHITE=[1,1,1,1],V3UNITK=new Set(['mine','npc','player','animal']);   // shared constants: no new arrays per call
function quad(a,p0,p1,p2,p3,n,c,uv){if(!uv)uv=QUV;const nx=n[0],ny=n[1],nz=n[2],r=c[0],g=c[1],b=c[2],al=c[3];if(a instanceof VA){a.v(p0[0],p0[1],p0[2],nx,ny,nz,uv[0],uv[1],r,g,b,al);a.v(p1[0],p1[1],p1[2],nx,ny,nz,uv[2],uv[3],r,g,b,al);a.v(p2[0],p2[1],p2[2],nx,ny,nz,uv[4],uv[5],r,g,b,al);a.v(p0[0],p0[1],p0[2],nx,ny,nz,uv[0],uv[1],r,g,b,al);a.v(p2[0],p2[1],p2[2],nx,ny,nz,uv[4],uv[5],r,g,b,al);a.v(p3[0],p3[1],p3[2],nx,ny,nz,uv[6],uv[7],r,g,b,al);return}a.push(p0[0],p0[1],p0[2],nx,ny,nz,uv[0],uv[1],r,g,b,al,p1[0],p1[1],p1[2],nx,ny,nz,uv[2],uv[3],r,g,b,al,p2[0],p2[1],p2[2],nx,ny,nz,uv[4],uv[5],r,g,b,al,p0[0],p0[1],p0[2],nx,ny,nz,uv[0],uv[1],r,g,b,al,p2[0],p2[1],p2[2],nx,ny,nz,uv[4],uv[5],r,g,b,al,p3[0],p3[1],p3[2],nx,ny,nz,uv[6],uv[7],r,g,b,al)}
function quad4(a,p0,p1,p2,p3,n,c0,c1,c2,c3){const nx=n[0],ny=n[1],nz=n[2],a0=c0[3]===undefined?1:c0[3],a1=c1[3]===undefined?1:c1[3],a2=c2[3]===undefined?1:c2[3],a3=c3[3]===undefined?1:c3[3];if(a instanceof VA){a.v(p0[0],p0[1],p0[2],nx,ny,nz,0,0,c0[0],c0[1],c0[2],a0);a.v(p1[0],p1[1],p1[2],nx,ny,nz,0,0,c1[0],c1[1],c1[2],a1);a.v(p2[0],p2[1],p2[2],nx,ny,nz,0,0,c2[0],c2[1],c2[2],a2);a.v(p0[0],p0[1],p0[2],nx,ny,nz,0,0,c0[0],c0[1],c0[2],a0);a.v(p2[0],p2[1],p2[2],nx,ny,nz,0,0,c2[0],c2[1],c2[2],a2);a.v(p3[0],p3[1],p3[2],nx,ny,nz,0,0,c3[0],c3[1],c3[2],a3);return}a.push(p0[0],p0[1],p0[2],nx,ny,nz,0,0,c0[0],c0[1],c0[2],a0,p1[0],p1[1],p1[2],nx,ny,nz,0,0,c1[0],c1[1],c1[2],a1,p2[0],p2[1],p2[2],nx,ny,nz,0,0,c2[0],c2[1],c2[2],a2,p0[0],p0[1],p0[2],nx,ny,nz,0,0,c0[0],c0[1],c0[2],a0,p2[0],p2[1],p2[2],nx,ny,nz,0,0,c2[0],c2[1],c2[2],a2,p3[0],p3[1],p3[2],nx,ny,nz,0,0,c3[0],c3[1],c3[2],a3)}
function tri(a,p0,p1,p2,n,c){const nx=n[0],ny=n[1],nz=n[2],r=c[0],g=c[1],b=c[2],al=c[3];if(a instanceof VA){a.v(p0[0],p0[1],p0[2],nx,ny,nz,0,0,r,g,b,al);a.v(p1[0],p1[1],p1[2],nx,ny,nz,0,0,r,g,b,al);a.v(p2[0],p2[1],p2[2],nx,ny,nz,0,0,r,g,b,al);return}a.push(p0[0],p0[1],p0[2],nx,ny,nz,0,0,r,g,b,al,p1[0],p1[1],p1[2],nx,ny,nz,0,0,r,g,b,al,p2[0],p2[1],p2[2],nx,ny,nz,0,0,r,g,b,al)}
// a box face from plain numbers (uv 0,1 1,1 1,0 0,0 as box and boxr always used)
function qb(a,x0,y0,z0,x1,y1,z1,x2,y2,z2,x3,y3,z3,nx,ny,nz,c){const r=c[0],g=c[1],b=c[2],al=c[3];if(a instanceof VA){a.v(x0,y0,z0,nx,ny,nz,0,1,r,g,b,al);a.v(x1,y1,z1,nx,ny,nz,1,1,r,g,b,al);a.v(x2,y2,z2,nx,ny,nz,1,0,r,g,b,al);a.v(x0,y0,z0,nx,ny,nz,0,1,r,g,b,al);a.v(x2,y2,z2,nx,ny,nz,1,0,r,g,b,al);a.v(x3,y3,z3,nx,ny,nz,0,0,r,g,b,al);return}a.push(x0,y0,z0,nx,ny,nz,0,1,r,g,b,al,x1,y1,z1,nx,ny,nz,1,1,r,g,b,al,x2,y2,z2,nx,ny,nz,1,0,r,g,b,al,x0,y0,z0,nx,ny,nz,0,1,r,g,b,al,x2,y2,z2,nx,ny,nz,1,0,r,g,b,al,x3,y3,z3,nx,ny,nz,0,0,r,g,b,al)}
// A vertex accumulator kept from frame to frame: push() appends into a Float32Array that only grows, so building a
// frame's geometry makes no new arrays once warm. It has .length like the plain arrays it stands in for.
function VA(){this.f=new Float32Array(4096);this.length=0}
VA.prototype.need=function(n){if(this.length+n>this.f.length){const g=new Float32Array(Math.max(this.f.length*2,this.length+n));g.set(this.f.subarray(0,this.length));this.f=g}};
VA.prototype.push=function(){const n=arguments.length;this.need(n);const f=this.f;let k=this.length;for(let i=0;i<n;i++)f[k++]=arguments[i];this.length=k;return k};
VA.prototype.copy=function(F,o,n){this.need(n);const f=this.f;let k=this.length;for(let i=0;i<n;i++)f[k++]=F[o+i];this.length=k};
VA.prototype.addArr=function(s){const n=s.length;this.need(n);if(s instanceof VA)this.f.set(s.f.subarray(0,n),this.length);else{const f=this.f;let k=this.length;for(let i=0;i<n;i++)f[k++]=s[i]}this.length+=n;return this};
VA.prototype.reset=function(){this.length=0;return this};
// one vertex (p3 n3 uv2 c4) into a VA without an arguments object
VA.prototype.v=function(x,y,z,nx,ny,nz,u,w,r,g,b,al){let k=this.length;if(k+12>this.f.length)this.need(12);const f=this.f;f[k]=x;f[k+1]=y;f[k+2]=z;f[k+3]=nx;f[k+4]=ny;f[k+5]=nz;f[k+6]=u;f[k+7]=w;f[k+8]=r;f[k+9]=g;f[k+10]=b;f[k+11]=al;this.length=k+12};
// Streams vertex data into the bound ARRAY_BUFFER through one reused Float32Array (no new typed array per draw).
function v3up(a){const gl=V3.gl,n=a.length;if(a instanceof VA){gl.bufferData(gl.ARRAY_BUFFER,a.f.subarray(0,n),gl.STREAM_DRAW);return}let S=V3.upS;if(!S||S.length<n)S=V3.upS=new Float32Array(Math.max(n,S?S.length*2:262144));S.set(a);gl.bufferData(gl.ARRAY_BUFFER,S.subarray(0,n),gl.STREAM_DRAW)}
function box(a,x,z,y0,y1,hw,c,sides){boxr(a,x-hw,x+hw,z-hw,z+hw,y0,y1,c,sides)}
function boxr(a,x0,x1,z0,z1,y0,y1,c,s){qb(a,x0,y1,z1,x1,y1,z1,x1,y1,z0,x0,y1,z0,0,1,0,c);
 if(!s||s[0])qb(a,x0,y0,z1,x1,y0,z1,x1,y1,z1,x0,y1,z1,0,0,1,c);if(!s||s[1])qb(a,x1,y0,z0,x0,y0,z0,x0,y1,z0,x1,y1,z0,0,0,-1,c);
 if(!s||s[2])qb(a,x1,y0,z1,x1,y0,z0,x1,y1,z0,x1,y1,z1,1,0,0,c);if(!s||s[3])qb(a,x0,y0,z0,x0,y0,z1,x0,y1,z1,x0,y1,z0,-1,0,0,c)}

