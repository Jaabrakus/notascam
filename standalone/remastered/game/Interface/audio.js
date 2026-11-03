/* Kin & Stone sound (audio session, 2026-10-22). Inlined into the HUD page by HUD.dm (Audio.dm RemasterHUDPage swaps this
   file in for the <!--rm-audio--> marker after the page's main script). The effects and interface sounds are synthesized
   here; the war drums while a fight is near (drum recordings, VSCO 2, played to this file's own patterns) and the user's
   forest track as the ambience bed come from Interface/sounds/ (the server sends them with the page and names them in
   rmSoundFiles; tools/build_audio_assets.py builds them). The synthesized ambience, voices and music below are off (the
   user, 2026-10-23; FEATURES, VOICES_ON). The synth half (rmSynth) is plain JS that also runs in node
   (tools/render_audio.js renders it to WAV for level checks) and seeds a Web Worker. Hooks for other code, all
   harmless when this file is absent:
     window.rmSfx&&rmSfx(name,opts)            a named sound (rmSfx.synth.SND); opts {x,y} places it in the world;
                                               also the moments select | group-set | group-recall | deny (rts-feel)
     window.rmSfx&&rmSfx.order(kind,{x,y})     an order acknowledgement (move|attack|gather|chop|mine|build|craft|deliver|guard|patrol|stop|cast)
     window.rmSfx&&rmSfx.at(name,x,y,info)     a world sound at a tile; 'impact' {k,w,spark}, 'fall' and 'built' {kind} (world-look)
     window.rmSfx&&rmSfx.weather(kind)         rain, storm, snow or null: the ambience follows (the game has no weather yet)
   The engine also reads the page itself (wrapping updateHUD/update3D/send/logPush): hits, specials, block breaks, level-ups,
   notices, units' work, the z level, night, season and the ground round the camera; and it keeps the HUD's other settings
   in the player's profile (the app's web view forgets page storage on quit). ASCII only: HUD.dm inlines it as text. */
(function(G){'use strict';
// The synth: pure functions, no browser needed. Its source also seeds the Web Worker that renders sounds off the page's
// main thread (so a long ambience bed or a music chord never costs the 3D view a frame).
function rmSynth(){'use strict';
const TAU=Math.PI*2;
let SR=44100;
function rng(seed){let a=(seed>>>0)||0x9e3779b9;return function(){a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296}}
function hash(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const lerp=(a,b,t)=>a+(b-a)*t;
const mtof=m=>440*Math.pow(2,(m-69)/12);
const secs=s=>new Float32Array(Math.max(1,Math.ceil(s*SR)));
const pick=(r,a)=>a[Math.floor(r()*a.length)%a.length];
const rr=(r,a,b)=>a+(b-a)*r();

// ---------------------------------------------------------------------------------------------------------------------
// DSP building blocks
// RBJ biquad
function BQ(){this.b0=1;this.b1=this.b2=this.a1=this.a2=0;this.x1=this.x2=this.y1=this.y2=0}
BQ.prototype.set=function(type,f,q,db){f=clamp(f,10,SR*0.47);q=q||0.707;const w=TAU*f/SR,c=Math.cos(w),s=Math.sin(w),al=s/(2*q);let b0,b1,b2,a0,a1,a2;
 if(type==='lp'){b0=(1-c)/2;b1=1-c;b2=b0;a0=1+al;a1=-2*c;a2=1-al}
 else if(type==='hp'){b0=(1+c)/2;b1=-(1+c);b2=b0;a0=1+al;a1=-2*c;a2=1-al}
 else if(type==='bp'){b0=al;b1=0;b2=-al;a0=1+al;a1=-2*c;a2=1-al}
 else{const A=Math.pow(10,(db||0)/40);
  if(type==='pk'){b0=1+al*A;b1=-2*c;b2=1-al*A;a0=1+al/A;a1=-2*c;a2=1-al/A}
  else{const sq=2*Math.sqrt(A)*al;
   if(type==='ls'){b0=A*((A+1)-(A-1)*c+sq);b1=2*A*((A-1)-(A+1)*c);b2=A*((A+1)-(A-1)*c-sq);a0=(A+1)+(A-1)*c+sq;a1=-2*((A-1)+(A+1)*c);a2=(A+1)+(A-1)*c-sq}
   else{b0=A*((A+1)+(A-1)*c+sq);b1=-2*A*((A-1)+(A+1)*c);b2=A*((A+1)+(A-1)*c-sq);a0=(A+1)-(A-1)*c+sq;a1=2*((A-1)-(A+1)*c);a2=(A+1)-(A-1)*c-sq}}}
 this.b0=b0/a0;this.b1=b1/a0;this.b2=b2/a0;this.a1=a1/a0;this.a2=a2/a0;return this};
BQ.prototype.run=function(x){const y=this.b0*x+this.b1*this.x1+this.b2*this.x2-this.a1*this.y1-this.a2*this.y2;this.x2=this.x1;this.x1=x;this.y2=this.y1;this.y1=y;return y};
function filt(a,t,f,q,db){const F=new BQ().set(t,f,q,db);for(let i=0;i<a.length;i++)a[i]=F.run(a[i]);return a}
// a filter whose frequency follows fn(0..1) over the buffer (coefficients every 32 samples)
function sweep(a,t,fn,q,db){const F=new BQ(),n=a.length;for(let i=0;i<n;i++){if((i&31)===0)F.set(t,fn(i/n),q,db);a[i]=F.run(a[i])}return a}
// two-pole resonator with unity gain at DC (formants, bodies)
function Res(){this.a=1;this.b=0;this.c=0;this.y1=0;this.y2=0}
Res.prototype.set=function(f,bw){const r=Math.exp(-Math.PI*bw/SR);this.c=-r*r;this.b=2*r*Math.cos(TAU*Math.min(f,SR*0.45)/SR);this.a=1-this.b-this.c;return this};
Res.prototype.run=function(x){const y=this.a*x+this.b*this.y1+this.c*this.y2;this.y2=this.y1;this.y1=y;return y};

function noise(n,r,col){const a=new Float32Array(Math.max(1,Math.ceil(n)));let b0=0,b1=0,b2=0,br=0;
 for(let i=0;i<a.length;i++){const w=r()*2-1;
  if(col==='p'){b0=0.99765*b0+w*0.0990460;b1=0.96300*b1+w*0.2965164;b2=0.57000*b2+w*1.0526913;a[i]=(b0+b1+b2+w*0.1848)*0.22}
  else if(col==='b'){br=(br+w*0.03)*0.997;a[i]=br*2.2}
  else a[i]=w}return a}
function mix(dst,src,at,g){at=Math.round(at);g=g==null?1:g;const n=Math.min(src.length,dst.length-at);for(let i=Math.max(0,-at);i<n;i++)dst[at+i]+=src[i]*g;return dst}
function scale(a,g){for(let i=0;i<a.length;i++)a[i]*=g;return a}
// envelope: linear attack (s), exponential decay to -60 dB in t60 (s)
function env(a,att,t60,hold){const na=Math.max(1,Math.round(att*SR)),nh=Math.round((hold||0)*SR),k=Math.exp(-6.9078/(Math.max(0.001,t60)*SR));let e=1;
 for(let i=0;i<a.length;i++){if(i<na)a[i]*=i/na;else if(i<na+nh);else{e*=k;a[i]*=e}}return a}
// shape by a function of t (0..1)
function shape(a,fn){const n=a.length;for(let i=0;i<n;i++)a[i]*=fn(i/n);return a}
function fadeEdges(a,fin,fout){const ni=Math.round(fin*SR),no=Math.round(fout*SR),n=a.length;for(let i=0;i<ni&&i<n;i++)a[i]*=i/ni;for(let i=0;i<no&&i<n;i++)a[n-1-i]*=i/no;return a}
function softclip(a,drive){const k=Math.tanh(drive);for(let i=0;i<a.length;i++)a[i]=Math.tanh(a[i]*drive)/k;return a}
// damped sinusoids: [freq, t60, amp, phase]
function modal(dst,at,modes,g,att){at=Math.round(at);g=g==null?1:g;const na=Math.max(1,Math.round((att||0.0006)*SR));
 for(const m of modes){const f=m[0];if(f<=0||f>=SR*0.47)continue;const k=Math.exp(-6.9078/(m[1]*SR)),w=TAU*f/SR;let e=m[2]*g,p=m[3]||0;const n=Math.min(dst.length-at,Math.ceil(m[1]*SR*1.1));
  for(let i=0;i<n;i++){dst[at+i]+=Math.sin(p)*e*(i<na?i/na:1);p+=w;e*=k}}return dst}
// a pitch-dropping sine thump (kick-drum style): body of impacts and drums
function thump(dst,at,f0,f1,t60,g,drop){at=Math.round(at);const n=Math.min(dst.length-at,Math.ceil(t60*SR*1.1)),k=Math.exp(-6.9078/(t60*SR));let p=0,e=g==null?1:g;const dk=drop||0.03;
 for(let i=0;i<n;i++){const t=i/SR,f=f1+(f0-f1)*Math.exp(-t/dk);p+=TAU*f/SR;dst[at+i]+=Math.sin(p)*e*(i<24?i/24:1);e*=k}return dst}
// filtered noise burst
function burst(dst,at,dur,r,type,f,q,att,t60,g,col){const b=noise(dur*SR,r,col);filt(b,type,f,q);env(b,att,t60);return mix(dst,b,at*SR,g)}
// rushing air: band-pass noise swept low > peak > end, swelling to peakAt
function whoosh(dur,r,f0,fpk,f1,q,peakAt,col){const n=noise(dur*SR,r,col||'w');peakAt=peakAt||0.55;
 sweep(n,'bp',t=>t<peakAt?lerp(f0,fpk,Math.pow(t/peakAt,0.7)):lerp(fpk,f1,(t-peakAt)/(1-peakAt)),q);
 return shape(n,t=>t<peakAt?Math.pow(t/peakAt,2.2):Math.pow(1-(t-peakAt)/(1-peakAt),1.8))}
// Karplus-Strong plucked string with a tuned fractional delay; t60 in seconds, bright 0..1, pos = pluck position
function pluck(f,dur,o){o=o||{};const r=o.r||Math.random,out=secs(dur),N=SR/f-0.5,L=Math.max(2,Math.floor(N)),frac=N-L,C=(1-frac)/(1+frac),buf=new Float32Array(L);
 let lp=0;const br=o.bright==null?0.5:o.bright;for(let i=0;i<L;i++){lp+=(r()*2-1-lp)*(0.08+0.9*br);buf[i]=lp}
 if(o.pos){const d=Math.max(1,Math.round(L*o.pos));for(let i=L-1;i>=d;i--)buf[i]-=buf[i-d]}
 let mean=0;for(let i=0;i<L;i++)mean+=buf[i];mean/=L;for(let i=0;i<L;i++)buf[i]-=mean;
 const rho=Math.pow(10,-3/((o.t60||1.5)*f));let idx=0,apx=0,apy=0,prev=buf[L-1];
 for(let n=0;n<out.length;n++){const x=buf[idx];out[n]=x;const y=rho*0.5*(x+prev);prev=x;const ap=C*y+apx-C*apy;apx=y;apy=ap;buf[idx]=ap;idx=idx+1===L?0:idx+1}
 return out}
// a lute: pluck + soft pick click + wooden body
function lute(f,dur,r,o){o=o||{};const s=pluck(f,dur,{r,t60:o.t60||1.4,bright:o.bright==null?0.55:o.bright,pos:o.pos||0.17});
 const b1=new Res().set(150,50),b2=new Res().set(290,70),b3=new Res().set(560,110),out=secs(dur);
 for(let i=0;i<s.length;i++){const x=s[i];out[i]=x*0.8+(b1.run(x)*0.5+b2.run(x)*0.35+b3.run(x)*0.25)}
 burst(out,0,0.006,r,'hp',2500,0.7,0.0005,0.004,0.12);return fadeEdges(out,0,0.08)}
// band-limited sawtooth (polyBLEP): no aliasing whistle on high notes
function blep(t,dt){if(t<dt){t/=dt;return t+t-t*t-1}if(t>1-dt){t=(t-1)/dt;return t*t+t+t+1}return 0}
function saw(p,dt){return 2*p-1-blep(p,dt)}
// a soft brass voice: saw harmonics through an opening filter, with vibrato
function brass(f,dur,r,o){o=o||{};const out=secs(dur),n=out.length,F=new BQ(),F2=new BQ();let p1=0,p2=0,p3=0;const det=1.003,vibD=o.vib==null?0.006:o.vib,att=o.att||0.06,bright=o.bright||2200;
 for(let i=0;i<n;i++){const t=i/SR,tt=i/n;const vib=1+vibD*Math.sin(TAU*5.2*t)*Math.min(1,t/0.25);
  const fq=f*vib*(1+(o.glide||0)*Math.exp(-t/0.05));p1+=fq/SR;p2+=fq*det/SR;p3+=fq/det/SR;p1-=Math.floor(p1);p2-=Math.floor(p2);p3-=Math.floor(p3);
  const x=saw(p1,fq/SR)+saw(p2,fq*det/SR)*0.7+saw(p3,fq/det/SR)*0.5;
  const a=t<att?t/att:1,rel=tt>0.85?(1-tt)/0.15:1,amp=a*rel*(0.85+0.15*Math.sin(TAU*0.7*t));
  if((i&31)===0){F.set('lp',300+bright*Math.min(1,t/(att*1.6))*(0.75+0.25*a)*(1-0.3*tt),1.1);F2.set('pk',o.formant||1100,1.2,5)}
  out[i]=F2.run(F.run(x))*amp*0.3}
 return out}
// a hand bell / church bell: hum, prime, minor third, fifth, nominal and upper partials
function bell(dst,at,f,t60,g,r){const P=[[0.5,1.25,0.35],[1,1,1],[1.19,0.8,0.42],[1.5,0.7,0.28],[2,0.55,0.5],[2.51,0.4,0.18],[2.66,0.35,0.13],[3.01,0.3,0.1],[4.17,0.22,0.06]];
 return modal(dst,at,P.map(([k,tt,a])=>[f*k*(1+(r()-0.5)*0.002),t60*tt,a,r()*TAU]),g,0.0015)}
// the space a short sound sits in, baked lightly into a few renders (the engine adds a real reverb)
function roomTail(a,amt,len,r){const n=Math.round(len*SR),out=new Float32Array(a.length+n);out.set(a);
 const taps=[[0.013,0.5],[0.021,0.4],[0.033,0.3],[0.047,0.22],[0.061,0.16]];for(const [d,g] of taps)mix(out,a,d*SR,g*amt*(0.8+0.4*r()));
 const tail=noise(n,r,'w');filt(tail,'lp',2500,0.7);env(tail,0.01,len);let e=0;for(let i=0;i<a.length;i++)e+=a[i]*a[i];e=Math.sqrt(e/Math.max(1,a.length));
 return mix(out,tail,Math.round(0.02*SR),e*amt*0.35)}

// ---------------------------------------------------------------------------------------------------------------------
// Voices: a small formant synthesizer speaking gibberish with a race's voice (glottal pulse > cascade formants)
const VOW={a:[730,1090,2440,3400],e:[530,1840,2480,3500],i:[300,2200,2950,3600],o:[570,840,2410,3300],u:[330,880,2240,3300],'@':[500,1400,2450,3400],A:[660,1700,2400,3400],V:[640,1190,2390,3400],O:[590,880,2540,3400]};
const DIPH={a:['i','u'],e:['i'],o:['u'],O:['i'],A:['i'],V:['u','i'],'@':['u'],u:['@'],i:['@']};
const RACE={
 human:{f0:122,vt:1,breath:0.08,growl:0,nasal:0,jit:0.012,rate:1,cons:'hhymgnbd',vow:'aeoVA@'},
 dwarf:{f0:96,vt:0.9,breath:0.06,growl:0.2,nasal:0,jit:0.02,rate:0.95,cons:'hrgbmd',vow:'oaVuO',fx:'slap'},
 elf:{f0:176,vt:1.1,breath:0.3,growl:0,nasal:0,jit:0.006,rate:0.82,cons:'hylnm',vow:'eai@A',fx:'chorus'},
 orc:{f0:80,vt:0.85,breath:0.1,growl:0.55,nasal:0,jit:0.03,rate:1,cons:'grhkdb',vow:'aoVO',drive:2.2},
 goblin:{f0:240,vt:1.24,breath:0.1,growl:0.05,nasal:0.6,jit:0.025,rate:1.35,cons:'nykhs',vow:'eiaA'},
 kobold:{f0:315,vt:1.34,breath:0.08,growl:0.12,nasal:0.3,jit:0.03,rate:1.5,cons:'yrkt',vow:'iaeA'},
 lizardman:{f0:104,vt:0.95,breath:0.25,growl:0.2,nasal:0,jit:0.02,rate:0.9,cons:'sshk',vow:'aeA',hiss:0.7},
 frogman:{f0:90,vt:0.9,breath:0.1,growl:0.35,nasal:0.2,jit:0.03,rate:1.1,cons:'brgm',vow:'uoO',croak:1},
 zombie:{f0:72,vt:0.88,breath:0.45,growl:0.3,nasal:0,jit:0.05,rate:0.6,cons:'hm',vow:'uoV',fx:'ring'},
 vampire:{f0:108,vt:0.98,breath:0.5,growl:0,nasal:0,jit:0.008,rate:0.8,cons:'hsml',vow:'ae@',fx:'ring'},
 dragon:{f0:52,vt:0.68,breath:0.3,growl:0.8,nasal:0,jit:0.04,rate:0.7,cons:'grh',vow:'aoO',drive:3,fx:'octave'},
 skeleton:{bones:1},spider:{chitter:1}};
const RACE_OF={human:'human',dwarf:'dwarf',elf:'elf',svartalfar:'elf',orc:'orc','half-demon':'orc',demon:'orc',werewolf:'orc',gargoyle:'dwarf',goblin:'goblin',gremlin:'goblin',kobold:'kobold',ratman:'kobold',lizardman:'lizardman',frogman:'frogman',zombie:'zombie',ghoul:'zombie',vampire:'vampire',illithid:'vampire',dragon:'dragon',skeleton:'skeleton',spider:'spider',sandking:'spider',queen:'spider',worker:'spider',warrior:'spider',devourer:'dragon'};   // races without a voice of their own borrow the nearest
function raceKey(race){const k=String(race||'').toLowerCase();return RACE_OF[k]||(RACE[k]?k:'human')}
// consonant targets: formants (or null = the vowel's), voicing, aspiration, frication (amp, Hz), seconds
const CONS={h:[null,0,0.9,0,0,0.05],y:[VOW.i,0.7,0,0,0,0.06],m:[[260,1000,2300,3300],0.45,0,0,0,0.07],n:[[260,1450,2500,3400],0.45,0,0,0,0.065],l:[[360,1050,2650,3400],0.6,0,0,0,0.05],
 r:[[450,1200,1700,3200],0.7,0,0,0,0.07],g:[[300,1900,2400,3400],0.25,0.1,0.35,1800,0.03],b:[[250,800,2200,3300],0.3,0.05,0.25,700,0.03],d:[[300,1700,2600,3400],0.25,0.1,0.35,3200,0.03],
 k:[null,0,0.5,0.8,2200,0.05],t:[null,0,0.45,0.75,4300,0.045],s:[null,0,0.05,0.7,5600,0.09]};
// syllable plans: [count, contour]; contours: q question, s statement, x shout, m mm-hm, f flat, d death, h hurt, c cheer
const VPLAN={select:[[1,'q'],[2,'q']],move:[[1,'s'],[2,'s']],attack:[[1,'x'],[2,'x']],work:[[2,'m']],build:[[2,'s'],[1,'s']],deliver:[[1,'s']],guard:[[1,'x']],stop:[[1,'f']],cast:[[2,'x']],death:[[1,'d']],hurt:[[1,'h']],cheer:[[1,'c']]};
function contour(c,t,k,n){// pitch multiplier at t (0..1) within syllable k of n
 if(c==='q')return k<n-1?1.0:lerp(0.96,1.32,Math.pow(t,1.6));
 if(c==='x')return k===0?lerp(1.35,1.45,t):lerp(1.4,1.05,t);
 if(c==='m')return k===0?1.0:lerp(1.18,0.94,t);
 if(c==='f')return lerp(1.0,0.86,t);
 if(c==='d')return lerp(1.35,0.55,Math.pow(t,0.8));
 if(c==='h')return lerp(1.4,1.1,t);
 if(c==='c')return lerp(1.1,1.5,Math.pow(t,0.6));
 return k===0&&n>1?lerp(1.08,1.04,t):lerp(1.1,0.8,t)}
// Rosenberg glottal pulse (open/closing phases)
function glottis(ph,op,cl){return ph<op?0.5*(1-Math.cos(Math.PI*ph/op)):ph<op+cl?Math.cos(Math.PI*(ph-op)/(2*cl)):0}
function voiceLine(race,gender,kind,variant,prof){const key=raceKey(race),P=prof||RACE[key],r=rng(hash(key+'|'+gender+'|'+kind+'|'+variant));
 if(P.bones)return bonesVoice(kind,r);if(P.chitter)return chitterVoice(kind,r);
 const fem=gender==='f'&&key!=='dragon',f0b=P.f0*(fem?1.65:1)*rr(r,0.94,1.06),vt=P.vt*(fem?1.15:1),rate=P.rate;
 const plan=pick(r,VPLAN[kind]||VPLAN.move),n=plan[0],cont=plan[1];
 // segments: {F,av,ah,af,ft,dur,syl,k}
 const seg=[];const loud=cont==='x'?1.0:cont==='d'?0.9:0.8;
 for(let k=0;k<n;k++){let c=pick(r,P.cons),v=pick(r,P.vow);
  if(cont==='m'){c=k===0?'m':'h';v=k===0?'@':pick(r,P.vow)}
  if(cont==='d'){c=pick(r,'hg');v=pick(r,'aV')}
  if(cont==='x'&&k===0&&P.cons.indexOf('r')>=0&&r()<0.5)c='g';
  const V=VOW[v],C=CONS[c];
  const vd=(cont==='d'?0.62:cont==='x'?(k===n-1?0.26:0.12):cont==='m'?(k===0?0.16:0.2):cont==='q'&&k===n-1?0.2:n>1&&k<n-1?0.1:0.17)*rr(r,0.9,1.15)/rate;
  if(C){seg.push({F:C[0]||V,av:C[1]*loud,ah:C[2]*loud,af:C[3]*loud,ft:C[4],dur:C[5]/Math.sqrt(rate),k,n,c,cv:0});
   if(c==='k'||c==='t')seg.push({F:V,av:0,ah:0.45*loud,af:0,ft:0,dur:0.03/rate,k,n,c,cv:0})}
  // a vowel may glide into another (aye, oh, ow): real speech never holds still
  const dip=cont!=='m'&&cont!=='d'&&r()<0.45?pick(r,DIPH[v]||['@']):null;
  if(P.hiss&&k===n-1&&r()<P.hiss){seg.push({F:V,av:loud,ah:P.breath,af:0,ft:0,dur:vd*0.7,vd:vd*0.7,k,n,cv:1,c:''});seg.push({F:V,av:0.1,ah:0.1,af:0.6*loud,ft:5200,dur:0.12/rate,k,n,cv:0,c:'s'})}
  else if(dip){seg.push({F:V,av:loud,ah:P.breath*loud,af:0,ft:0,dur:vd*0.55,vd,k,n,cv:1,c:''});seg.push({F:VOW[dip],av:loud,ah:P.breath*loud,af:0,ft:0,dur:vd*0.45,vd,k,n,cv:2,glide:1,c:''})}
  else seg.push({F:V,av:loud,ah:P.breath*loud,af:0,ft:0,dur:vd,vd,k,n,cv:1,c:''});
  if(k<n-1)seg.push({F:V,av:0.0,ah:0.02,af:0,ft:0,dur:0.03/rate,k,n,cv:0,c:''})}
 seg.push({F:seg[seg.length-1].F,av:0,ah:0,af:0,ft:0,dur:0.06,k:n-1,n,cv:0,c:''});
 let total=0;for(const s of seg)total+=s.dur;const out=secs(total+0.08),N=out.length;
 const R=[new Res(),new Res(),new Res(),new Res()],nasR=new Res().set(270,100),fric=new BQ(),tilt=[0,0];
 const bw=[70,90,140,200].map(b=>b*(1+P.breath*0.8));
 let si=0,segStart=0,segEnd=seg[0].dur*SR;let F=seg[0].F.map(x=>x*vt),av=0,ah=0,af=0,ft=seg[0].ft||3000;let ph=0,per=0,shim=1,gprev=0,jit=0,jt=0;
 const sm=Math.exp(-1/(0.012*SR)),smG=Math.exp(-1/(0.045*SR)),sa=Math.exp(-1/(0.006*SR)),growlF=rr(r,28,42);let lpS=0,sylStart=0;
 for(let i=0;i<N;i++){
  while(i>=segEnd&&si<seg.length-1){si++;segStart=segEnd;segEnd+=seg[si].dur*SR;if(seg[si].cv===1)sylStart=segStart}
  const S=seg[si];
  const smx=S.glide?smG:sm;for(let j=0;j<4;j++)F[j]=F[j]*smx+S.F[j]*vt*(1-smx);
  av=av*sa+S.av*(1-sa);ah=ah*sa+S.ah*(1-sa);af=af*sa+S.af*(1-sa);if(S.ft)ft=S.ft;
  if((i&15)===0){for(let j=0;j<4;j++)R[j].set(F[j],bw[j]);if(af>0.001)fric.set('bp',ft*Math.sqrt(vt),1.4)}
  // pitch: the syllable's contour, a slow drift and jitter
  const vowT=S.cv?clamp((i-sylStart)/Math.max(1,S.vd*SR),0,1):(S.k<S.n-1?1:0);
  // each syllable swells in and eases off
  const avE=av*(S.cv?Math.min(1,0.55+vowT/0.12*0.45)*(vowT>0.65?1-(vowT-0.65)/0.35*0.55:1):1);
  if((i&63)===0){jt=jit;jit=(r()*2-1)*P.jit}
  const f0=f0b*contour(cont,vowT,S.k,S.n)*(1+lerp(jt,jit,(i&63)/64))*(1+0.004*Math.sin(TAU*4.5*i/SR));
  ph+=f0/SR;if(ph>=1){ph-=1;per++;shim=1+(r()*2-1)*0.06*(1+P.growl);if(P.growl&&(per&1))shim*=1-P.growl*0.45}
  const g=glottis(ph,0.42,0.16),dg=(g-gprev)*SR/f0*0.18;gprev=g;
  let vo=dg*shim;if(P.growl)vo*=1-P.growl*0.4*(0.5+0.5*Math.sin(TAU*growlF*i/SR));if(P.croak)vo*=0.35+0.65*(0.5+0.5*Math.sin(TAU*14*i/SR));
  // spectral tilt: breathy voices are darker
  lpS+=(vo-lpS)*(0.55-0.3*P.breath);vo=lpS;
  const wn=r()*2-1;const asp=wn*(ah+P.breath*avE*(0.35+0.65*g))*0.5;
  let x=avE*vo+asp;for(let j=0;j<4;j++)x=R[j].run(x);
  if(P.nasal||S.c==='m'||S.c==='n'){const nz=nasR.run(avE*vo)*(P.nasal+(S.c==='m'||S.c==='n'?0.8:0));x=x*(1-0.4*P.nasal)+nz*1.2}
  if(af>0.001)x+=fric.run(wn)*af*0.9;
  out[i]=x}
 let o=filt(out,'hp',70,0.7);if(P.drive)softclip(scale(o,1/Math.max(1e-6,peakOf(o))),P.drive);
 // a dragon speaks with a second voice an octave under the first: the same line again from the same seed, half the pitch
 if(P.fx==='octave'){const lo=voiceLine(race,gender,kind,variant,Object.assign({},P,{f0:P.f0*0.5,fx:null,drive:0}));mix(o,filt(lo,'lp',900,0.7),0,0.5);return o}
 return voiceFx(o,P.fx,r)}
// each people's voice gets a touch of character: the undead a ring-modulated shimmer, elves a soft chorus, dwarves a short
// slap off the stone (dragons' octave layer is made in voiceLine)
function voiceFx(a,fx,r){if(!fx)return a;const n=a.length,o=new Float32Array(n+Math.round(0.08*SR));o.set(a);
 if(fx==='ring'){const f=rr(r,32,48);for(let i=0;i<n;i++)o[i]=a[i]*(0.7+0.3*Math.sin(TAU*f*i/SR))}
 else if(fx==='chorus'){for(const [d,dep,rate,g] of [[0.012,0.002,0.7,0.35],[0.019,0.003,0.45,0.3]])for(let i=0;i<o.length;i++){const s=i-(d+dep*Math.sin(TAU*rate*i/SR))*SR,j=Math.floor(s),fr=s-j;if(j>=0&&j+1<n)o[i]+=(a[j]*(1-fr)+a[j+1]*fr)*g}}
 else if(fx==='slap'){const d=Math.round(0.055*SR);for(let i=d;i<o.length;i++)if(i-d<n)o[i]+=a[i-d]*0.18}
 return o}
function bonesVoice(kind,r){const out=secs(0.5);const n=kind==='death'?14:kind==='attack'?7:4+Math.floor(r()*3);
 for(let k=0;k<n;k++){const t=(kind==='death'?k*0.035:r()*0.28)+0.01,f=rr(r,700,1700);modal(out,t*SR,[[f,0.035,1],[f*2.3,0.02,0.4]],rr(r,0.4,1))}
 const br=noise(0.32*SR,r,'w');sweep(br,'bp',t=>lerp(900,1600,t),2);env(br,0.08,0.3);mix(out,br,0.02*SR,0.25);return out}
function chitterVoice(kind,r){const out=secs(0.45);const n=kind==='attack'?16:9;for(let k=0;k<n;k++){modal(out,(k*0.022+r()*0.008)*SR,[[rr(r,2500,4200),0.012,1]],rr(r,0.4,1))}
 const h=noise(0.35*SR,r,'w');filt(h,'hp',4000,0.7);env(h,0.04,0.3);mix(out,h,0.05*SR,0.2);return out}

// ---------------------------------------------------------------------------------------------------------------------
// The sound book: name -> {cat, gain, vars, gap (ms between starts), max (voices at once), lvl (loudness), sr, gen(r,v)}
// cat: fx effects (in the world), ui interface, vo voices, amb ambience, mus music
const SND={};
function def(name,cat,o,gen){SND[name]=Object.assign({cat,gain:1,vars:3,gap:45,max:4,lvl:0.7,sr:44100,jit:0.035,spatial:cat==='fx'||cat==='amb'},o,{gen})}
function peakOf(a){let m=0;for(let i=0;i<a.length;i++){const v=Math.abs(a[i]);if(v>m)m=v}return m}
// loudness: the loudest 50 ms RMS window
function stRMS(a,sr){const w=Math.max(1,Math.round(0.05*(sr||SR)));let best=0,acc=0;for(let i=0;i<a.length;i++){acc+=a[i]*a[i];if(i>=w)acc-=a[i-w]*a[i-w];if(i>=w-1||i===a.length-1){const v=acc/Math.min(w,i+1);if(v>best)best=v}}return Math.sqrt(Math.max(0,best))}
// finish a one-shot: DC out, edges, even loudness (lvl 1 = -12 dBFS short-term RMS), peaks under -1 dBFS, silence trimmed
function finish(chs,lvl){chs=Array.isArray(chs)?chs:[chs];for(const a of chs){filt(a,'hp',22,0.7)}
 let rmsv=0,pk=0;for(const a of chs){rmsv=Math.max(rmsv,stRMS(a));pk=Math.max(pk,peakOf(a))}
 let g=rmsv>0?(0.25*lvl)/rmsv:1;if(pk*g>0.89)g=0.89/pk;
 let end=0;for(const a of chs){scale(a,g);for(let i=a.length-1;i>end;i--)if(Math.abs(a[i])>0.0003){end=i;break}}
 end=Math.min(chs[0].length,end+Math.round(0.01*SR));
 return chs.map(a=>fadeEdges(a.length>end?a.slice(0,end):a,0.0008,0.006))}

// --- Interface: wood, leather, parchment and bells ---
def('ui.hover','ui',{gain:0.32,vars:4,gap:40,max:2,lvl:0.5},(r)=>{const a=secs(0.04),f=rr(r,1700,2100);modal(a,0,[[f,0.008,1],[f*2.31,0.005,0.5],[f*3.7,0.004,0.25]]);burst(a,0,0.003,r,'bp',3500,0.9,0.0002,0.0025,0.7);return a});
def('ui.click','ui',{gain:0.42,vars:4,gap:30,max:3,lvl:0.62},(r)=>{const a=secs(0.14),f=rr(r,980,1220);modal(a,0,[[f,0.045,1],[f*2.41,0.025,0.42],[f*0.52,0.06,0.35],[f*3.9,0.012,0.15]]);burst(a,0,0.003,r,'bp',3200,0.9,0.0002,0.0025,0.5);thump(a,0,190,120,0.035,0.25);return a});
def('ui.open','ui',{gain:0.5,vars:3,gap:90,max:2,lvl:0.55},(r)=>{const d=0.34,a=secs(d+0.05),n=noise(d*SR,r,'w'),cr=noise(d*SR,r,'w');filt(cr,'lp',45,0.7);
 for(let i=0;i<n.length;i++)n[i]*=0.35+Math.min(1.6,Math.abs(cr[i])*9);sweep(n,'bp',t=>lerp(800,2900,Math.pow(t,0.8)),0.9);shape(n,t=>t<0.55?Math.pow(t/0.55,1.4):Math.pow(1-(t-0.55)/0.45,1.3));
 mix(a,n,0,1);thump(a,0,130,72,0.09,0.8);modal(a,0.24*SR,[[rr(r,560,660),0.05,0.25],[rr(r,1300,1450),0.03,0.12]]);return filt(a,'lp',4200,0.6)});
def('ui.close','ui',{gain:0.45,vars:3,gap:90,max:2,lvl:0.5},(r)=>{const d=0.22,a=secs(d+0.12),n=noise(d*SR,r,'w'),cr=noise(d*SR,r,'w');filt(cr,'lp',50,0.7);
 for(let i=0;i<n.length;i++)n[i]*=0.35+Math.min(1.6,Math.abs(cr[i])*9);sweep(n,'bp',t=>lerp(2600,850,t),0.9);shape(n,t=>t<0.3?t/0.3:Math.pow(1-(t-0.3)/0.7,1.5));
 mix(a,n,0,1);thump(a,0.17*SR,120,66,0.08,0.9);modal(a,0.17*SR,[[rr(r,480,560),0.05,0.3]]);return filt(a,'lp',4000,0.6)});
def('ui.tab','ui',{gain:0.42,vars:4,gap:50,max:2,lvl:0.5},(r)=>{const a=secs(0.13);for(const [t,g] of [[0,1],[0.045,0.7]]){const n=noise(0.03*SR,r,'w');filt(n,'bp',rr(r,2100,2800),1.1);env(n,0.004,0.025);mix(a,n,t*SR,g)}modal(a,0.04*SR,[[rr(r,1450,1650),0.025,0.25]]);return filt(a,'lp',4500,0.6)});
def('ui.error','ui',{gain:0.5,vars:2,gap:250,max:1,lvl:0.6},(r)=>{const a=secs(0.32);modal(a,0,[[190,0.08,1],[430,0.045,0.4],[95,0.06,0.3]]);modal(a,0.12*SR,[[150,0.1,1],[338,0.05,0.4],[75,0.07,0.3]]);burst(a,0,0.01,r,'lp',600,0.7,0.0005,0.008,0.4);burst(a,0.12,0.01,r,'lp',500,0.7,0.0005,0.008,0.4);return filt(a,'lp',2400,0.7)});
def('ui.notify','ui',{gain:0.45,vars:2,gap:400,max:1,lvl:0.42},(r)=>{const a=secs(1.7);bell(a,0,1318.5,1.1,1,r);bell(a,0.13*SR,987.8,1.3,0.85,r);return filt(a,'lp',7000,0.7)});
def('ui.warn','ui',{gain:0.5,vars:2,gap:3000,max:1,lvl:0.5},(r)=>{const a=secs(3.0);bell(a,0,rr(r,318,334),2.6,1,r);thump(a,0,70,48,0.4,0.2);return a});
def('ui.levelup','ui',{gain:0.55,vars:2,gap:1200,max:1,lvl:0.55},(r)=>{const a=secs(2.6),notes=[72,74,76,79,81,84,86,88];notes.forEach((m,k)=>mix(a,pluck(mtof(m),1.9,{r,t60:1.6,bright:0.75,pos:0.12}),k*0.055*SR,0.55+k*0.04));
 const t=notes.length*0.055+0.05;bell(a,t*SR,mtof(91),1.4,0.35,r);bell(a,(t+0.07)*SR,mtof(96),1.2,0.25,r);return filt(a,'hp',180,0.7)});
def('ui.milestone','ui',{gain:0.55,vars:1,gap:2000,max:1,lvl:0.6},(r)=>{const a=secs(2.2),seq=[[67,0,0.2],[72,0.2,0.2],[76,0.4,0.2],[79,0.6,1.3]];for(const [m,t,d] of seq)mix(a,brass(mtof(m),d+0.1,r,{att:0.03,bright:2600,vib:t>0.5?0.008:0.003}),t*SR,1);
 thump(a,0,90,55,0.5,0.5);thump(a,0.6*SR,90,55,0.7,0.6);bell(a,0.6*SR,mtof(91),1.3,0.18,r);return a});
def('ui.alert','ui',{gain:0.6,vars:1,gap:20000,max:1,lvl:0.65},(r)=>{const a=secs(2.9);mix(a,brass(110,1.0,r,{att:0.12,bright:900,formant:520,vib:0.004,glide:-0.03}),0,1);mix(a,brass(146.8,1.6,r,{att:0.1,bright:1000,formant:520,vib:0.006}),0.95*SR,1);
 for(const t of [0,0.95,1.45]){thump(a,t*SR,62,42,0.55,0.9);burst(a,t,0.08,r,'lp',300,0.7,0.002,0.12,0.35)}return a});
def('ui.place','ui',{gain:0.5,vars:3,gap:80,max:2,lvl:0.55},(r)=>{const a=secs(0.3),f=rr(r,220,260);modal(a,0,[[f,0.09,1],[f*2.6,0.05,0.5],[f*4.1,0.03,0.2]]);thump(a,0,110,60,0.08,0.7);burst(a,0,0.02,r,'bp',1500,0.8,0.001,0.02,0.25);return a});
def('ui.birth','ui',{gain:0.42,vars:2,gap:2000,max:1,lvl:0.45},(r)=>{const a=secs(2.2);[76,79,84].forEach((m,k)=>mix(a,pluck(mtof(m),1.8,{r,t60:1.8,bright:0.6,pos:0.25}),k*0.16*SR,0.8));bell(a,0.5*SR,mtof(96),1.2,0.15,r);return filt(a,'hp',200,0.7)});
def('ui.coins','ui',{gain:0.45,vars:3,gap:200,max:1,lvl:0.5},(r)=>{const a=secs(0.6);const n=5+Math.floor(r()*4);for(let k=0;k<n;k++){const t=r()*0.3,f=rr(r,2800,5200);modal(a,t*SR,[[f,0.12,1],[f*1.47,0.08,0.5],[f*2.13,0.05,0.3]],rr(r,0.3,1))}return a});
def('ui.save','ui',{gain:0.4,vars:1,gap:1000,max:1,lvl:0.45},(r)=>{const a=secs(1.0);mix(a,lute(mtof(74),0.9,r,{bright:0.6}),0,0.8);mix(a,lute(mtof(81),0.9,r,{bright:0.6}),0.09*SR,0.7);return a});
def('ui.aim','ui',{gain:0.4,vars:2,gap:300,max:1,lvl:0.5},(r)=>{const a=secs(0.7);for(let k=0;k<4;k++){const f=mtof(pick(r,[79,83,86,88,91]));modal(a,k*0.05*SR,[[f,0.5,0.6],[f*2.01,0.3,0.2]])}const w=whoosh(0.4,r,1500,5000,3000,1.5,0.6);mix(a,w,0,0.25);return a});
def('ui.pause','ui',{gain:0.45,vars:1,gap:300,max:1,lvl:0.5},(r)=>{const a=secs(0.5);modal(a,0,[[440,0.12,1],[1050,0.06,0.3]]);modal(a,0.11*SR,[[330,0.16,1],[790,0.08,0.3]]);return filt(a,'lp',3000,0.7)});
def('ui.resume','ui',{gain:0.45,vars:1,gap:300,max:1,lvl:0.5},(r)=>{const a=secs(0.5);modal(a,0,[[330,0.1,1],[790,0.05,0.3]]);modal(a,0.1*SR,[[495,0.16,1],[1180,0.08,0.3]]);return filt(a,'lp',3000,0.7)});
def('ui.descend','ui',{gain:0.45,vars:1,gap:800,max:1,lvl:0.55},(r)=>{const a=secs(1.3),w=whoosh(1.0,r,1400,700,180,1.1,0.35,'p');mix(a,w,0,1);thump(a,0.75*SR,70,40,0.5,0.6);return roomTail(a,0.6,1.4,r)});
def('ui.ascend','ui',{gain:0.45,vars:1,gap:800,max:1,lvl:0.55},(r)=>{const a=secs(1.2),w=whoosh(0.9,r,250,900,2200,1.1,0.7,'p');mix(a,w,0,1);return a});
def('ui.pick','ui',{gain:0.4,vars:3,gap:40,max:2,lvl:0.5},(r)=>{const a=secs(0.08),f=rr(r,1400,1650);modal(a,0,[[f,0.02,1],[f*2.2,0.012,0.4]]);burst(a,0,0.003,r,'bp',3000,0.9,0.0002,0.002,0.4);return a});
def('ui.groupset','ui',{gain:0.45,vars:1,gap:150,max:1,lvl:0.5},(r)=>{const a=secs(0.3);modal(a,0,[[880,0.05,1],[2050,0.03,0.3]]);modal(a,0.07*SR,[[1320,0.07,1],[3000,0.04,0.3]]);return a});
def('ui.arrive','ui',{gain:0.5,vars:1,gap:60000,max:1,lvl:0.5},(r)=>{const a=secs(4.2);for(const [m,g] of [[50,1],[57,0.8],[62,0.55]])mix(a,brass(mtof(m),3.6,r,{att:1.2,bright:900,vib:0.003,formant:700}),0,g*0.6);bell(a,1.3*SR,mtof(86),2.2,0.25,r);bell(a,1.45*SR,mtof(93),1.8,0.15,r);return filt(a,'lp',3500,0.6)});
def('ui.bagpick','ui',{gain:0.4,vars:2,gap:120,max:1,lvl:0.45},(r)=>{const a=secs(0.25),n=noise(0.18*SR,r,'p');sweep(n,'bp',x=>lerp(700,1500,x),0.9);env(n,0.01,0.16);mix(a,n,0,1);modal(a,0.02*SR,[[rr(r,900,1100),0.03,0.2]]);return a});
def('ui.bagdrop','ui',{gain:0.4,vars:2,gap:120,max:1,lvl:0.45},(r)=>{const a=secs(0.3),n=noise(0.12*SR,r,'p');filt(n,'lp',1200,0.7);env(n,0.003,0.1);mix(a,n,0,0.8);thump(a,0,140,80,0.07,0.8);return a});
// a race's accent under its order cue: an orc's war drum, a dwarf's anvil, an elf's harp, a goblin's rattle, bones, a hiss
def('accent.orc','ui',{gain:0.38,vars:2,gap:60,max:1,lvl:0.55},(r)=>{const a=secs(0.4);thump(a,0,rr(r,85,95),48,0.3,1,0.03);burst(a,0,0.04,r,'lp',500,0.7,0.001,0.05,0.4,'p');return a});
def('accent.dwarf','ui',{gain:0.32,vars:2,gap:60,max:1,lvl:0.5},(r)=>{const a=secs(0.5),f=rr(r,1250,1400);modal(a,0,[[f,0.3,1],[f*2.76,0.18,0.4],[f*5.4,0.08,0.2]]);return a});
def('accent.elf','ui',{gain:0.32,vars:2,gap:60,max:1,lvl:0.5},(r)=>{const a=secs(1.0);mix(a,pluck(mtof(pick(r,[79,83,86])),0.9,{r,t60:0.9,bright:0.7,pos:0.3}),0,1);return filt(a,'lp',6000,0.6)});
def('accent.goblin','ui',{gain:0.32,vars:2,gap:60,max:1,lvl:0.5},(r)=>{const a=secs(0.3);for(let k=0;k<5;k++)modal(a,(k*0.03+r()*0.01)*SR,[[rr(r,600,1100),0.03,0.7]]);return a});
def('accent.bone','ui',{gain:0.32,vars:2,gap:60,max:1,lvl:0.5},(r)=>{const a=secs(0.3);for(let k=0;k<3;k++)modal(a,(k*0.045)*SR,[[rr(r,900,1600),0.035,1],[rr(r,2200,2800),0.02,0.3]]);return a});
def('accent.hiss','ui',{gain:0.3,vars:2,gap:60,max:1,lvl:0.45},(r)=>{const a=secs(0.4),n=noise(0.3*SR,r,'w');filt(n,'hp',4000,0.7);filt(n,'lp',8000,0.7);env(n,0.03,0.25);return mix(a,n,0,1)});
def('ui.chat','ui',{gain:0.35,vars:2,gap:500,max:1,lvl:0.42},(r)=>{const a=secs(0.25);modal(a,0,[[rr(r,1500,1600),0.04,1],[rr(r,3300,3500),0.02,0.3]]);modal(a,0.07*SR,[[rr(r,1950,2050),0.05,0.8],[rr(r,4300,4500),0.02,0.2]]);return filt(a,'lp',5000,0.6)});
def('ui.equip','ui',{gain:0.4,vars:3,gap:120,max:1,lvl:0.5},(r)=>{const a=secs(0.35),n=noise(0.08*SR,r,'p');filt(n,'bp',1200,0.8);env(n,0.004,0.07);mix(a,n,0,0.6);const f=rr(r,1800,2400);modal(a,0.02*SR,[[f,0.12,0.6],[f*1.47,0.08,0.3],[f*2.3,0.05,0.15]]);thump(a,0,130,80,0.05,0.3);return a});
// instant order cues, before the voice answers
def('cmd.move','ui',{gain:0.42,vars:3,gap:60,max:2,lvl:0.5},(r)=>{const a=secs(0.16);thump(a,0,150,85,0.05,1);burst(a,0,0.03,r,'bp',900,0.8,0.002,0.03,0.45,'p');modal(a,0,[[rr(r,640,720),0.03,0.25]]);return a});
def('cmd.attack','ui',{gain:0.42,vars:3,gap:60,max:2,lvl:0.55},(r)=>{const a=secs(0.45),n=whoosh(0.16,r,2500,6000,3500,1.4,0.6);mix(a,n,0,0.7);const f=rr(r,2900,3300);modal(a,0.1*SR,[[f,0.3,0.35],[f*1.51,0.18,0.18],[f*2.2,0.1,0.1]]);return filt(a,'lp',5500,0.6)});
def('cmd.work','ui',{gain:0.42,vars:3,gap:60,max:2,lvl:0.5},(r)=>{const a=secs(0.3),f=rr(r,1800,2100);modal(a,0,[[f,0.09,0.7],[f*2.7,0.05,0.3]]);modal(a,0.07*SR,[[f*1.12,0.08,0.5],[f*2.9,0.04,0.2]]);thump(a,0,160,100,0.04,0.4);return a});
def('cmd.build','ui',{gain:0.42,vars:3,gap:60,max:2,lvl:0.5},(r)=>{const a=secs(0.28);for(const t of [0,0.1]){modal(a,t*SR,[[rr(r,380,430),0.05,1],[rr(r,950,1050),0.03,0.4],[rr(r,2900,3200),0.06,0.15]]);burst(a,t,0.005,r,'bp',2500,0.8,0.0003,0.004,0.4)}return a});

// --- Combat ---
def('swing.light','fx',{gain:0.5,vars:4,gap:35,max:5,lvl:0.5},(r)=>{const d=rr(r,0.15,0.2),a=whoosh(d,r,rr(r,500,700),rr(r,1900,2500),rr(r,800,1000),2.0,0.55),s=whoosh(d,r,rr(r,4200,4800),rr(r,5200,6200),rr(r,4400,5000),12,0.55);return mix(a,s,0,0.35)});   // air, and a blade's thin hiss
def('swing.heavy','fx',{gain:0.55,vars:4,gap:35,max:5,lvl:0.55},(r)=>{const d=rr(r,0.24,0.3),a=whoosh(d,r,220,rr(r,800,1000),280,1.5,0.6,'p'),b=whoosh(d,r,140,380,150,1.2,0.6,'b');return mix(a,b,0,0.7)});
def('swing.thrust','fx',{gain:0.5,vars:3,gap:35,max:5,lvl:0.5},(r)=>{const a=whoosh(0.12,r,900,1900,1300,1.8,0.4);modal(a,0,[[rr(r,300,360),0.04,0.15]]);return a});
def('hit.flesh','fx',{gain:0.7,vars:4,gap:30,max:6,lvl:0.72},(r)=>{const a=secs(0.32);thump(a,0,rr(r,120,150),rr(r,45,55),0.12,1);burst(a,0,0.03,r,'lp',700,0.8,0.0005,0.03,0.7,'p');burst(a,0.002,0.02,r,'bp',rr(r,1100,1500),1.2,0.0005,0.015,0.45);
 const sq=noise(0.09*SR,r,'w');sweep(sq,'bp',t=>lerp(900,450,t),3);env(sq,0.005,0.08);mix(a,sq,0.01*SR,0.3);return a});
def('hit.armor','fx',{gain:0.7,vars:4,gap:30,max:6,lvl:0.72},(r)=>{const a=secs(0.5);thump(a,0,130,55,0.1,0.9);const f=rr(r,650,950);modal(a,0,[[f,0.18,0.5],[f*2.71,0.12,0.35],[f*5.13,0.07,0.2],[f*7.9,0.04,0.12]]);burst(a,0,0.012,r,'hp',2500,0.7,0.0003,0.01,0.6);return a});
def('hit.big','fx',{gain:0.75,vars:3,gap:40,max:4,lvl:0.8},(r)=>{const a=secs(0.6);thump(a,0,105,38,0.25,1,0.04);burst(a,0,0.06,r,'lp',500,0.7,0.001,0.06,0.8,'p');for(let k=0;k<6;k++)modal(a,(0.004+r()*0.04)*SR,[[rr(r,1400,3200),0.015,0.3]]);return a});
def('parry','fx',{gain:0.6,vars:4,gap:40,max:4,lvl:0.7},(r)=>{const a=secs(1.0),f=rr(r,1050,1450),M=[[1,0.7,1],[2.32,0.5,0.6],[4.25,0.32,0.4],[6.63,0.2,0.25],[9.38,0.14,0.15]];modal(a,0,M.map(([k,t,g])=>[f*k,t,g,r()*TAU]));modal(a,0,M.slice(0,3).map(([k,t,g])=>[f*k+rr(r,2,5),t,g*0.5,r()*TAU]));burst(a,0,0.008,r,'hp',3000,0.7,0.0002,0.006,0.8);return a});
def('block','fx',{gain:0.62,vars:3,gap:40,max:4,lvl:0.7},(r)=>{const a=secs(0.45);const f=rr(r,170,200);modal(a,0,[[f,0.1,1],[f*2.45,0.06,0.5],[f*5.1,0.03,0.25]]);thump(a,0,120,60,0.08,0.7);const g=rr(r,1300,1600);modal(a,0,[[g,0.16,0.18],[g*2.7,0.09,0.1]]);burst(a,0,0.01,r,'bp',1800,0.8,0.0003,0.008,0.6);return a});
def('death.fall','fx',{gain:0.7,vars:3,gap:80,max:3,lvl:0.75},(r)=>{const a=secs(0.9);thump(a,0.02*SR,90,36,0.3,1,0.05);burst(a,0.02,0.15,r,'lp',450,0.7,0.003,0.15,0.6,'p');thump(a,0.16*SR,75,40,0.2,0.5);
 const cl=noise(0.35*SR,r,'w');filt(cl,'bp',2200,0.8);env(cl,0.01,0.3);mix(a,cl,0.04*SR,0.12);for(let k=0;k<4;k++)modal(a,(0.03+r()*0.2)*SR,[[rr(r,900,1600),0.08,0.1],[rr(r,2400,3000),0.05,0.06]]);return a});
def('ko','fx',{gain:0.55,vars:2,gap:200,max:2,lvl:0.6},(r)=>{const a=secs(0.7);modal(a,0,[[240,0.1,1],[560,0.05,0.4]]);const n=a.length;let p=0;for(let i=0.05*SR;i<n;i++){const t=(i-0.05*SR)/SR;p+=TAU*(1800-1100*t)/SR;a[i]+=Math.sin(p)*0.12*Math.exp(-t*4)*(1+0.5*Math.sin(TAU*9*t))}return a});
def('bow.shoot','fx',{gain:0.55,vars:3,gap:40,max:4,lvl:0.55},(r)=>{const a=secs(0.5);mix(a,pluck(rr(r,95,120),0.35,{r,t60:0.25,bright:0.9,pos:0.5}),0,0.8);burst(a,0,0.006,r,'hp',2000,0.7,0.0003,0.005,0.5);const w=whoosh(0.3,r,2600,4200,2400,3,0.3);mix(a,w,0.02*SR,0.25);return a});
def('arrow.hit','fx',{gain:0.55,vars:4,gap:30,max:5,lvl:0.6},(r)=>{const a=secs(0.25);modal(a,0,[[rr(r,380,460),0.05,1],[rr(r,900,1100),0.03,0.4]]);burst(a,0,0.008,r,'bp',2200,0.8,0.0002,0.006,0.6);thump(a,0,140,70,0.04,0.4);return a});
def('siege.launch','fx',{gain:0.7,vars:2,gap:200,max:2,lvl:0.75},(r)=>{const a=secs(1.0);const cr=noise(0.35*SR,r,'w');for(let i=0;i<cr.length;i++)cr[i]*=Math.max(0,Math.sin(TAU*28*i/SR));sweep(cr,'bp',t=>lerp(600,900,t),4);mix(a,cr,0,0.4);thump(a,0.35*SR,80,40,0.35,1);modal(a,0.35*SR,[[160,0.2,0.4],[410,0.1,0.2]]);mix(a,whoosh(0.45,r,200,700,250,1.2,0.4,'p'),0.38*SR,0.4);return a});
def('siege.impact','fx',{gain:0.8,vars:3,gap:120,max:3,lvl:0.85},(r)=>{const a=secs(1.6);thump(a,0,70,28,0.7,1,0.06);burst(a,0,0.5,r,'lp',700,0.6,0.002,0.5,0.8,'p');for(let k=0;k<26;k++)modal(a,(0.03+Math.pow(r(),1.5)*0.9)*SR,[[rr(r,500,2600),0.02,rr(r,0.05,0.25)]]);return a});
def('ram.hit','fx',{gain:0.8,vars:2,gap:200,max:2,lvl:0.85},(r)=>{const a=secs(1.0);thump(a,0,75,35,0.45,1,0.05);modal(a,0,[[105,0.35,0.6],[260,0.2,0.35],[540,0.1,0.15]]);burst(a,0,0.08,r,'lp',900,0.7,0.001,0.1,0.5);return a});
// magic and ailments
def('spell.fire','fx',{gain:0.6,vars:3,gap:80,max:3,lvl:0.65},(r)=>{const a=secs(0.9),w=whoosh(0.7,r,150,900,300,0.9,0.3,'p');mix(a,w,0,1);for(let k=0;k<26;k++){const t=r()*0.75;burst(a,t,0.01,r,'bp',rr(r,1500,4000),1.5,0.0002,0.006,rr(r,0.1,0.4))}return a});
def('spell.frost','fx',{gain:0.55,vars:3,gap:80,max:3,lvl:0.55},(r)=>{const a=secs(1.0);for(let k=0;k<18;k++){const t=r()*0.5,f=rr(r,2800,6500);modal(a,t*SR,[[f,rr(r,0.2,0.5),rr(r,0.2,0.6)]])}const w=whoosh(0.6,r,3000,6000,4000,2,0.2);mix(a,w,0,0.35);return a});
def('spell.shock','fx',{gain:0.55,vars:3,gap:80,max:3,lvl:0.6},(r)=>{const a=secs(0.6),n=noise(0.5*SR,r,'w');let gate=0;for(let i=0;i<n.length;i++){if(r()<0.004)gate=rr(r,0.4,1);gate*=0.995;n[i]*=gate}filt(n,'bp',2800,0.8);mix(a,n,0,1);thump(a,0,160,60,0.1,0.5);return a});
def('spell.poison','fx',{gain:0.5,vars:3,gap:80,max:3,lvl:0.55},(r)=>{const a=secs(0.8);const h=noise(0.6*SR,r,'w');filt(h,'hp',3500,0.7);env(h,0.05,0.5);mix(a,h,0,0.4);for(let k=0;k<9;k++){const t=r()*0.6,f=rr(r,200,520),n=Math.round(0.06*SR),b=new Float32Array(n);let p=0;for(let i=0;i<n;i++){p+=TAU*f*(1+i/n*1.4)/SR;b[i]=Math.sin(p)*Math.sin(Math.PI*i/n)}mix(a,b,t*SR,rr(r,0.3,0.7))}return a});
def('spell.holy','fx',{gain:0.6,vars:2,gap:120,max:2,lvl:0.65},(r)=>{const a=secs(2.0);bell(a,0,rr(r,520,560),1.6,1,r);bell(a,0.02*SR,rr(r,780,820),1.4,0.5,r);thump(a,0,90,45,0.5,0.7);return a});
def('spell.dark','fx',{gain:0.55,vars:3,gap:120,max:2,lvl:0.6},(r)=>{const d=0.8,n=noise(d*SR,r,'p');sweep(n,'bp',t=>lerp(1800,200,t),2.5);shape(n,t=>Math.pow(t,1.5)*(t>0.9?(1-t)/0.1:1));const a=secs(d+0.1);mix(a,n,0,1);thump(a,d*0.85*SR,70,40,0.3,0.6);return a});
def('spell.astral','fx',{gain:0.5,vars:2,gap:120,max:2,lvl:0.55},(r)=>{const a=secs(1.4);for(let k=0;k<5;k++){const f=mtof(pick(r,[76,79,81,83,86,88])),n=a.length;let p=0;for(let i=0;i<n;i++){const t=i/SR;p+=TAU*f*(1+0.01*Math.sin(TAU*(3+k)*t))/SR;a[i]+=Math.sin(p)*0.15*Math.sin(Math.PI*Math.min(1,t/1.3))}}return a});
// specials (Specials.dm): a ground slam, a lob, a dart or arrow in flight, a tongue lash
def('slam','fx',{gain:0.75,vars:2,gap:200,max:2,lvl:0.8},(r)=>{const a=secs(1.2);thump(a,0,85,32,0.55,1,0.05);burst(a,0,0.3,r,'lp',600,0.7,0.002,0.35,0.7,'p');for(let k=0;k<24;k++)burst(a,0.02+Math.pow(r(),1.6)*0.6,0.01,r,'bp',rr(r,600,3000),1.3,0.0003,0.012,rr(r,0.05,0.25));return a});
def('throw','fx',{gain:0.5,vars:3,gap:120,max:2,lvl:0.5},(r)=>whoosh(rr(r,0.35,0.45),r,300,900,400,1.2,0.4,'p'));
def('whizz','fx',{gain:0.5,vars:3,gap:60,max:3,lvl:0.5},(r)=>{const d=0.32,a=whoosh(d,r,4200,3600,2200,4,0.25);let p=0;for(let i=0;i<a.length;i++){const x=i/a.length;p+=TAU*(3200-1400*x)/SR;a[i]+=Math.sin(p)*0.08*Math.sin(Math.PI*x)}return a});
def('tongue','fx',{gain:0.55,vars:2,gap:200,max:2,lvl:0.6},(r)=>{const a=secs(0.5),n=noise(0.25*SR,r,'w');sweep(n,'bp',x=>lerp(2500,500,x),3);env(n,0.01,0.22);mix(a,n,0,1);const m=Math.round(0.05*SR);let p=0;for(let i=0;i<m;i++){p+=TAU*(300+900*i/m)/SR;a[Math.round(0.26*SR)+i]+=Math.sin(p)*0.6*Math.sin(Math.PI*i/m)}return a});
def('web','fx',{gain:0.5,vars:2,gap:100,max:2,lvl:0.55},(r)=>{const a=secs(0.4),n=noise(0.3*SR,r,'w');sweep(n,'bp',t=>lerp(1200,500,t),2);env(n,0.005,0.25);mix(a,n,0,1);thump(a,0,120,70,0.08,0.4);return a});
def('bleed','fx',{gain:0.4,vars:3,gap:150,max:2,lvl:0.45},(r)=>{const a=secs(0.2),n=noise(0.12*SR,r,'w');sweep(n,'bp',t=>lerp(700,350,t),4);env(n,0.004,0.1);return mix(a,n,0,1)});
def('splash','fx',{gain:0.55,vars:3,gap:80,max:3,lvl:0.6},(r)=>{const a=secs(0.8),n=noise(0.6*SR,r,'w');sweep(n,'bp',t=>lerp(2200,900,t),0.7);env(n,0.004,0.5);mix(a,n,0,1);for(let k=0;k<8;k++){const t=0.05+r()*0.4,f=rr(r,500,1400),m=Math.round(0.04*SR),b=new Float32Array(m);let p=0;for(let i=0;i<m;i++){p+=TAU*f*(1+1.5*i/m)/SR;b[i]=Math.sin(p)*Math.sin(Math.PI*i/m)}mix(a,b,t*SR,0.25)}return a});

// --- Work ---
def('chop','fx',{gain:0.55,vars:5,gap:40,max:4,lvl:0.65},(r)=>{const a=secs(0.4),f=rr(r,190,250);burst(a,0,0.004,r,'bp',rr(r,2800,4000),0.8,0.0002,0.003,0.9);modal(a,0,[[f,0.11,1],[f*2.15,0.07,0.6],[f*3.8,0.05,0.35],[f*6.2,0.03,0.2]]);thump(a,0,140,70,0.06,0.6);
 if(r()<0.5){const c=noise(0.06*SR,r,'w');filt(c,'bp',1100,2);env(c,0.002,0.05);mix(a,c,0.012*SR,0.25)}return a});
def('mine','fx',{gain:0.55,vars:5,gap:40,max:4,lvl:0.65},(r)=>{const a=secs(0.45),f=rr(r,2100,2900);modal(a,0,[[f,0.12,0.6],[f*1.62,0.08,0.35],[f*2.7,0.05,0.2]]);burst(a,0,0.03,r,'bp',rr(r,1200,1800),0.9,0.0003,0.03,0.9);thump(a,0,170,90,0.04,0.4);
 const g=5+Math.floor(r()*6);for(let k=0;k<g;k++){const t=0.02+Math.pow(r(),1.4)*0.25;burst(a,t,0.006,r,'bp',rr(r,1800,4500),1.5,0.0002,0.004,rr(r,0.05,0.25))}return a});
def('mine.ore','fx',{gain:0.6,vars:4,gap:40,max:5,lvl:0.65},(r)=>{const a=secs(0.6),f=rr(r,2600,3400);modal(a,0,[[f,0.3,0.8],[f*1.51,0.2,0.5],[f*2.42,0.12,0.3],[f*3.2,0.08,0.2]]);burst(a,0,0.02,r,'bp',2000,0.9,0.0003,0.02,0.6);
 for(let k=0;k<5;k++){const t=0.03+r()*0.2;burst(a,t,0.006,r,'bp',rr(r,2000,5000),1.5,0.0002,0.004,rr(r,0.05,0.2))}return a});
def('tree.fall','fx',{gain:0.75,vars:2,gap:500,max:2,lvl:0.75},(r)=>{const a=secs(2.6);// creak, the rush of the crown, the crash
 const cr=noise(0.9*SR,r,'w');let pulse=0,next=0;for(let i=0;i<cr.length;i++){if(i>=next){pulse=1;next=i+Math.round(SR/rr(r,14,26))}pulse*=0.993;cr[i]*=pulse}filt(cr,'bp',rr(r,500,700),5);shape(cr,t=>Math.sin(Math.PI*Math.min(1,t*1.1)));mix(a,cr,0,0.7);
 mix(a,whoosh(0.9,r,300,1400,500,0.9,0.75,'p'),0.6*SR,0.6);const t=1.45;thump(a,t*SR,80,32,0.6,1,0.05);burst(a,t,0.6,r,'lp',900,0.7,0.002,0.6,0.7,'p');
 for(let k=0;k<30;k++){const tt=t+Math.pow(r(),1.6)*0.8;burst(a,tt,0.02,r,'bp',rr(r,1500,5000),1.2,0.0005,0.02,rr(r,0.05,0.2))}return a});
def('rock.break','fx',{gain:0.7,vars:3,gap:250,max:2,lvl:0.75},(r)=>{const a=secs(1.3);thump(a,0,95,40,0.35,1,0.05);burst(a,0,0.25,r,'lp',800,0.7,0.002,0.3,0.7,'p');
 for(let k=0;k<40;k++){const t=Math.pow(r(),1.8)*1.0;burst(a,t,0.01,r,'bp',rr(r,700,3500),1.3,0.0003,rr(r,0.006,0.02),rr(r,0.05,0.3))}return a});
def('build','fx',{gain:0.55,vars:4,gap:40,max:4,lvl:0.62},(r)=>{const a=secs(0.45),two=r()<0.4;for(const t of two?[0,0.17]:[0]){const f=rr(r,330,420);modal(a,t*SR,[[f,0.06,1],[f*2.3,0.04,0.45],[rr(r,2700,3300),0.09,0.18]]);burst(a,t,0.004,r,'bp',2600,0.8,0.0002,0.003,0.7);thump(a,t*SR,150,80,0.04,0.4)}return a});
def('craft.anvil','fx',{gain:0.55,vars:4,gap:60,max:3,lvl:0.62},(r)=>{const a=secs(1.0),f=rr(r,600,700);modal(a,0,[[f,0.7,1],[f*2.76,0.45,0.6],[f*5.4,0.25,0.35],[f*8.93,0.12,0.2]]);burst(a,0,0.005,r,'hp',2500,0.7,0.0002,0.004,0.6);return a});
def('craft.saw','fx',{gain:0.5,vars:2,gap:400,max:2,lvl:0.55},(r)=>{const a=secs(0.95);for(const [t,d,up] of [[0,0.4,1],[0.45,0.4,0]]){const n=noise(d*SR,r,'w');for(let i=0;i<n.length;i++)n[i]*=0.5+0.5*Math.sin(TAU*(up?95:80)*i/SR);sweep(n,'bp',x=>up?lerp(1500,2600,x):lerp(2600,1500,x),2.2);shape(n,x=>Math.sin(Math.PI*x));mix(a,n,t*SR,1)}return a});
def('craft.tinker','fx',{gain:0.5,vars:4,gap:60,max:3,lvl:0.55},(r)=>{const a=secs(0.4);for(let k=0;k<3;k++){const f=rr(r,1600,3200);modal(a,(k*0.07+r()*0.03)*SR,[[f,0.06,0.7],[f*1.9,0.04,0.3]])}return a});
// a wall or building piece finished (world-look's rmSfx.at('built',x,y,{kind})): it settles with a thump and a little dust
def('built','fx',{gain:0.55,vars:3,gap:150,max:2,lvl:0.6},(r)=>{const a=secs(0.7);thump(a,0,rr(r,95,120),45,0.25,1,0.04);burst(a,0,0.12,r,'lp',700,0.7,0.002,0.12,0.6,'p');const d=whoosh(0.5,r,900,1600,600,0.8,0.25,'p');mix(a,d,0.03*SR,0.22);
 for(let k=0;k<7;k++)burst(a,0.03+Math.pow(r(),1.5)*0.35,0.008,r,'bp',rr(r,900,2800),1.3,0.0003,0.008,rr(r,0.05,0.18));return a});
def('built.wood','fx',{gain:0.55,vars:3,gap:150,max:2,lvl:0.6},(r)=>{const a=secs(0.6),f=rr(r,200,240);modal(a,0,[[f,0.12,1],[f*2.3,0.07,0.45],[f*4.4,0.04,0.2]]);thump(a,0,120,60,0.1,0.7);const d=whoosh(0.4,r,900,1500,600,0.8,0.25,'p');mix(a,d,0.03*SR,0.15);return a});
def('dig','fx',{gain:0.55,vars:3,gap:60,max:3,lvl:0.6},(r)=>{const a=secs(0.4);burst(a,0,0.15,r,'lp',900,0.7,0.002,0.12,0.8,'p');thump(a,0,120,60,0.06,0.5);for(let k=0;k<10;k++)burst(a,r()*0.18,0.006,r,'bp',rr(r,800,2500),1.2,0.0003,0.005,0.15);return a});
def('drop','fx',{gain:0.5,vars:3,gap:150,max:2,lvl:0.55},(r)=>{const a=secs(0.5);thump(a,0,120,65,0.1,0.8);burst(a,0,0.06,r,'lp',900,0.7,0.002,0.06,0.5,'p');for(let k=0;k<5;k++)modal(a,(0.02+r()*0.12)*SR,[[rr(r,300,650),0.05,0.4],[rr(r,900,1500),0.03,0.15]]);return a});
def('pickup','fx',{gain:0.45,vars:3,gap:150,max:2,lvl:0.5},(r)=>{const a=secs(0.35),n=noise(0.2*SR,r,'p');sweep(n,'bp',x=>lerp(900,1700,x),0.9);env(n,0.02,0.18);mix(a,n,0,0.8);for(let k=0;k<2;k++)modal(a,(0.05+k*0.06)*SR,[[rr(r,1600,2600),0.05,0.3]]);return a});
def('door','fx',{gain:0.5,vars:2,gap:300,max:2,lvl:0.55},(r)=>{const a=secs(0.9),cr=noise(0.5*SR,r,'w');let pl=0,nx=0;for(let i=0;i<cr.length;i++){if(i>=nx){pl=1;nx=i+Math.round(SR/rr(r,30,60))}pl*=0.99;cr[i]*=pl}filt(cr,'bp',rr(r,700,950),6);shape(cr,t=>Math.sin(Math.PI*t));mix(a,cr,0,0.8);modal(a,0.5*SR,[[180,0.12,0.8],[420,0.06,0.3]]);return a});

// --- Ambient one-shots ---
function chirp(dst,at,f0,f1,dur,g,fm){const n=Math.round(dur*SR),start=Math.round(at);let p=0;for(let i=0;i<n&&start+i<dst.length;i++){const t=i/n;const f=f0+(f1-f0)*t;p+=TAU*f*(1+(fm||0)*Math.sin(TAU*60*i/SR))/SR;dst[start+i]+=Math.sin(p)*g*Math.sin(Math.PI*t)}return dst}
def('bird.song','amb',{gain:0.35,vars:8,gap:400,max:3,lvl:0.5},(r,v)=>{const a=secs(1.8),sp=v%4,base=rr(r,2400,4200);let t=0.02;
 const note=(f0,f1,d,g,tr)=>{const n=Math.round(d*SR),s=Math.round(t*SR),tf=rr(r,28,45);let p=0;for(let i=0;i<n&&s+i<a.length;i++){const x=i/n,f=(f0+(f1-f0)*x)*(1+(tr||0)*Math.sin(TAU*tf*i/SR));p+=TAU*f/SR;a[s+i]+=(Math.sin(p)+0.12*Math.sin(2*p))*Math.pow(Math.sin(Math.PI*x),0.7)*g}};
 if(sp===0){const n=6+Math.floor(r()*7);for(let k=0;k<n;k++){const f=base*rr(r,0.75,1.35),d=rr(r,0.03,0.07);note(f,f*rr(r,0.8,1.25),d,rr(r,0.5,1),0.02);t+=d+rr(r,0.01,0.03)}}   // a warbler's run
 else if(sp===1){const f=base*rr(r,0.9,1.1),n=8+Math.floor(r()*8);for(let k=0;k<n;k++){note(f*(1-k*0.01),f*0.92,0.035,0.8*(1-k/n*0.5),0);t+=0.05}}   // a trill
 else if(sp===2){const f=base*0.7;note(f,f*1.25,0.22,1,0.01);t+=0.28;note(f*1.2,f*0.9,0.3,0.8,0.015);t+=0.34;if(r()<0.6)note(f*0.95,f*1.05,0.18,0.6,0.01)}   // a whistled call
 else{const n=3+Math.floor(r()*4);for(let k=0;k<n;k++){const f=base*rr(r,0.95,1.2);note(f*1.3,f*0.8,0.045,rr(r,0.6,1),0);t+=rr(r,0.09,0.16)}}   // sparrow chips
 return filt(a,'hp',1400,0.7)});
def('bird.crow','amb',{gain:0.35,vars:3,gap:1500,max:1,lvl:0.5},(r)=>{const a=secs(1.4);const n=1+Math.floor(r()*3);for(let k=0;k<n;k++){const d=0.22,b=noise(d*SR,r,'w'),q=new Float32Array(b.length);let p=0;for(let i=0;i<b.length;i++){p+=TAU*560*(1-0.2*i/b.length)/SR;q[i]=(Math.sin(p)>0?1:-1)*0.5+b[i]*0.4}
 const F1=new Res().set(1100,250),F2=new Res().set(1800,300);for(let i=0;i<q.length;i++)q[i]=F1.run(q[i])+F2.run(q[i])*0.6;shape(q,t=>Math.pow(Math.sin(Math.PI*t),0.6));mix(a,q,k*0.33*SR,1)}return a});
def('owl','amb',{gain:0.35,vars:3,gap:5000,max:1,lvl:0.5},(r)=>{const a=secs(1.8),f=rr(r,370,410);for(const [t,d,g] of [[0,0.35,1],[0.55,0.15,0.6],[0.75,0.45,0.9]]){const n=Math.round(d*SR);let p=0;for(let i=0;i<n;i++){const x=i/n;p+=TAU*f*(1.05-0.08*x)/SR;a[Math.round(t*SR)+i]+=Math.sin(p)*g*Math.pow(Math.sin(Math.PI*x),0.8)}}
 const br=noise(a.length,r,'w');filt(br,'bp',f,4);for(let i=0;i<a.length;i++)a[i]+=br[i]*Math.abs(a[i])*0.6;return a});
def('wolf','amb',{gain:0.3,vars:2,gap:20000,max:1,lvl:0.45},(r)=>{const d=2.6,a=secs(d+0.2),n=a.length,F1=new Res().set(700,200),F2=new Res().set(1100,250);let p=0;const f0=rr(r,420,500);
 for(let i=0;i<d*SR;i++){const t=i/SR,x=t/d;const f=f0*(x<0.15?lerp(0.8,1.1,x/0.15):x<0.7?1.1+0.05*Math.sin(TAU*0.7*t):lerp(1.15,0.8,(x-0.7)/0.3))*(1+0.008*Math.sin(TAU*5*t));p+=TAU*f/SR;const s=Math.sin(p)+0.3*Math.sin(2*p)+0.1*Math.sin(3*p);a[i]=(F1.run(s)+F2.run(s)*0.5)*Math.pow(Math.sin(Math.PI*x),0.7)}
 return roomTail(filt(a,'lp',2500,0.7),0.6,1.2,r)});
def('frog','amb',{gain:0.35,vars:4,gap:600,max:2,lvl:0.5},(r)=>{const a=secs(0.6),f=rr(r,140,260),n=2+Math.floor(r()*3);for(let k=0;k<n;k++){const d=0.07,m=Math.round(d*SR),b=new Float32Array(m);let p=0;for(let i=0;i<m;i++){p+=TAU*f/SR;b[i]=(p%TAU<TAU*0.3?1:-0.4)*Math.sin(Math.PI*i/m)}const R1=new Res().set(f*4,200);for(let i=0;i<m;i++)b[i]=R1.run(b[i]);mix(a,b,k*0.1*SR,1)}return a});
def('drip','amb',{gain:0.35,vars:5,gap:300,max:3,lvl:0.5},(r)=>{const a=secs(0.5),f=rr(r,900,1900);const n=Math.round(0.12*SR);let p=0;for(let i=0;i<n;i++){const t=i/SR;p+=TAU*f*(1+3*t)/SR;a[i]+=Math.sin(p)*Math.exp(-t*35)}burst(a,0,0.004,r,'hp',3000,0.7,0.0002,0.003,0.2);return roomTail(a,0.9,0.9,r)});
def('pebbles','amb',{gain:0.3,vars:3,gap:3000,max:1,lvl:0.45},(r)=>{const a=secs(1.2);let t=0,g=1;for(let k=0;k<9;k++){burst(a,t,0.008,r,'bp',rr(r,1200,3500),1.4,0.0002,0.006,g);t+=rr(r,0.04,0.14);g*=0.82}return roomTail(a,0.7,1.0,r)});
def('hawk','amb',{gain:0.3,vars:2,gap:12000,max:1,lvl:0.45},(r)=>{const a=secs(1.3);chirp(a,0,2600,2100,0.9,1,0.03);const n=noise(0.9*SR,r,'w');filt(n,'bp',2400,3);env(n,0.05,0.8);mix(a,n,0,0.1);return roomTail(a,0.4,0.8,r)});
def('bubble','amb',{gain:0.35,vars:4,gap:400,max:2,lvl:0.5},(r)=>{const a=secs(0.6);thump(a,0,rr(r,70,110),rr(r,140,220),0.25,1,0.08);burst(a,0.05,0.2,r,'lp',300,0.7,0.01,0.2,0.4,'b');return a});
def('bell.village','amb',{gain:0.32,vars:1,gap:30000,max:1,lvl:0.5,spatial:false},(r)=>{const a=secs(5.5);for(let k=0;k<3;k++)bell(a,k*1.3*SR,rr(r,290,296),3.0,0.9,r);return filt(a,'lp',3000,0.7)});
def('cave.groan','amb',{gain:0.3,vars:2,gap:20000,max:1,lvl:0.45},(r)=>{const a=secs(3.0),n=noise(3.0*SR,r,'b');sweep(n,'bp',t=>lerp(90,60,t),3);shape(n,t=>Math.pow(Math.sin(Math.PI*t),1.5));mix(a,n,0,1);return a});

// --- Ambient beds: seamless stereo loops. Every slow wobble is a sum of sines with a whole number of cycles per loop,
// so the loop point never shows; the noise underneath is cross-faded across it. ---
function loopLFO(r,L,lo,hi,n){const P=[];for(let k=0;k<(n||4);k++)P.push([1+Math.floor(r()*Math.max(1,L*0.4)),r()*TAU,r()]);let s=0;for(const p of P)s+=p[2];return t=>{let v=0;for(const p of P)v+=Math.sin(TAU*p[0]*t/L+p[1])*p[2];return lo+(hi-lo)*(0.5+0.5*v/s)}}
function seamless(a,fadeS){const nf=Math.round(fadeS*SR),n=a.length-nf,out=new Float32Array(n);for(let i=0;i<n;i++)out[i]=a[i];for(let i=0;i<nf;i++){const x=i/nf;out[i]=a[i]*Math.sqrt(x)+a[n+i]*Math.sqrt(1-x)}return out}
function bed(L,r,fill){const F=1.0,chs=[0,1].map(c=>{const a=secs(L+F);fill(a,c,r,L+F);return seamless(a,F)});return chs}
function bedWind(L,r,cold){const cut=loopLFO(r,L,350,1100,5),amp=loopLFO(r,L,0.25,1,4),wh=loopLFO(r,L,650,1250,3);
 return bed(L,r,(a,c,rr2)=>{const n=noise(a.length,rng(hash('w'+c)+Math.floor(r()*1e6)),'p'),F=new BQ(),W=new BQ();for(let i=0;i<a.length;i++){const t=(i/SR)%L;if((i&63)===0){F.set('bp',cut(t)*(c?1.06:0.95),0.6);if(cold)W.set('bp',wh(t),18)}let x=F.run(n[i])*amp(t);if(cold)x+=W.run(n[i])*0.5*amp(t)*amp((t+L/3)%L);a[i]=x}})}
def('bed.wind','amb',{gain:0.5,vars:1,lvl:0.5,sr:22050,loop:12,spatial:false},(r)=>bedWind(12,r,false));
def('bed.wind.cold','amb',{gain:0.5,vars:1,lvl:0.5,sr:22050,loop:12,spatial:false},(r)=>bedWind(12,r,true));
def('bed.sky','amb',{gain:0.55,vars:1,lvl:0.55,sr:22050,loop:10,spatial:false},(r)=>{const cut=loopLFO(r,10,500,1600,5),amp=loopLFO(r,10,0.5,1,4);return bed(10,r,(a,c)=>{const n=noise(a.length,rng(77+c),'w'),F=new BQ();for(let i=0;i<a.length;i++){const t=(i/SR)%10;if((i&63)===0)F.set('bp',cut(t)*(c?1.05:0.95),0.5);a[i]=F.run(n[i])*amp(t)}})});
def('bed.leaves','amb',{gain:0.4,vars:1,lvl:0.4,sr:22050,loop:12,spatial:false},(r)=>{const amp=loopLFO(r,12,0.1,1,5);return bed(12,r,(a,c)=>{const n=noise(a.length,rng(91+c),'w'),gr=noise(a.length,rng(13+c),'w');filt(gr,'lp',8,0.7);filt(n,'hp',2500,0.7);filt(n,'lp',7000,0.7);for(let i=0;i<a.length;i++){const t=(i/SR)%12;a[i]=n[i]*amp(t)*Math.min(1,Math.abs(gr[i])*20)}})});
def('bed.water','amb',{gain:0.45,vars:1,lvl:0.45,sr:22050,loop:12,spatial:false},(r)=>{const sw=loopLFO(r,12,0.3,1,3);return bed(12,r,(a,c,rx,LL)=>{const n=noise(a.length,rng(31+c),'p');filt(n,'lp',700,0.7);const R2=rng(55+c);for(let i=0;i<a.length;i++){const t=(i/SR)%12;a[i]=n[i]*sw(t)}
 for(let k=0;k<LL*6;k++){const t=R2()*(LL-0.1),f=200+R2()*900,m=Math.round(0.05*SR);let p=0;for(let i=0;i<m;i++){p+=TAU*f*(1+i/m)/SR;const j=Math.round(t*SR)+i;if(j<a.length)a[j]+=Math.sin(p)*Math.sin(Math.PI*i/m)*0.04}}})});
def('bed.insects','amb',{gain:0.32,vars:1,lvl:0.4,sr:22050,loop:12,spatial:false},(r)=>{const sw=loopLFO(r,12,0.2,1,3);return bed(12,r,(a,c)=>{const n=noise(a.length,rng(41+c),'w'),F=new BQ().set('bp',4300+c*400,6);const am=180+c*23;for(let i=0;i<a.length;i++){const t=(i/SR)%12;a[i]=F.run(n[i])*(0.5+0.5*Math.sin(TAU*am*i/SR))*sw(t)}})});
def('bed.crickets','amb',{gain:0.35,vars:1,lvl:0.4,sr:22050,loop:12,spatial:false},(r)=>bed(12,r,(a,c,rx,LL)=>{const R2=rng(61+c*7);for(let k=0;k<4;k++){const f=4200+R2()*900,rate=0.5+R2()*0.5,g=0.3+R2()*0.7,ph=R2()*rate;for(let t=ph;t<LL-0.2;t+=rate+(R2()-0.5)*0.05){for(let q=0;q<3;q++){const s=Math.round((t+q*0.032)*SR),m=Math.round(0.018*SR);let p=0;for(let i=0;i<m&&s+i<a.length;i++){p+=TAU*f/SR;a[s+i]+=Math.sin(p)*Math.sin(Math.PI*i/m)*g*0.3}}}}}));
def('bed.cave','amb',{gain:0.5,vars:1,lvl:0.4,sr:22050,loop:12,spatial:false},(r)=>{const amp=loopLFO(r,12,0.6,1,3);return bed(12,r,(a,c)=>{const n=noise(a.length,rng(71+c),'b'),m=noise(a.length,rng(81+c),'p');filt(n,'lp',120,0.7);filt(m,'bp',230,6);for(let i=0;i<a.length;i++){const t=(i/SR)%12;a[i]=(n[i]+m[i]*0.25)*amp(t)}})});
def('bed.lava','amb',{gain:0.5,vars:1,lvl:0.45,sr:22050,loop:12,spatial:false},(r)=>bed(12,r,(a,c,rx,LL)=>{const n=noise(a.length,rng(101+c),'b');filt(n,'lp',160,0.7);for(let i=0;i<a.length;i++)a[i]=n[i];const R2=rng(111+c);
 for(let k=0;k<LL*4;k++){const t=R2()*(LL-0.3);thump(a,t*SR,60+R2()*50,120+R2()*80,0.2,0.25,0.08)}for(let k=0;k<LL*30;k++){const s=Math.round(R2()*(a.length-200));for(let i=0;i<60;i++)a[s+i]+=(R2()*2-1)*0.06*Math.exp(-i/12)}}));
def('bed.jungle','amb',{gain:0.38,vars:1,lvl:0.42,sr:22050,loop:12,spatial:false},(r)=>bed(12,r,(a,c,rx,LL)=>{const n=noise(a.length,rng(121+c),'w'),F=new BQ().set('bp',3100+c*300,4);for(let i=0;i<a.length;i++)a[i]=F.run(n[i])*(0.4+0.6*Math.pow(0.5+0.5*Math.sin(TAU*36*i/SR),3))*0.6;
 const R2=rng(131+c);for(let k=0;k<LL*2.5;k++){const t=R2()*(LL-0.3),f=1800+R2()*2500;chirp(a,t*SR,f,f*(0.7+R2()*0.8),0.05+R2()*0.12,0.25,0.03)}}));
def('bed.fire','amb',{gain:0.45,vars:1,lvl:0.45,sr:22050,loop:8,spatial:true},(r)=>bed(8,r,(a,c,rx,LL)=>{const n=noise(a.length,rng(141+c),'p');filt(n,'lp',350,0.7);for(let i=0;i<a.length;i++)a[i]=n[i]*0.8;const R2=rng(151+c);for(let k=0;k<LL*25;k++){const s=Math.round(R2()*(a.length-400)),f=1500+R2()*3000,F=new BQ().set('bp',f,1.5),g=0.1+R2()*0.4;for(let i=0;i<300;i++)a[s+i]+=F.run((R2()*2-1))*g*Math.exp(-i/40)}}));

// battle drums (music volume): a low taiko and a frame drum
def('drum.taiko','mus',{gain:0.5,vars:3,gap:60,max:3,lvl:0.6,spatial:false,jit:0.02},(r)=>{const a=secs(0.9);thump(a,0,rr(r,72,80),rr(r,44,50),0.6,1,0.04);burst(a,0,0.05,r,'lp',rr(r,500,700),0.7,0.001,0.08,0.5,'p');modal(a,0,[[rr(r,110,125),0.25,0.3],[rr(r,190,215),0.15,0.15]]);return a});
def('drum.frame','mus',{gain:0.35,vars:4,gap:40,max:3,lvl:0.5,spatial:false,jit:0.03},(r)=>{const a=secs(0.4);thump(a,0,rr(r,150,175),rr(r,110,125),0.18,0.8,0.02);burst(a,0,0.04,r,'bp',rr(r,1500,2200),0.8,0.0005,0.05,0.6);return a});
// village life: a far-off murmur of voices and the odd tool, under the camera when many of yours are about
def('bed.village','amb',{gain:0.4,vars:1,lvl:0.35,sr:22050,loop:12,spatial:false},(r)=>bed(12,r,(a,c,rx,LL)=>{const R2=rng(191+c*13),F=new BQ().set('lp',1300,0.7);
 for(let k=0;k<16;k++){const race=pick(R2,['human','human','dwarf','elf','orc','goblin']),v=voiceLine(race,R2()<0.4?'f':'m',pick(R2,['select','move','work','build','stop']),k+c*40);mix(a,v,R2()*(LL-0.8)*SR,0.12+R2()*0.22)}
 for(let i=0;i<a.length;i++)a[i]=F.run(a[i]);for(let k=0;k<LL*0.8;k++){const tt=R2()*(LL-0.3),f=300+R2()*200;modal(a,tt*SR,[[f,0.05,0.12],[f*2.4,0.03,0.05]])}}));
// weather (rmSfx.weather): rain on leaves and ground, and thunder far off
def('bed.rain','amb',{gain:0.5,vars:1,lvl:0.5,sr:22050,loop:10,spatial:false},(r)=>{const amp=loopLFO(r,10,0.75,1,3);return bed(10,r,(a,c,rx,LL)=>{const n=noise(a.length,rng(161+c),'p');filt(n,'bp',2200,0.5);for(let i=0;i<a.length;i++)a[i]=n[i]*amp((i/SR)%10)*0.8;const R2=rng(171+c);
 for(let k=0;k<LL*140;k++){const s=Math.round(R2()*(a.length-200)),f=1800+R2()*4500,g=0.05+R2()*0.25,F=new BQ().set('bp',f,3);for(let i=0;i<120;i++)a[s+i]+=F.run(R2()*2-1)*g*Math.exp(-i/18)}})});
def('thunder','amb',{gain:0.55,vars:3,gap:8000,max:1,lvl:0.6,spatial:false},(r)=>{const d=4.5,a=secs(d),n=noise(d*SR,r,'b');filt(n,'lp',rr(r,180,320),0.7);
 shape(n,t=>(t<0.04?t/0.04:1)*Math.exp(-t*3.2)*(0.6+0.4*Math.sin(TAU*rr(r,1.5,3)*t)));mix(a,n,0,1);const cr=noise(0.5*SR,r,'w');filt(cr,'bp',900,0.7);env(cr,0.005,0.45);mix(a,cr,0,0.25);return roomTail(a,0.5,1.5,r)});
// --- Music instruments (rendered per note, cached) ---
function musLute(midi,r){return lute(mtof(midi),2.6,r,{t60:1.7,bright:0.45})}
function musHarp(midi,r){const s=pluck(mtof(midi),3.2,{r,t60:2.6,bright:0.65,pos:0.28});return fadeEdges(filt(s,'lp',5000,0.7),0,0.1)}
function musFlute(midi,dur,r){const f=mtof(midi),out=secs(dur+0.2),n=out.length,br=noise(n,r,'w'),B=new BQ().set('bp',f*2,3);let p=0;
 for(let i=0;i<n;i++){const t=i/SR,a=Math.min(1,t/0.09)*(t>dur?Math.max(0,1-(t-dur)/0.18):1),vib=1+0.006*Math.sin(TAU*5*t)*Math.min(1,Math.max(0,(t-0.25)/0.3));p+=TAU*f*vib/SR;out[i]=(Math.sin(p)+0.18*Math.sin(2*p)+0.06*Math.sin(3*p))*a*0.4+B.run(br[i])*a*0.05}return out}
function musPad(midis,dur,r){const out=[secs(dur),secs(dur)],n=out[0].length;for(const m of midis){const f=mtof(m);for(let c=0;c<2;c++){const F=new BQ().set('lp',1100,0.6);const det=[1,1.004+c*0.002,0.996-c*0.002];const ph=det.map(()=>r());
  for(let i=0;i<n;i++){const t=i/SR,x=i/n;let s=0;for(let k=0;k<3;k++){ph[k]+=f*det[k]/SR;ph[k]-=Math.floor(ph[k]);s+=saw(ph[k],f*det[k]/SR)}const a=Math.min(1,t/1.6)*Math.min(1,(dur-t)/2.0);out[c][i]+=F.run(s)*a*0.12}}}return out}
function musDrone(midi,dur,r){const out=[secs(dur),secs(dur)],f=mtof(midi);for(let c=0;c<2;c++){const F=new BQ().set('lp',500,0.7);let p=0,q=0;for(let i=0;i<out[c].length;i++){const t=i/SR,v=1+0.003*Math.sin(TAU*(4.6+c*0.3)*t);p+=f*v/SR;q+=f*2.003*v/SR;p-=Math.floor(p);q-=Math.floor(q);const a=Math.min(1,t/2.5)*Math.min(1,(dur-t)/3);out[c][i]=F.run(saw(p,f*v/SR)+saw(q,f*2.003*v/SR)*0.3)*a*0.3}}return out}

// render a book sound or an instrument note: returns {sr, ch:[Float32Array...]}
function render(name,variant,sr){const d=SND[name];if(!d)return null;const prev=SR;SR=sr||d.sr;try{const r=rng(hash(name+'#'+variant));let out=d.gen(r,variant);
  let ch=Array.isArray(out)?out:[out];if(d.loop){// loops keep their length; just set their level
   let pk=0,sum=0,cnt=0;for(const a of ch){pk=Math.max(pk,peakOf(a));for(let i=0;i<a.length;i++)sum+=a[i]*a[i];cnt+=a.length}const rm=Math.sqrt(sum/cnt);let g=rm>0?(0.18*d.lvl)/rm:1;if(pk*g>0.89)g=0.89/pk;ch=ch.map(a=>scale(a,g))}
  else ch=finish(ch,d.lvl);
  return {sr:SR,ch}}finally{SR=prev}}
function renderInst(kind,args,sr){const prev=SR;SR=sr||32000;try{const r=rng(hash(kind+JSON.stringify(args)));let out=kind==='lute'?musLute(args[0],r):kind==='harp'?musHarp(args[0],r):kind==='flute'?musFlute(args[0],args[1],r):kind==='pad'?musPad(args[0],args[1],r):musDrone(args[0],args[1],r);
  const ch=Array.isArray(out)?out:[out];let pk=0;for(const a of ch)pk=Math.max(pk,peakOf(a));if(pk>0.89)for(const a of ch)scale(a,0.89/pk);return {sr:SR,ch}}finally{SR=prev}}
function renderVoice(race,gender,kind,variant){const prev=SR;SR=44100;try{const a=voiceLine(race,gender,kind,variant);return {sr:SR,ch:finish([a],kind==='death'?0.66:0.6)}}finally{SR=prev}}
return {SND,render,renderInst,renderVoice,RACE,raceKey,VPLAN,stRMS,peakOf,clamp,lerp,rng,hash,rr,pick}}
const SYNTH=rmSynth();
if(typeof module!=='undefined'&&module.exports){module.exports=SYNTH;return}
if(typeof window==='undefined')return;
const {SND,render,renderInst,renderVoice,raceKey,clamp,lerp,rng,hash,rr,pick}=SYNTH;

// What is on (the user, 2026-10-23: "keep the new fight sounds everything else is good expect the music the ambiance
// sounds and we need a war drumns in battle"): the effects and interface sounds; the war drums and the forest bed in place
// of the synthesized music and ambience, which wait behind these.
const FEATURES={fx:true,ui:true,amb:false,music:false};
function allowed(d){return d.rec?true:d.cat==='fx'?FEATURES.fx:d.cat==='ui'?FEATURES.ui:d.cat==='amb'?FEATURES.amb:d.cat==='mus'?FEATURES.music:true}
// the recordings the server sent (Audio.dm): snd-<sound>-<take>.m4a, and the ambience bed
const FILES=new Set(Array.isArray(window.rmSoundFiles)?window.rmSoundFiles:[]),REC=new Map(),BED='amb-forest.m4a';
for(const f of FILES){const m=/^snd-(.+)-(\d+)\.m4a$/.exec(String(f));if(!m)continue;const L=REC.get(m[1])||[];L[+m[2]]=f;REC.set(m[1],L)}
// the war drum kit: level of each drum in the mix
const WD_GAIN={'wd.boom':0.9,'wd.soft':0.75,'wd.low':0.75,'wd.hand':0.55,'wd.timp':0.7,'wd.roll':0.6,'wd.crash':0.4,'wd.gong':0.5};
// the drums' own make-up on their path round the bus compressor (graph; the compressor adds about 7 dB of its own make-up
// to what goes through it): a battle's drums sit about 3 dB above where they were (the user asked for louder drums,
// 2026-10-23), the most the limiter allows before the fight sounds lose more than half a dB
const WD_MAKE=4.5;
for(const [n,L] of REC){const files=L.filter(Boolean);REC.set(n,files);if(!SND[n]){if(!WD_GAIN[n]){REC.delete(n);continue}SND[n]={cat:'wd',gain:WD_GAIN[n],vars:0,gap:25,max:8,lvl:0.7,sr:44100,jit:0.012,spatial:false}}SND[n].vars=files.length;SND[n].rec=true}

// =====================================================================================================================
// The engine (browser)
const CATS=[['master','Master'],['fx','Effects'],['ui','Interface'],['vo','Voices'],['amb','Ambience'],['wd','War drums'],['mus','Music']];
const DEFAULTS={master:70,fx:80,ui:55,vo:75,amb:40,wd:65,mus:35,bg:1};
const E={ctx:null,bus:{},buffers:new Map(),state:new Map(),live:[],prefs:Object.assign({},DEFAULTS),hidden:false,lastInput:0,played:0,skipped:0,errors:0,
 wait:new Map(),racesWarm:new Set(),unitAt:new Map(),killRace:new Map(),amb:{layers:new Map(),next:0,mix:{}},mus:{next:0,phrase:null,on:false},seenHits:new Set(),work:new Map(),lastAck:0,lastSelectVoice:0,model:null,unitsSel:'',z:0,night:null};
const now=()=>E.ctx?E.ctx.currentTime:0;
function V(){try{return typeof V3!=='undefined'?V3:null}catch(e){return null}}
function M(){try{return typeof model!=='undefined'?model:null}catch(e){return null}}
function log(e){E.errors++;if(E.errors<6)console.warn('audio:',e&&e.message||e)}

// --- settings: the player's profile on the server (HUD model "audio"), with a local copy for the web client ---
function loadLocal(){try{const s=JSON.parse(localStorage.getItem('rmAudio')||'null');if(s)applyPrefs(s,false)}catch(e){}}
function applyPrefs(p,fromServer){if(!p||typeof p!=='object')return;for(const k in DEFAULTS)if(typeof p[k]==='number'&&isFinite(p[k]))E.prefs[k]=clamp(Math.round(p[k]),0,100);syncUI();setGains()}
let saveT=0;
function savePrefs(){try{localStorage.setItem('rmAudio',JSON.stringify(E.prefs))}catch(e){}clearTimeout(saveT);saveT=setTimeout(()=>{E.sentPrefs=JSON.stringify(E.prefs);E.audioAt=Date.now();try{if(typeof send==='function')send('audioprefs',E.sentPrefs)}catch(e){log(e)}},700)}
function curve(v){v=clamp(v/100,0,1);return v*v}
function setGains(){if(!E.ctx)return;const t=now();for(const [k] of CATS){const g=k==='master'?curve(E.prefs.master)*(E.hidden&&E.prefs.bg?0:1):curve(E.prefs[k]);const b=k==='master'?E.master:E.bus[k];if(b)b.gain.setTargetAtTime(g,t,0.06)}
 if(E.wdOut)E.wdOut.gain.setTargetAtTime(curve(E.prefs.master)*(E.hidden&&E.prefs.bg?0:1)*WD_MAKE,t,0.06)}

// --- the graph ---
function makeIR(ctx,len,decay,bright){const n=Math.round(len*ctx.sampleRate),b=ctx.createBuffer(2,n,ctx.sampleRate),r=rng(hash('ir'+len));
 for(let c=0;c<2;c++){const d=b.getChannelData(c);let lp=0;for(let i=0;i<n;i++){const t=i/ctx.sampleRate,k=clamp(bright-t*0.35,0.04,0.95);lp+=((r()*2-1)-lp)*k;d[i]=lp*Math.exp(-t*6.9/decay)*(i<ctx.sampleRate*0.004?i/(ctx.sampleRate*0.004):1)}
  for(const [tt,g] of [[0.011,0.5],[0.019,0.35],[0.027,0.3],[0.041,0.22]]){const j=Math.round((tt+c*0.003)*ctx.sampleRate);if(j<n)d[j]+=g}}return b}
// the chain: categories -> master -> a gentle bus compressor -> make-up gain -> a limiter, so a quiet scene sits at a
// normal level and the busiest battle never clips; two rooms (open air, caves) fed by world sounds and voices
function graph(ctx,G){const comp=ctx.createDynamicsCompressor(),make=ctx.createGain(),lim=ctx.createDynamicsCompressor(),out=ctx.createGain();G.master=ctx.createGain();
 const setc=(c,th,kn,ra,at,re)=>{try{c.threshold.value=th;c.knee.value=kn;c.ratio.value=ra;c.attack.value=at;c.release.value=re}catch(e){}};
 setc(comp,-22,8,4,0.003,0.25);make.gain.value=2.6;setc(lim,-4,0,20,0.001,0.06);out.gain.value=0.92;
 // tone: rumble below what any speaker plays is cut (it only eats the limiter's headroom), and a little presence added
 const hp=ctx.createBiquadFilter(),pres=ctx.createBiquadFilter();hp.type='highpass';hp.frequency.value=35;hp.Q.value=0.7;pres.type='highshelf';pres.frequency.value=3000;pres.gain.value=1.5;
 G.master.connect(hp);hp.connect(pres);pres.connect(comp);comp.connect(make);make.connect(lim);lim.connect(out);out.connect(ctx.destination);G.out=out;
 G.bus={};for(const [k] of CATS)if(k!=='master'){G.bus[k]=ctx.createGain();G.bus[k].connect(G.master)}
 G.duck=ctx.createGain();G.bus.mus.disconnect();G.bus.mus.connect(G.duck);G.duck.connect(G.master);
 // the war drums go round the bus compressor, straight to the limiter (with the master volume and their own make-up), so
 // loud drums never press the fight sounds down; their own low cut keeps rumble out of the limiter
 // and a voice and compressor of their own: less sub-bass (headroom no laptop speaker plays), more body and skin, so they
 // sound louder for the same peaks; the compressor makes them fuller and keeps their peaks off the limiter
 const bq=(type,f,q,g)=>{const b=ctx.createBiquadFilter();b.type=type;b.frequency.value=f;b.Q.value=q;if(g)b.gain.value=g;return b};
 const wdEq=[bq('highpass',70,0.7),bq('peaking',160,1,4),bq('highshelf',2500,0.7,5)],wdComp=ctx.createDynamicsCompressor();setc(wdComp,-36,4,8,0.002,0.25);
 G.wdOut=ctx.createGain();G.wdOut.gain.value=WD_MAKE;G.bus.wd.disconnect();G.bus.wd.connect(wdEq[0]);wdEq[0].connect(wdEq[1]);wdEq[1].connect(wdEq[2]);wdEq[2].connect(wdComp);wdComp.connect(G.wdOut);G.wdOut.connect(lim);
 G.verb={};for(const [k,len,dec,br] of [['air',1.6,1.3,0.55],['cave',3.4,3.0,0.4]]){const cv=ctx.createConvolver();cv.buffer=makeIR(ctx,len,dec,br);const g=ctx.createGain();g.gain.value=k==='air'?1:0;const send=ctx.createGain();send.gain.value=k==='air'?0.22:0.55;send.connect(cv);cv.connect(g);g.connect(G.master);G.verb[k]={send,ret:g}}
 G.verbIn=ctx.createGain();G.verbIn.connect(G.verb.air.send);G.verbIn.connect(G.verb.cave.send);return G}
function build(){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return false;const ctx=E.ctx=new AC();graph(ctx,E);
 E.meter=ctx.createAnalyser();E.meter.fftSize=1024;E.out.connect(E.meter);setGains();return true}
function startAudio(){if(E.ctx)return true;try{if(!build())return false}catch(err){log(err);return false}roomFor(E.z||1);loadRecs();prewarm();setTimeout(ambTick,600);musTick();wdTick();onVisibility();return true}
// the recordings: fetched and decoded as soon as the audio exists, four at a time, the bed first
function decode(f){return fetch(f).then(r=>{if(!r.ok)throw new Error(f+': '+r.status);return r.arrayBuffer()}).then(ab=>new Promise((ok,no)=>E.ctx.decodeAudioData(ab,ok,no)))}
function loadRecs(){if(E.recLoad)return;const q=[];if(FILES.has(BED))q.push([BED,BED]);for(const [n,files] of REC)files.forEach((f,v)=>q.push([n+'#'+v,f]));
 const R=E.recLoad={n:q.length,ok:0,fail:0};
 const next=()=>{const it=q.shift();if(!it)return;decode(it[1]).then(b=>{E.buffers.set(it[0],b);R.ok++;if(it[0]===BED)bedStart()},e=>{R.fail++;log(e&&e.message?e:new Error(it[1]+': not decoded'))}).then(next)};
 for(let k=0;k<4;k++)next()}
function unlock(e){if(e&&e.isTrusted===false)return;E.lastInput=performance.now();if(e)E.gestured=true;if(!startAudio())return;
 if(E.ctx.state==='suspended'&&!(E.hidden&&E.prefs.bg))E.ctx.resume().catch(()=>{})}
// where the web view lets a page play before any click (the app's may), the world is heard from the start; elsewhere the
// context waits, suspended, for the first click or key
function tryEarly(){if(E.ctx||!(window.AudioContext||window.webkitAudioContext))return;try{const AC=window.AudioContext||window.webkitAudioContext,probe=new AC();
 const go=()=>{const ok=probe.state==='running';probe.close().catch(()=>{});if(ok&&!E.ctx)startAudio()};if(probe.state==='running')go();else setTimeout(go,250)}catch(e){}}
['pointerdown','keydown','touchstart'].forEach(t=>document.addEventListener(t,unlock,true));

// --- buffers: rendered by a worker made from the synth's own source (the page only copies finished channels in),
// cached, and asked for ahead of time: every one-shot at load, voices for the races you have, music a phrase ahead ---
const WSRC='"use strict";var S=('+rmSynth.toString()+')();onmessage=function(e){var q=e.data,R;try{R=q.k==="snd"?S.render(q.a[0],q.a[1]):q.k==="inst"?S.renderInst(q.a[0],q.a[1]):S.renderVoice(q.a[0],q.a[1],q.a[2],q.a[3])}catch(err){postMessage({id:q.id,err:String(err&&err.message||err)});return}if(!R){postMessage({id:q.id,err:"nothing to render: "+q.k+" "+JSON.stringify(q.a)});return}postMessage({id:q.id,sr:R.sr,ch:R.ch},R.ch.map(function(a){return a.buffer}))}';
let W=null,wseq=0;const wpend=new Map();
function renderNow(k,a){try{return k==='snd'?render(a[0],a[1]):k==='inst'?renderInst(a[0],a[1]):renderVoice(a[0],a[1],a[2],a[3])}catch(e){log(e);return null}}
function worker(){if(W!==null)return W;W=false;try{const w=new Worker(URL.createObjectURL(new Blob([WSRC],{type:'text/javascript'})));
  w.onmessage=e=>{const d=e.data,q=wpend.get(d.id);if(!q)return;wpend.delete(d.id);if(d.err){log(d.err);q.fin(null)}else q.fin({sr:d.sr,ch:d.ch})};
  w.onerror=e=>{log('worker: '+(e&&e.message||'failed'));W=false;for(const [id,q] of [...wpend]){wpend.delete(id);q.fin(renderNow(q.k,q.a))}};W=w}catch(e){W=false}return W}
function toBuffer(R){const b=E.ctx.createBuffer(R.ch.length,R.ch[0].length,R.sr);R.ch.forEach((a,c)=>{if(b.copyToChannel)b.copyToChannel(a,c);else b.getChannelData(c).set(a)});return b}
// the buffer if it is ready (converted for the audio once it has started), else null after asking for it; cb runs when it lands
// low = ahead-of-time: those trickle to the worker one by one, so a sound wanted now never queues behind them
const lowQ=[];
function pump(){const wk=worker();if(!wk)return;let low=0;for(const q of wpend.values())if(q.low)low++;while(lowQ.length&&low<1){const q=lowQ.shift();if(!E.wait.has(q.key)||E.buffers.has(q.key))continue;q.low=true;low++;const id=++wseq;wpend.set(id,q);wk.postMessage({id,k:q.k,a:q.a})}}   /* one at a time: the worker runs them in order, so anything wanted now waits behind one at most */
function getBuf(key,k,a,cb,low){const b=E.buffers.get(key);
 if(b){if(!b.ch)return b;if(!E.ctx)return null;const B=toBuffer(b);E.buffers.set(key,B);return B}
 const w=E.wait.get(key);if(w){if(cb)w.push(cb);if(!low){const i=lowQ.findIndex(q=>q.key===key);if(i>=0){const q=lowQ.splice(i,1)[0],wk=worker(),id=++wseq;wpend.set(id,q);wk.postMessage({id,k:q.k,a:q.a})}}return null}
 const list=cb?[cb]:[];E.wait.set(key,list);
 const fin=R=>{E.wait.delete(key);if(R){E.buffers.set(key,R);for(const f of list)try{f()}catch(e){log(e)}}pump()};
 const wk=worker();if(wk){const q={key,fin,k,a};if(low){if(low==='front')lowQ.unshift(q);else lowQ.push(q);pump()}else{const id=++wseq;wpend.set(id,q);wk.postMessage({id,k,a})}}else setTimeout(()=>fin(renderNow(k,a)),0);return null}
const VTAKES=4;   // takes per voice line: a run of clicks never repeats the last one
function vkey(race,g,kind,v){return 'vo|'+raceKey(race)+'|'+g+'|'+kind+'|'+v}
const FIRST=['ui.arrive','ui.click','ui.hover','ui.open','ui.close','ui.tab','cmd.move','cmd.attack','cmd.work','cmd.build','ui.error','swing.light','swing.heavy','hit.flesh','hit.armor','parry','block','chop','mine','build'];
function prewarm(){if(E.warmed)return;E.warmed=true;for(const n of FIRST.concat(Object.keys(SND).filter(n=>!FIRST.includes(n)&&!SND[n].loop)))if(!SND[n].rec&&allowed(SND[n]))for(let v=0;v<SND[n].vars;v++)getBuf(n+'#'+v,'snd',[n,v],null,true);
 if(FEATURES.amb)for(const n of ['bed.wind','bed.leaves'])getBuf(n+'#0','snd',[n,0],null,true);warmVoices('human','m')}
// unit voices are off: the user, 2026-10-23 ("no unit speechs"); the voice synth stays in the book
var VOICES_ON=false;   // var: read safely even before this line runs
function warmVoices(race,g){if(!VOICES_ON)return;const k=raceKey(race)+g;if(E.racesWarm.has(k))return;E.racesWarm.add(k);for(const kind of ['select','move','attack','work','build','death','hurt'])for(let v=0;v<VTAKES;v++)getBuf(vkey(race,g,kind,v),'voice',[race,g,kind,v],null,true)}

// --- where a world sound sits: pan and level from the camera ---
function place(x,y){const v=V();if(!v||!v.on||typeof x!=='number'||typeof y!=='number')return {g:1,pan:0,far:0};
 const rx=x-(v.cx||0),ry=y-(v.cy||0),yaw=v.yaw||0,dist=v.dist||15,right=rx*Math.cos(yaw)+ry*Math.sin(yaw),d=Math.hypot(rx,ry),R=6+0.45*dist;
 let g=1/(1+Math.pow(d/R,2))*Math.sqrt(clamp(16/dist,0.45,1));return {g,pan:clamp(right/(R*1.1),-0.85,0.85),far:clamp((d-R)/(2.5*R),0,1)}}

// --- playing: variety, throttling and a voice budget ---
const MAXLIVE=30;
function reap(){const t=now();E.live=E.live.filter(l=>l.end>t)}
function hush(){const t=now();for(const l of E.live){try{l.gain.gain.setTargetAtTime(0,t,0.02);l.end=t+0.05}catch(e){}}if(voiceLive)voiceLive.end=t}
function connectOut(node,cat,pan,far,wet){const ctx=E.ctx;let n=node;
 if(far>0.05){const lp=ctx.createBiquadFilter();lp.type='lowpass';lp.frequency.value=lerp(18000,1800,far);n.connect(lp);n=lp}
 if(pan&&ctx.createStereoPanner){const p=ctx.createStereoPanner();p.pan.value=pan;n.connect(p);n=p}
 n.connect(E.bus[cat]);if(wet>0){const s=ctx.createGain();s.gain.value=wet;n.connect(s);s.connect(E.verbIn)}}
function start(b,cat,g,o){const ctx=E.ctx,src=ctx.createBufferSource();src.buffer=b;src.playbackRate.value=o.rate||1;const gn=ctx.createGain();gn.gain.value=g;src.connect(gn);
 connectOut(gn,cat,o.pan||0,o.far||0,o.wet==null?(cat==='fx'?0.5:cat==='vo'?0.3:cat==='amb'?0.4:0.12):o.wet);const at=now()+(o.delay||0)/1000;src.start(at);
 const l={src,gain:gn,start:at,end:at+b.duration/(o.rate||1),g,name:o.name,cat};E.live.push(l);src.onended=()=>{try{gn.disconnect()}catch(e){}};return l}
function play(name,o){o=o||{};if(!E.ctx||E.ctx.state!=='running')return null;const d=SND[name];if(!d||!allowed(d))return null;
 try{reap();const t=now();let st=E.state.get(name);if(!st){st={last:-1,n:0,v:-1};E.state.set(name,st)}
  let g=d.gain*(o.gain==null?1:o.gain),pan=o.pan||0,far=0;
  if(d.spatial&&o.x!=null){const P=place(o.x,o.y);g*=P.g;pan=P.pan;far=P.far}
  if(g<0.02){E.skipped++;return null}
  // throttling works on start times (sounds may be scheduled ahead): no two starts of one sound closer than its gap,
  // no more than its own voice count sounding at once, 30 in all; a louder (nearer) one may take a quieter one's place
  const at=t+(o.delay||0)/1000;st.times=(st.times||[]).filter(x=>x>t-Math.max(2,d.gap/1000+0.5));
  if(st.times.some(x=>Math.abs(x-at)<d.gap/1000)){E.skipped++;return null}
  // a crowd of the same sound (ten woodcutters, a big melee) thickens rather than just getting louder
  const dense=st.times.filter(x=>Math.abs(x-at)<1).length;if(dense>3)g*=Math.sqrt(3/dense);
  const over=l=>l.start<=at+0.01&&l.end>at,mine=E.live.filter(l=>l.name===name&&over(l));
  if(mine.length>=d.max){const q=mine.reduce((a,b)=>a.g<b.g?a:b);if(q.g>=g){E.skipped++;return null}try{q.gain.gain.setTargetAtTime(0,Math.max(t,at),0.015);q.end=Math.max(t,at)+0.05}catch(e){}}
  const all=E.live.filter(over);if(all.length>=MAXLIVE){const q=all.reduce((a,b)=>a.g<b.g?a:b);if(q.g>=g){E.skipped++;return null}try{q.gain.gain.setTargetAtTime(0,Math.max(t,at),0.015);q.end=Math.max(t,at)+0.05}catch(e){}}
  // a different take each time, never the same twice in a row
  let v=o.variant;if(v==null){v=Math.floor(Math.random()*d.vars);if(d.vars>1&&v===st.v)v=(v+1)%d.vars}st.v=v;
  const asked=performance.now(),b=d.rec?E.buffers.get(name+'#'+v):getBuf(name+'#'+v,'snd',[name,v],()=>{if(performance.now()-asked<300)play(name,Object.assign({},o,{variant:v}))});if(!b){if(d.rec)E.skipped++;return null}st.last=at;st.times.push(at);E.played++;
  return start(b,d.cat,g*(1+(Math.random()-0.5)*0.12),{rate:(o.rate||1)*(1+(Math.random()-0.5)*2*d.jit),pan,far,delay:o.delay,name,wet:o.wet})}catch(e){log(e);return null}}

// --- voices: one at a time (a new answer cuts the old one short), a little ducking of the music ---
let voiceLive=null;
function speak(race,gender,kind,o){o=o||{};if(!VOICES_ON||!E.ctx||E.ctx.state!=='running')return;try{const t=now();
  if(voiceLive&&voiceLive.end>t&&o.soft)return;
  let v=o.variant;if(v==null){const sk='vo|'+raceKey(race)+gender+kind,st=E.state.get(sk)||{v:-1};v=(st.v+1+Math.floor(Math.random()*3))%VTAKES;st.v=v;E.state.set(sk,st)}
  const asked=performance.now(),b=getBuf(vkey(race,gender,kind,v),'voice',[race,gender,kind,v],()=>{if(performance.now()-asked<450)speak(race,gender,kind,Object.assign({},o,{variant:v}))});if(!b)return;
  if(voiceLive&&voiceLive.end>t){try{voiceLive.gain.gain.setTargetAtTime(0,t,0.03)}catch(e){}}let g=o.gain||1,pan=0,far=0;if(o.x!=null&&o.place){const P=place(o.x,o.y);g*=Math.max(0.35,P.g);pan=P.pan*0.6;far=P.far*0.5}
  voiceLive=start(b,'vo',g*0.9,{pan,far,rate:1+(Math.random()-0.5)*0.04,name:'voice'});E.played++;
  E.duck.gain.setTargetAtTime(0.55,t,0.05);E.duck.gain.setTargetAtTime(1,t+b.duration,0.4)}catch(e){log(e)}}
function genderOf(u){const g=String(u&&u.gender||'').toLowerCase();return g[0]==='f'?'f':'m'}

// --- order acknowledgements ---
const ORDER_CUE={move:'cmd.move',attack:'cmd.attack',gather:'cmd.work',chop:'cmd.work',mine:'cmd.work',build:'cmd.build',craft:'cmd.build',deliver:'cmd.move',guard:'cmd.attack',patrol:'cmd.move',stop:'ui.click',cast:'cmd.attack'};
const ORDER_VOICE={move:'move',attack:'attack',gather:'work',chop:'work',mine:'work',build:'build',craft:'build',deliver:'deliver',guard:'guard',patrol:'move',stop:'stop',cast:'cast'};
function selectedUnits(){const m=M();return m&&Array.isArray(m.units)?m.units.filter(u=>u.selected):[]}
const ACCENT={orc:'accent.orc',dragon:'accent.orc',dwarf:'accent.dwarf',elf:'accent.elf',goblin:'accent.goblin',kobold:'accent.goblin',skeleton:'accent.bone',zombie:'accent.bone',vampire:'accent.bone',lizardman:'accent.hiss',spider:'accent.hiss'};
function order(kind,o){o=o||{};kind=String(kind||'move').toLowerCase();if(!ORDER_VOICE[kind])kind='move';const t=performance.now();if(t-E.lastAck<180)return;E.lastAck=t;
 play(ORDER_CUE[kind]||'cmd.move');const sel=selectedUnits(),u=o.unit||sel[0];if(!u)return;const ac=ACCENT[raceKey(u.race)];if(ac)play(ac,{delay:25});speak(u.race,genderOf(u),ORDER_VOICE[kind],{x:u.x,y:u.y})}
// what a click in 3D will do, from what is under it (the server decides; this answers at once)
function predictClick(value){const p=String(value||'').split('|'),x=+p[0],y=+p[1],ref=p[2]||'';const v=V();if(!selectedUnits().length)return null;
 if(ref&&v&&Array.isArray(v.things)){const t=v.things.find(o=>(o.ref||o.id)===ref);if(t){if(t.kind==='mine')return null;if(t.kind==='npc'&&!t.peace||t.kind==='animal'||t.kind==='player'&&t.war)return 'attack';if(t.kind==='item')return 'gather';if(t.kind==='station')return 'craft'}}
 let K=null;try{if(typeof v3kindAt==='function')K=v3kindAt(x,y)}catch(e){}if(K&&K.kind==='tree')return 'chop';if(K&&(K.kind==='wall'&&K.blocks||K.kind==='block'))return 'mine';return 'move'}
const SEND_ORDER={mineroof:'mine',carve:'mine',paint3d:'build',placeworkshop:'build',wallramp:'build',wallstairs:'build',captureorder:'attack',attackorder:'attack',chainorder:'attack',attackpart:'attack',feedbeast:'deliver',carrybody:'deliver',caveenter:'move',dropoff:'deliver',stance:'guard',defensemode:'guard',craft:'craft',build:'build',job:'gather',unitability:'cast',weaponmove:'cast',specialaim:'cast'};
function onSend(a,v){E.lastInput=performance.now();if(!E.ctx)return;
 if(a==='click3d'){const k=predictClick(v);if(k)order(k);else E.pendingSelect=performance.now();return}
 if(a==='boxrefs'||a==='box3d'||a==='selectmany'){E.pendingSelect=performance.now();return}
 if(a==='action'&&/^(stop|cancel|halt)$/.test(String(v))){order('stop');return}
 if(/^(paint3d|placeworkshop|wallramp|wallstairs|carve)$/.test(a))play('ui.place');
 if(SEND_ORDER[a]&&selectedUnits().length)order(SEND_ORDER[a]);
 if(a==='save'||a==='savegame')play('ui.save');
 // goods: coins for a deal, a clink when gear is handled from the bag
 if(a==='trade'&&/^(buy|sell)\|/.test(String(v))||a==='market'&&/^buy\b/.test(String(v)))play('ui.coins');
 else if(/^(inventory|giveitem|useitem|equipbest|autouse)$/.test(a))play('ui.equip')}

// --- interface sounds from the page itself ---
function ctl(el){return el&&el.closest?el.closest('button,[role=tab],[role=menuitem],summary,select,input[type=checkbox],input[type=range],a[href]'):null}
let hoverEl=null,hoverAt=0;
document.addEventListener('pointerover',e=>{const b=ctl(e.target);if(!b||b===hoverEl)return;hoverEl=b;if(b.disabled)return;const t=performance.now();if(t-hoverAt<70)return;hoverAt=t;if(e.isTrusted)play('ui.hover')   /* sweeping across a row of buttons ticks, it doesn't rattle */},true);
document.addEventListener('pointerout',e=>{if(hoverEl&&!hoverEl.contains(e.relatedTarget))hoverEl=null},true);
document.addEventListener('pointerdown',e=>{if(!e.isTrusted||e.button!==0)return;if(e.target&&(e.target.id==='minimap'||e.target.id==='wmCanvas')){play('ui.pick');return}   /* a jump on the minimap or world map */
 const b=ctl(e.target);if(!b)return;E.lastUiClick=performance.now();
 if(b.disabled||b.getAttribute('aria-disabled')==='true'){play('ui.error',{gain:0.6});return}
 if(b.matches('[role=tab],nav button,.hftabs button,[data-hftab],[data-tab]'))play('ui.tab');
 else if(b.matches('input[type=range]'))return;
 else play('ui.click')},true);
// panels: open/close sounds when the player opened them; a chime when the game opens one by itself
const PANELS=['settings','worldmap','usecard','askcard','loghist','daycard','awaycard','borderControls','buildPalette','magicTargets','unitGroups','menu3d'];
const SELF_OPEN={askcard:'ui.notify',daycard:'ui.notify',awaycard:'ui.notify'};
function panelOpen(el){return el.tagName==='DIALOG'?el.open:!el.hidden}
let panelState=new Map(),panelAt=0;
function watchPanels(){const obs=new MutationObserver(list=>{const t=performance.now();for(const m of list){const el=m.target;if(!PANELS.includes(el.id))continue;const open=panelOpen(el);if(panelState.get(el.id)===open)continue;panelState.set(el.id,open);
  if(t-panelAt<120)continue;panelAt=t;const user=t-E.lastInput<1500;
  const soft=t-(E.lastUiClick||0)<300?0.6:1;   /* softer right after the button's own click */
  if(open)play(user?(el.id==='menu3d'?'ui.tab':'ui.open'):(SELF_OPEN[el.id]||null)||'ui.open',{gain:user?soft:0.7});else if(user)play('ui.close',{gain:soft})}});
 for(const id of PANELS){const el=document.getElementById(id);if(el){panelState.set(id,panelOpen(el));obs.observe(el,{attributes:true,attributeFilter:['hidden','open']})}}
 // the main panel and the log open by a class on the body; attack mode and spell aiming arm the same way
 const flags=()=>{const c=document.body.classList;return {panel:c.contains('panel-open'),log:c.contains('logopen'),atk:c.contains('attacking'),aim:c.contains('aiming'),bag:c.contains('bagdragging')}};let was=flags();
 new MutationObserver(()=>{const f=flags(),t=performance.now(),user=t-E.lastInput<1500;
  if(user&&(f.panel!==was.panel||f.log!==was.log)&&t-panelAt>=120){panelAt=t;play((f.panel&&!was.panel)||(f.log&&!was.log)?'ui.open':'ui.close',{gain:t-(E.lastUiClick||0)<300?0.6:1})}   /* softer right after the button's own click */
  if(f.atk&&!was.atk)play('cmd.attack',{gain:0.8});if(f.aim&&!was.aim)play('ui.aim');if(f.bag!==was.bag)play(f.bag?'ui.bagpick':'ui.bagdrop');was=f}).observe(document.body,{attributes:true,attributeFilter:['class']})}

// --- reading the model ---
const HIT_SPELL={burn:'spell.fire',chill:'spell.frost',shock:'spell.shock',venom:'spell.poison',smite:'spell.holy',drain:'spell.dark',astral:'spell.astral',webbed:'web',bleed:'bleed',ko:'ko'};
function swingFor(w){w=String(w||'');return /axe|mace|hammer|club|maul|morning/.test(w)?'swing.heavy':/spear|pike|lance|fork/.test(w)?'swing.thrust':'swing.light'}
function onHits(list){if(!Array.isArray(list))return;const fresh=[];for(const h of list){if(!h||E.seenHits.has(h.id))continue;E.seenHits.add(h.id);fresh.push(h)}
 if(E.seenHits.size>600)E.seenHits=new Set([...E.seenHits].slice(-300));if(!E.hitsPrimed){E.hitsPrimed=true;return}   // the first model's hits are old news
 // closest first, so the throttle keeps the ones that matter
 fresh.sort((a,b)=>place(b.x,b.y).g-place(a.x,a.y).g);
 // a fight on screen (several blows within a few seconds) brings the battle drums in under the music
 const nowP=performance.now(),notBlow=new Set(['bleed','burn','venom','chill','shock','drain','smite','astral','webbed','echo','wall','wreck','drop','limb','rout','turned','save','cover','flank','rear','charge','crit']);   /* ticks and words, not blows: a wounded unit's bleeding (Stumps.dm) held the drums on long after the fight (the owner, 10-28: "battle music plays longer than it needs to when out of battle") */
 for(const h of fresh)if(!(typeof h.k==='string'&&h.k[0]==='+')&&!notBlow.has(h.k)&&place(h.x,h.y).g>0.2){E.fightHits=(E.fightHits||[]).filter(x=>nowP-x<5000);E.fightHits.push(nowP)}
 if(E.fightHits&&E.fightHits.length>=4){if(!E.battle||E.battle.until<now())E.battle={next:now()+0.15,step:0};E.battle.until=now()+7}
 // world-look sounds the landing itself (rmSfx.at('impact'|'fall'), the frame the blow shows) for a blow on a unit in view:
 // then the feed gives only the striker's side, and the death comes with the fall
 const wl=wlHandles();
 for(const h of fresh.slice(0,10)){const k=h.k;
  if(typeof k==='string'&&k[0]==='+'){play('splash',{x:h.x,y:h.y});continue}
  const eng=h.w==='ram'||h.w==='catapult'||h.w==='ballista',handled=wl&&k!=='miss'&&k!=='bleed'&&!eng&&(k==='wall'||k==='wreck'||wlUnitAt(h.x,h.y));
  if(k==='wall'&&!handled){play('siege.impact',{x:h.x,y:h.y});continue}
  if(k==='kill'){const t=wlUnitAt(h.x,h.y);E.killRace.set(h.x+','+h.y,{race:(E.unitAt.get(h.x+','+h.y)||{}).race||t&&t.model||'human',g:genderOf(E.unitAt.get(h.x+','+h.y)),at:performance.now()});if(h.mine)play('ui.warn',{delay:600,gain:0.5})}
  // one update brings a batch: spread it over a third of a second, as the blows really fell; projectiles land after their flight
  const spread=fresh.length>1&&!handled?Math.random()*320:0;let late=0;
  if(h.p){const l=Math.hypot(h.x-h.ax,h.y-h.ay);late=h.p==='arrow'?90+l*55:h.p==='bolt'?60+l*30:h.p==='boulder'?400+l*90:150+l*85;
   play(h.p==='boulder'?'siege.launch':'bow.shoot',{x:h.ax,y:h.ay,rate:h.p==='bolt'?0.75:1,delay:spread})}
  else if(!eng&&(h.w&&k!=='bleed'&&!HIT_SPELL[k]||k==='miss'))play(swingFor(h.w),{x:h.ax!=null?h.ax:h.x,y:h.ay!=null?h.ay:h.y,delay:spread});
  if(handled)continue;
  const at={x:h.x,y:h.y,delay:late+(h.p?0:70)+spread};
  if(k==='miss'){if(h.p)play('arrow.hit',Object.assign({},at,{gain:0.5}))}
  else{landing(h,at);if(k==='kill')play('death.fall',Object.assign({},at,{delay:at.delay+120}))}}
 // the death cry of the fallen (when world-look does not show the fall), or a grunt from one of yours taking a heavy
 // blow (one voice per batch); your own units speak with their race and sex, others with the race their model shows
 const kill=!wl&&fresh.find(h=>h.k==='kill'),hurt=!kill&&fresh.find(h=>h.mine&&h.n>=8&&h.k!=='miss'&&h.k!=='block'&&h.k!=='parry');const H=kill||hurt;
 if(H){const P=place(H.x,H.y);if(P.g>0.15){const u=E.unitAt.get(H.x+','+H.y),t=!u&&wlUnitAt(H.x,H.y);
  speakWorld(u?u.race:t&&t.model||'human',u?genderOf(u):'m',kill?'death':'hurt',H.x,H.y,P,kill?250:90)}}}
// the struck one's side of a blow: flesh, armour, a parry's ring, a shield, a spell, an arrow, a boulder
function landing(h,at){const k=h.k;
 if(k==='parry'||k==='guard')play('parry',at);
 else if(k==='block')play('block',at);
 else if(HIT_SPELL[k])play(HIT_SPELL[k],at);
 else if(k==='wall'||k==='wreck'||h.w==='catapult'||h.p==='boulder')play('siege.impact',at);
 else if(h.w==='ram')play('ram.hit',at);
 else if(h.p||h.w==='bow'||h.w==='crossbow')play('arrow.hit',at);
 else if(k==='stagger')return;   // the blow that staggered was heard already
 // a heavy blow (a mace, a cleave, 30 or more: the yellow number): a deeper, louder body hit with no ring. The user turned
 // down the "high pitch synth sound when a yellow number appeared" (hit.big's pings), 2026-10-23
 else if(h.n>=30||k==='crush'||k==='big'||k==='cleave')play('hit.flesh',Object.assign({},at,{rate:0.86,gain:1.2}));
 // any other blow that lands: the body hit. hit.armor's bell-like ring heard as "a chime when enemy hits a player for
 // damage" (the user, 2026-10-23), so it is no longer used
 else play('hit.flesh',at)}
function wlHandles(){const v=V();try{return !!(v&&v.on&&typeof v3impact==='function')}catch(e){return false}}
function wlUnitAt(x,y){const v=V();return v&&Array.isArray(v.things)?v.things.find(o=>o.x===x&&o.y===y&&!o.ly&&(o.kind==='mine'||o.kind==='npc'||o.kind==='player'||o.kind==='animal')):null}
// rmSfx.at('impact'|'fall') from world-look: the frame a blow shows landing, the moment a killed unit slumps
let impactsAt=[];
function onImpact(x,y,info){info=info||{};const t=performance.now();impactsAt=impactsAt.filter(a=>t-a<60);
 // several landing in one frame: a few tens of milliseconds apart, so the throttle keeps them; a melee blow lands just after its swing
 const melee=!/bow/.test(String(info.w||''))&&info.w!=='catapult',delay=(melee?60:0)+impactsAt.length*(35+Math.random()*25);impactsAt.push(t);
 landing({k:info.k,w:info.w,n:info.k==='kill'?0:0},{x,y,delay})}
function onFall(x,y){const P=place(x,y);play('death.fall',{x,y});const R=E.killRace.get(x+','+y);if(R&&P.g>0.15)speakWorld(R.race,R.g,'death',x,y,P,60)}
function speakWorld(race,g,kind,x,y,P,delay){if(!VOICES_ON||!E.ctx)return;try{const st=E.state.get('vo.world')||{last:0};const t=performance.now();if(t-st.last<900)return;st.last=t;E.state.set('vo.world',st);
 const v=Math.floor(Math.random()*VTAKES),b=getBuf(vkey(race,g,kind,v),'voice',[race,g,kind,v]);if(!b)return;start(b,'vo',0.8*P.g,{pan:P.pan,far:P.far,delay,name:'voice.world'})}catch(e){log(e)}}
function onWork(list){if(!Array.isArray(list))return;const v=V();const W=new Map();
 for(const w of list){const [x,y,dmg,blows,dx,dy,broken]=w,key=x+','+y,p=E.work.get(key);W.set(key,{blows,broken});if(!p){continue}
  let K=null;try{if(typeof v3kindAt==='function')K=v3kindAt(x,y)}catch(e){}const tree=K&&K.kind==='tree';
  if(broken&&!p.broken){play(tree?'tree.fall':'rock.break',{x,y});continue}
  // many hands at once: spread the blows of one update over a third of a second instead of one lost in the throttle
  const n=Math.min(3,blows-p.blows),sp=list.length>1?Math.random()*350:0;for(let k=0;k<n;k++)play(tree?'chop':K&&K.vein?'mine.ore':'mine',{x,y,delay:sp+k*150})}
 E.work=W}
// units at work beyond chopping and mining (from what their card says they are doing): builders hammer, smiths ring
// the anvil, carpenters saw; a few at a time, near the camera
const WORK_SND=[[/^(building|constructing|raising|repairing|hammering)\b/i,'build'],
 [/^(making|forging|smelting|smithing|trying)\b.*\b(sword|axe|mace|spear|dagger|helm|chest|armou?r|shield|pick|ingot|bar|chain|nail|blade|metal|iron|silver|gold|adamant|automail)/i,'craft.anvil'],
 [/^(making|sawing|carving|trying)\b.*\b(bed|chair|table|door|bow|staff|club|barrel|crate|plank|wood|wooden|cart|bridge|ladder|shelf|throne)/i,'craft.saw'],
 [/^(making|cooking|brewing|tanning|sewing|weaving|crafting|trying)\b/i,'craft.tinker'],[/^(tilling|planting|digging|sowing)\b/i,'dig']];
let lastWorkTick=0;const lastOrder=new Map();
function workTick(m){const t=performance.now();if(t-lastWorkTick<700)return;lastWorkTick=t;if(!m||!Array.isArray(m.units))return;let n=0;
 for(const u of m.units){const s=String(u.order||''),was=lastOrder.get(u.ref);lastOrder.set(u.ref,s);
  // goods set down at the stockpile
  if(was!=null&&s!==was&&/^(Stored|Delivered)\b/.test(s)&&place(u.x,u.y).g>0.1)play('drop',{x:u.x,y:u.y});
  else if(was!=null&&s!==was&&/^(Picked up|Took|Gathered|Fetched)\b/.test(s)&&place(u.x,u.y).g>0.1)play('pickup',{x:u.x,y:u.y});
  if(n>=3)continue;if(u.paused||u.z!==E.z&&E.z)continue;let snd=null;for(const [re,nm] of WORK_SND)if(re.test(s)){snd=nm;break}
  if(snd&&Math.random()<0.55&&place(u.x,u.y).g>0.08){play(snd,{x:u.x,y:u.y,delay:Math.random()*600});n++}}}
// a refusal (only right after the player did something): "can't", "not enough", "needs a ...", "No idle units ...", "Choose ..."
const ERR=/\b(can'?t|cannot|isn'?t|aren'?t|not enough|no way|too far|no room|unreachable|belongs to someone|is blocked|already (planned|taken|there|has|in|advanced)|must be|is full|needs? (a|an|at least|to|\d|two|three|four|more))\b|^(no |nothing |choose |select |set a |there is no|you need)/i;
const ALARM=/\b(alarm|on fire|has died|was killed|attacked yours|raid|raiders|under attack|is dying|starving)\b/i;
function onNotice(n){n=String(n||'');if(n===E.notice)return;const first=E.notice==null;E.notice=n;if(first||!n)return;const t=performance.now();
 if(ALARM.test(n)){const st=E.state.get('alarm')||{t:0};if(t-st.t>5000){st.t=t;E.state.set('alarm',st);play('ui.warn')}return}
 if(!/^milestone/i.test(n)&&ERR.test(n)&&t-E.lastInput<2500)play('ui.error')}
// good news in the village log: a birth, a building done, a sale (one chime per kind every few seconds)
const NEWS=[[/\bwas born\b|\bgave birth\b/i,'ui.birth'],[/^Built: |\b(is finished|was finished|is built|was built|completed|stands finished|put up)\b/i,'ui.place'],[/\b(sold|bought)\b.*\bcoins?\b|\bcoins?\b.*\b(paid|earned|received)\b/i,'ui.coins']];
function onLog(t,k){if(!E.ctx||k==='fight')return;
 // someone speaking (players' and units' speech in the old output feed): a soft blip, now and then
 if(k==='chat'){if(/\b(says|whispers|shouts|yells|OOC)\b/.test(String(t||''))){const st=E.state.get('news.chat')||{t:0},n=performance.now();if(n-st.t>2500){st.t=n;E.state.set('news.chat',st);play('ui.chat')}}return}t=String(t||'');for(const [re,snd] of NEWS)if(re.test(t)){const st=E.state.get('news.'+snd)||{t:0},n=performance.now();if(n-st.t>4000){st.t=n;E.state.set('news.'+snd,st);play(snd)}return}}
// specials (Specials.dm's feed): the caster's cry and the cast where it stands, then what lands where it was aimed
const SPECIAL={breath:['dragon','spell.fire','spell.fire',350],web:['spider','throw','web',300],charge:['human','swing.heavy','block',380],slam:['dwarf','slam',null,0],pierce:['elf','bow.shoot','arrow.hit',260],
 leap:['orc','throw','slam',420],firepot:['goblin','throw','spell.fire',450],sweep:['lizardman','swing.heavy','hit.flesh',120],tongue:['frogman','tongue','hit.flesh',260],dart:['kobold','whizz','arrow.hit',220],
 plague:['human','throw','spell.poison',450],shadowstep:['elf','spell.dark','spell.dark',200],acid:['dragon','spell.poison','spell.poison',260],mindblast:['vampire','spell.dark','spell.astral',150]};
function onSpecials(list){if(!Array.isArray(list))return;const fresh=list.filter(f=>f&&!E.seenHits.has('sp'+f.id));for(const f of fresh)E.seenHits.add('sp'+f.id);if(!E.spPrimed){E.spPrimed=true;return}
 for(const f of fresh.slice(0,4)){const S=SPECIAL[f.sp];if(!S)continue;const P=place(f.sx,f.sy);if(S[1])play(S[1],{x:f.sx,y:f.sy});if(S[2])play(S[2],{x:f.tx,y:f.ty,delay:S[3]});if(P.g>0.15)speakWorld(S[0],'m','attack',f.sx,f.sy,P,0)}}
function onModel(m){if(!m)return;E.model=m;persistModel(m);
 if(Array.isArray(m.units)){E.unitAt=new Map();for(const u of m.units)if(u.z===m.z)E.unitAt.set(u.x+','+u.y,u)}
 if(Array.isArray(m.units)&&E.warmed)for(const u of m.units.slice(0,40))warmVoices(u.race,genderOf(u));
 if(typeof m.audio==='string'&&m.audio&&m.audio!==E.serverPrefs){E.serverPrefs=m.audio;if(m.audio!==E.sentPrefs){try{applyPrefs(JSON.parse(m.audio),true)}catch(e){}}}
 if(!E.ctx)return;
 onHits(m.hits);onSpecials(m.specialFx);onNotice(m.notice);workTick(m);
 // level-ups (own units), milestones, raids
 for(const d of Array.isArray(m.xpDrops)?m.xpDrops:[]){if(!d||E.seenHits.has('xp'+d.id))continue;E.seenHits.add('xp'+d.id);if(E.xpPrimed&&d.level){
  // the full fanfare for one you are watching (selected or in view), a soft one for the rest of the village; the one who
  // rose gives a cheer in their own voice
  const u=Array.isArray(m.units)&&m.units.find(x=>x.ref===d.unit),near=u&&(u.selected||place(u.x,u.y).g>0.25);play('ui.levelup',{gain:near||!u?1:0.4});
  if(u&&place(u.x,u.y).g>0.12)setTimeout(()=>speak(u.race,genderOf(u),'cheer',{soft:true}),700)}}E.xpPrimed=true;
 const ms=Array.isArray(m.milestones)?m.milestones.length:0;if(E.ms!=null&&ms>E.ms)play('ui.milestone');E.ms=ms;
 const al=!!m.alert;if(E.alert===false&&al)play('ui.alert');E.alert=al;
 const sel=selectedUnits().map(u=>u.ref).join(',');if(sel!==E.unitsSel){const was=E.unitsSel;E.unitsSel=sel;const t=performance.now();
  if(sel&&(E.pendingSelect&&t-E.pendingSelect<2000||t-E.lastInput<1500)&&t-E.lastSelectVoice>500){E.lastSelectVoice=t;E.pendingSelect=0;const u=selectedUnits()[0];speak(u.race,genderOf(u),'select',{soft:false})}}
 if(m.season)E.season=m.season;
 if(typeof m.speed==='number'){if(E.speed!=null&&(m.speed===0)!==(E.speed===0))play(m.speed===0?'ui.pause':'ui.resume');E.speed=m.speed}}
const ZH={1:0,2:-1,3:1,4:-2};
function on3D(m){if(!m)return;if(typeof m.z==='number'&&m.z!==E.z){if(E.z&&E.ctx)play((ZH[m.z]||0)<(ZH[E.z]||0)?'ui.descend':'ui.ascend');E.z=m.z;roomFor(m.z)}
 doors();if(typeof m.night==='boolean'||m.night!=null){const n=!!m.night;if(E.night!=null&&n!==E.night&&E.ctx){if(!n&&E.z===1)play('bell.village')}E.night=n}
 if(E.ctx)onWork(m.work);else if(Array.isArray(m.work)){E.work=new Map(m.work.map(w=>[w[0]+','+w[1],{blows:w[3],broken:w[6]}]))}}
// doors and gates creak as they open or shut near the camera
function doors(){const v=V();if(!v||!Array.isArray(v.things))return;const D=new Map();for(const t of v.things)if(t.m3==='door'||t.m3==='gate'||t.gate){const k=t.id||t.ref||t.x+','+t.y,o=!!t.open;D.set(k,o);const was=E.doors&&E.doors.get(k);if(was!=null&&was!==o&&E.ctx)play('door',{x:t.x,y:t.y,rate:o?1:0.92})}E.doors=D}
// one room at a time: the other fades out, then is cut off so its convolution stops costing CPU
function roomFor(z){if(!E.ctx)return;const t=now(),cave=z===2||z===4,on=cave?E.verb.cave:E.verb.air,off=cave?E.verb.air:E.verb.cave;
 on.ret.gain.setTargetAtTime(1,t,0.5);off.ret.gain.setTargetAtTime(0,t,0.5);try{E.verbIn.connect(on.send)}catch(e){}
 clearTimeout(E.roomT);E.roomT=setTimeout(()=>{try{E.verbIn.disconnect(off.send)}catch(e){}},3000)}

// --- ambience: beds cross-fade with what is round the camera; birds, owls and drips come and go ---
function surroundings(){const v=V(),T=v&&v.terrain;const out={trees:0,water:0,lava:0,snow:0,sand:0,marsh:0,rock:0,n:0,biome:{}};if(!T||!Array.isArray(T.tiles)||!v)return out;
 const cx=Math.round(v.cx||0),cy=Math.round(v.cy||0),R=9;for(let j=-R;j<=R;j+=2)for(let i=-R;i<=R;i+=2){const x=cx+i-T.x0,y=cy+j-T.y0;if(x<0||y<0||x>=T.w||y>=T.h)continue;const c=T.tiles[y*T.w+x];const K=c?T.kinds[c-1]:null;if(!K)continue;out.n++;
  const s=String(K.state||'')+' '+String(K.tex||'');if(K.kind==='tree')out.trees++;else if(K.kind==='water')out.water++;else if(K.kind==='lava')out.lava++;else if(K.kind==='wall'||K.kind==='block')out.rock++;
  if(/snow|ice/.test(s))out.snow++;else if(/desert|sand/.test(s))out.sand++;else if(/marsh|swamp|bog/.test(s))out.marsh++;if(K.biome)out.biome[K.biome]=(out.biome[K.biome]||0)+1}return out}
function ambTargets(){const z=E.z||1,S=surroundings(),n=Math.max(1,S.n),night=!!E.night,season=String(E.season||'').toLowerCase(),f=k=>clamp(k/n*2.2,0,1),B=k=>clamp((S.biome[k]||0)/n*2,0,1);const T={};
 if(z===1&&E.weather){const W=E.weather;T['bed.rain']=W==='rain'?0.8:W==='storm'?1:0;if(W==='snow')T['bed.wind.cold']=0.9}
 if(z===2){T['bed.cave']=1;if(B('mushroom'))T['bed.insects']=0.15}else if(z===4){T['bed.cave']=0.6;T['bed.lava']=Math.max(0.5,f(S.lava));}else if(z===3){T['bed.sky']=1}
 else{const cold=season==='winter'||f(S.snow)>0.3||B('tundra')>0.3;T[cold?'bed.wind.cold':'bed.wind']=0.55+0.3*f(S.rock)+(cold?0.2:0);T['bed.leaves']=f(S.trees)*(season==='winter'?0.3:season==='autumn'?1:0.8);T['bed.water']=f(S.water);
  if(B('jungle')>0.2)T['bed.jungle']=B('jungle')*(night?0.6:1);if(B('ashlands'))T['bed.lava']=B('ashlands')*0.6;
  if(night)T['bed.crickets']=season==='winter'?0:0.7*(1-f(S.snow));else if(season==='summer'||season==='spring')T['bed.insects']=(season==='summer'?0.45:0.2)*(1-f(S.sand)*0.5)*(1-f(S.snow))}
 // your own people about: a village's murmur by day, quieter at night
 if(z===1){let near=0;const v0=V();if(v0){for(const u of E.unitAt.values())if(Math.hypot(u.x-(v0.cx||0),u.y-(v0.cy||0))<12)near++;if(Array.isArray(v0.things)&&v0.things.some(o=>o.tavern&&Math.hypot(o.x-(v0.cx||0),o.y-(v0.cy||0))<9))near+=6}   /* a tavern is busy whoever is about */if(near>=5)T['bed.village']=Math.min(1,(near-4)/8)*(night?0.3:0.8)}
 // campfires and burning things nearby
 const v=V();if(v&&Array.isArray(v.things)){let best=0;for(const t of v.things){if(t.kind==='effect'&&(t.flame||/fire/i.test(t.name||''))||t.burning){const P=place(t.x,t.y);if(P.g>best)best=P.g}}if(best>0.1)T['bed.fire']=Math.min(1,best*1.3)}
 return {T,S,z,night,season}}
function ambTick(){if(!E.ctx||!FEATURES.amb)return;setTimeout(ambTick,2500);ambWork()}
const ambWork=timed('ambience',function(){if(E.ctx.state!=='running')return;try{const {T,S,z,night,season}=ambTargets(),t=now();
  for(const name of new Set([...Object.keys(T),...E.amb.layers.keys()])){const want=T[name]||0;let L=E.amb.layers.get(name);
   if(!L&&want>0.02){const b=getBuf(name+'#0','snd',[name,0]);if(!b)continue;const src=E.ctx.createBufferSource();src.buffer=b;src.loop=true;src.playbackRate.value=rr(Math.random,0.96,1.04);const g=E.ctx.createGain();g.gain.value=0;src.connect(g);g.connect(E.bus.amb);src.start(t,Math.random()*b.duration);L={src,g,want:0};E.amb.layers.set(name,L)}
   if(!L)continue;L.want=want;L.g.gain.setTargetAtTime(want*SND[name].gain*rr(Math.random,0.78,1.08),t,2.2);   /* a slow random drift hides the loop */if(want<=0.02&&!L.stopAt)L.stopAt=t+9;else if(want>0.02)L.stopAt=0;
   if(L.stopAt&&t>L.stopAt){try{L.src.stop()}catch(e){}L.g.disconnect();E.amb.layers.delete(name)}}
  // spot sounds round the camera
  if(performance.now()>E.amb.next){E.amb.next=performance.now()+rr(Math.random,2500,7000);const v=V();const at=()=>({x:(v&&v.cx||0)+rr(Math.random,-14,14),y:(v&&v.cy||0)+rr(Math.random,-14,14)});const n=Math.max(1,S.n),trees=S.trees/n;let c=[];
   if(z===1&&E.weather==='storm'&&Math.random()<0.5)c=[['thunder',1]];else if(z===2||z===4)c=[['drip',3],['pebbles',1],['cave.groan',z===4?0.6:0.3]].concat(z===4?[['bubble',2]]:[]);
   else if(z===1){if(night)c=[['owl',1.2],['wolf',0.25],['frog',S.marsh+S.water?1.5:0.2]];else c=[['bird.song',(0.6+trees*5)*(season==='spring'?1.6:season==='autumn'?0.7:1)],['bird.crow',season==='autumn'?1.2:0.5],['hawk',S.sand+S.rock?0.6:0.1],['frog',S.marsh?1.2:0]];if(String(season)==='winter'&&!night)c=[['bird.crow',1]]}
   const tot=c.reduce((s,x)=>s+x[1],0);let pr=Math.random()*tot;for(const [nm,w] of c){pr-=w;if(pr<=0){play(nm,Object.assign(at(),{gain:0.9}));break}}}}catch(e){log(e)}});

// --- music: a quiet bed that comes and goes. Lute and pad by day, harp and drone by night, a low drone underground ---
const MODES={day:{bpm:68,root:62,scale:[0,2,3,5,7,9,10],progs:[[[0,3,7],[-2,2,5],[0,3,7],[5,9,12]],[[0,3,7],[3,7,10],[-2,2,5],[0,3,7]],[[0,3,7],[5,9,12],[3,7,10],[-2,2,5]]]},
 night:{bpm:60,root:57,scale:[0,2,3,5,7,8,10],progs:[[[0,3,7],[-4,0,3],[-2,2,5],[0,3,7]],[[0,3,7],[5,8,12],[-4,0,3],[-5,-1,2]]]},
 deep:{bpm:56,root:50,scale:[0,1,3,5,7,8,10],progs:[[[0,3,7],[1,5,8],[0,3,7],[-2,1,5]],[[0,3,7],[-4,0,3],[1,5,8],[0,3,7]]]}};
const DRUMS=[['drum.taiko',1],null,['drum.frame',0.5],['drum.frame',0.35],['drum.taiko',0.8],['drum.frame',0.5],null,['drum.frame',0.6],['drum.taiko',1],null,['drum.frame',0.5],['drum.taiko',0.6],['drum.taiko',0.9],['drum.frame',0.45],['drum.frame',0.55],['drum.frame',0.7]];
function drums(t){const B=E.battle;if(!B)return;const step=60/96/2;while(B.next<t+0.4){if(B.next>B.until){E.battle=null;return}const fade=Math.min(1,(B.until-B.next)/3),D=DRUMS[B.step%DRUMS.length];if(D)play(D[0],{gain:D[1]*fade,delay:Math.max(0,(B.next-now())*1000)});B.next+=step;B.step++}}
function musTick(){if(!E.ctx||!FEATURES.music)return;setTimeout(musTick,250);musWork()}
const musWork=timed('music',function(){if(E.ctx.state!=='running'||E.prefs.mus<=0||E.prefs.master<=0)return;try{const t=now(),M2=E.mus;drums(t);
  if(!M2.phrase){if(!M2.next)M2.next=t+rr(Math.random,6,14);if(t<M2.next)return;const mood=E.z===2||E.z===4?'deep':E.night?'night':'day';const R0=rng(Math.floor(Math.random()*1e9));M2.phrase={mood,bar:0,t0:t+1.5,bars:8,beat:60/MODES[mood].bpm,prog:pick(R0,MODES[mood].progs),style:mood==='deep'?'sparse':pick(R0,mood==='day'?['arp','arp','air','sparse']:['arp','sparse','sparse']),r:R0};musFetch(M2.phrase)}
  const P=M2.phrase,barLen=P.beat*4;while(P.bar<P.bars&&P.t0+P.bar*barLen<t+1.0){schedBar(P,P.t0+P.bar*barLen,barLen);P.bar++}
  if(P.bar>=P.bars&&t>P.t0+P.bars*barLen){M2.phrase=null;M2.next=t+rr(Math.random,25,70)}}catch(e){log(e)}});
function note(kind,args,at,g,pan){const b=getBuf(kind+JSON.stringify(args),'inst',[kind,args]);if(!b)return;const src=E.ctx.createBufferSource();src.buffer=b;const gn=E.ctx.createGain();gn.gain.value=g;src.connect(gn);let n=gn;if(pan&&E.ctx.createStereoPanner){const p=E.ctx.createStereoPanner();p.pan.value=pan;gn.connect(p);n=p}n.connect(E.bus.mus);const s=E.ctx.createGain();s.gain.value=0.35;n.connect(s);s.connect(E.verbIn);src.start(at);src.onended=()=>{try{gn.disconnect()}catch(e){}}}
// everything a phrase may play, asked of the worker before its first bar (tempos are fixed per mood, so these repeat)
const FLUTE_BEATS=[0.5,1,1.5,2];
function musFetch(P){const Md=MODES[P.mood],root=Md.root,len=P.beat*4,inst=P.mood==='day'?'lute':'harp',ask=(k,a)=>getBuf(k+JSON.stringify(a),'inst',[k,a],null,'front');
 for(const ch of P.prog){ask('pad',[ch.map(x=>root+x-12),len*2+1.5]);for(const x of ch){ask(inst,[root+x]);ask(inst,[root+x+12]);ask('harp',[root+x-12])}ask(inst,[root+ch[0]+24])}
 if(P.mood!=='day')ask('drone',[root-24,len*4+2]);else for(const x of Md.scale)for(const b of FLUTE_BEATS)ask('flute',[root+12+x,Math.round(P.beat*b*100)/100])}
// a flute line that walks the mode in steps and leaps back, two bars long, ending on a chord tone
function airLine(P,at,span,amp){const Md=MODES[P.mood],r=P.r,sc=Md.scale.map(x=>Md.root+12+x);let deg=Math.floor(r()*3)+2,tt=at+P.beat*0.5;
 while(tt<at+span-P.beat){deg=clamp(deg+pick(r,[-2,-1,-1,1,1,2,-3,3]),0,sc.length-1);const d=P.beat*pick(r,[0.5,1,1,1.5,2]);if(tt+d>at+span)break;note('flute',[sc[deg],Math.round(d*100)/100],tt,0.24*amp,rr(r,-0.15,0.15));tt+=d}}
function schedBar(P,at,len){const Md=MODES[P.mood],r=P.r,ch=P.prog[P.bar%P.prog.length],root=Md.root,first=P.bar===0,last=P.bar===P.bars-1;
 const fadeIn=Math.min(1,(P.bar+1)/2),fadeOut=last?0.7:1,amp=fadeIn*fadeOut;
 if(P.bar%2===0)note('pad',[ch.map(x=>root+x-12),len*2+1.5],at,0.5*amp,0);
 if(P.mood!=='day'&&P.bar%4===0)note('drone',[root-24,len*4+2],at,0.55*amp,0);
 const beat=P.beat,inst=P.mood==='day'?'lute':'harp',tones=ch.map(x=>root+x);
 if(P.mood==='deep'){if(r()<0.6)note('harp',[tones[0]-12],at+beat*rr(r,0,2),0.35*amp,rr(r,-0.3,0.3));return}
 // three ways to play a phrase: arpeggios, a few notes left hanging, or a flute air over the pad alone
 if(P.style==='sparse'){for(let k=0;k<2;k++)if(r()<0.75)note(inst,[pick(r,tones)+(r()<0.3?12:0)],at+beat*(k*2+rr(r,0,1.2)),0.32*amp,rr(r,-0.35,0.35));return}
 if(P.style==='air'){if(P.bar%2===0)airLine(P,at,len*2,amp);if(r()<0.5)note(inst,[tones[0]],at,0.3*amp,0);return}
 // an arpeggio pattern with rests
 const pat=pick(r,[[0,1,2,1,0,1,2,1],[0,2,1,2,0,2,1,2],[0,1,2,3,2,1,0,null],[0,null,2,1,null,2,1,0]]);
 for(let k=0;k<8;k++){const i=pat[k];if(i==null||r()<0.18)continue;const m=i===3?tones[0]+12:tones[i];note(inst,[m+(r()<0.15?12:0)],at+k*beat/2+rr(r,0,0.015),(k%2?0.28:0.36)*amp,rr(r,-0.35,0.35))}
 // now and then a flute line over it
 if(P.mood==='day'&&P.bar>=2&&P.bar<P.bars-1&&r()<0.45){const sc=Md.scale.map(x=>root+12+x);let deg=Math.floor(r()*4)+2;let tt=at+beat*rr(r,0,1);for(let k=0;k<3+Math.floor(r()*3);k++){deg=clamp(deg+pick(r,[-2,-1,-1,1,1,2]),0,sc.length-1);const d=beat*pick(r,[0.5,1,1,1.5,2]);if(tt+d>at+len*1.5)break;note('flute',[sc[deg],Math.round(d*100)/100],tt,0.22*amp,rr(r,-0.2,0.2));tt+=d}}}

// --- war drums: our own patterns on the drum recordings. They come in when a fight is near the camera (E.battle, from the
// hits feed), on a timpani roll into a first big hit; they grow with the fight (hits in the last 5 s: 1 skirmish, 2 battle,
// 3 a great battle), turn every fourth bar into a fill, and end on a last hit and a gong a few seconds after it. Each fight
// gets one of three themes. A bar is written out at once (wdBar), so checks can render the very same drums offline. ---
// patterns: 16 steps a bar; . rest, p m f F softer to harder; for the timpani, 0-3 is which drum (low to high), struck f
const WD_THEMES=[
 {name:'march',bpm:96,layers:[['wd.boom',1,'F.......f.......'],['wd.boom',2,'............m...'],['wd.boom',3,'...m.......m.m..'],['wd.soft',1,'....p.......p...'],
  ['wd.hand',2,'..m.f...m.m.f.m.'],['wd.hand',3,'m..............m'],['wd.low',2,'........F.......'],['wd.low',3,'F...............'],['wd.timp',2,'............1...'],['wd.timp',3,'..........2.....']]},
 {name:'charge',bpm:108,layers:[['wd.boom',1,'F...f...F...f...'],['wd.boom',2,'..............f.'],['wd.boom',3,'..f.......f.....'],['wd.hand',1,'..m...m...m...m.'],
  ['wd.hand',2,'m...m..mm...m..m'],['wd.hand',3,'.m.m.m...m.m.m..'],['wd.low',2,'F...............'],['wd.low',3,'........F.......'],['wd.timp',2,'........2.......'],['wd.timp',3,'....1.......3...']]},
 {name:'deep',bpm:84,layers:[['wd.boom',1,'F.......F.......'],['wd.boom',2,'..............m.'],['wd.boom',3,'......m.........'],['wd.timp',1,'............0...'],
  ['wd.timp',2,'....0...........'],['wd.timp',3,'0.............1.'],['wd.soft',1,'....p.......p...'],['wd.low',2,'F...............'],['wd.low',3,'........F.......'],
  ['wd.hand',2,'....p.......p...'],['wd.hand',3,'..p.....p.m...p.']]}];
const WD_VEL={p:0.4,m:0.62,f:0.82,F:1};
const WD_PAN={'wd.boom':0,'wd.soft':0.12,'wd.low':0,'wd.hand':0.28,'wd.timp':0.2,'wd.roll':-0.1,'wd.crash':0.18,'wd.gong':-0.12};
// one bar's hits: [time, sound, take, gain, pan]; kind '' a bar, 'fill' the fourth bar of a phrase, 'end' the last hit
function wdRoll(){const b=E.buffers.get('wd.roll#0');return b?b.duration:2.5}
function wdBar(th,level,t0,kind,r){const T=WD_THEMES[th],st=60/T.bpm/4,out=[],hum=k=>k%4?(r()-0.5)*0.016:(r()-0.5)*0.006,vel=v=>v*(0.92+r()*0.16);
 const hit=(k,name,g,take,pan)=>out.push([t0+k*st+hum(k),name,take==null?-1:take,vel(g),pan==null?WD_PAN[name]*(k%2?1:-1):pan]);
 if(kind==='end'){hit(0,'wd.boom',1);hit(0,'wd.low',1);hit(0,'wd.gong',0.9,null,WD_PAN['wd.gong']);if(level>=2)hit(0,'wd.crash',0.8,0,WD_PAN['wd.crash']);return out}
 const fill=kind==='fill'&&level>=2;
 for(const [name,lv,pat] of T.layers){if(lv>level)continue;for(let k=0;k<16;k++){const c=pat[k];if(c==='.')continue;if(fill&&k>=8&&name!=='wd.low')continue;
  if(name==='wd.timp'){const d=+c;hit(k,name,WD_VEL.f,d,(d-1.5)*0.2)}else hit(k,name,WD_VEL[c]*(k===0?1.05:1))}}
 if(fill){for(let k=8;k<16;k++)hit(k,'wd.hand',0.5+0.06*(k-8));out.push([t0+16*st-wdRoll(),'wd.roll',0,0.75,WD_PAN['wd.roll']]);if(level>=3)for(const k of [12,14])hit(k,'wd.timp',0.85,k===12?2:3,0)}
 return out}
function wdLevel(){const t=performance.now(),n=(E.fightHits||[]).filter(x=>t-x<5000).length;return n>=20?3:n>=10?2:1}
// the battle: when the drums came in, which theme, the bar playing, its level
let WDS=null;
function wdTick(){if(!E.ctx)return;setTimeout(wdTick,200);wdWork()}
const wdWork=timed('drums',function(){if(E.ctx.state!=='running')return;try{const t=now(),fight=!!(E.battle&&E.battle.until>t);bedLevel(fight);
  if(!WDS){if(!fight||!REC.has('wd.boom'))return;
   const r=rng(Math.floor(Math.random()*1e9)),th=E.wdLast&&t-E.wdLast.at<30?E.wdLast.th:Math.floor(r()*WD_THEMES.length),bar=60/WD_THEMES[th].bpm*4;
   WDS={th,r,next:t+0.05+wdRoll(),bar,n:0,level:wdLevel()};wdPlay([[t+0.05,'wd.roll',0,0.8,WD_PAN['wd.roll']]]);   /* a roll swells into the first downbeat */
   wdPlay([[WDS.next,'wd.crash',0,0.7,WD_PAN['wd.crash']]])}
  while(WDS&&WDS.next<t+0.6){const S=WDS;if(!fight){wdPlay(wdBar(S.th,S.level,S.next,'end',S.r));E.wdLast={th:S.th,at:t};WDS=null;break}
   const lv=wdLevel();if(lv>S.level||S.n%4===0)S.level=lv;   /* louder at once, quieter only at a phrase */
   wdPlay(wdBar(S.th,S.level,S.next,S.n%4===3?'fill':'',S.r));S.n++;S.next+=S.bar}}catch(e){log(e)}});
function wdPlay(list){const t=now();for(const [at,name,take,g,pan] of list)play(name,{delay:Math.max(0,(at-t)*1000),gain:g,pan,variant:take>=0?take:undefined,wet:0.38})}
// the ambience bed: the user's forest track, looped, softer underground and well down under the drums (-10 dB once a
// battle begins, within a second or two; back slowly after it, the user asked, 2026-10-23)
function bedLevel(fight){const B=E.bed;if(!B||!B.g)return;const want=(E.z===2||E.z===4?0.55:1)*(fight?0.3:1);if(Math.abs(want-(B.want||0))>0.01){const down=want<(B.want||0);B.want=want;B.g.gain.setTargetAtTime(want,now(),down?0.5:2.5)}}
function bedStart(){if(E.bed)return;const b=E.buffers.get(BED);if(!b)return;const ctx=E.ctx,src=ctx.createBufferSource(),g=ctx.createGain();src.buffer=b;src.loop=true;g.gain.value=0;
 src.connect(g);g.connect(E.bus.amb);src.start(now()+0.05);E.bed={src,g,want:0};bedLevel(!!(E.battle&&E.battle.until>now()))}

// --- the Sound section in Settings ---
function syncUI(){const box=document.getElementById('rmSound');if(!box)return;for(const [k] of CATS){const i=box.querySelector('[data-k="'+k+'"]');if(!i)continue;if(+i.value!==E.prefs[k])i.value=E.prefs[k];const o=i.parentNode.querySelector('output');if(o&&o.textContent!==String(E.prefs[k]))o.textContent=E.prefs[k]}const bg=box.querySelector('[data-k="bg"]');if(bg)bg.checked=!!E.prefs.bg}
function settingsUI(){const S=document.getElementById('settings');if(!S||document.getElementById('rmSound'))return;
 const st=document.createElement('style');st.textContent='#rmSound{border-top:1px solid var(--line,#3b4e42);margin-top:8px;padding-top:6px}#rmSound h4{margin:2px 0 4px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--gold,#e0bb73)}#rmSound .rmvol{display:grid;grid-template-columns:76px 1fr 30px;align-items:center;gap:8px;margin:3px 0;font-size:13px}#rmSound .rmvol input{width:100%;accent-color:var(--gold,#e0bb73);min-height:0;margin:0}#rmSound output{text-align:right;color:var(--muted,#adbcab);font-variant-numeric:tabular-nums}#rmSound .rmbg{display:flex;gap:7px;align-items:center;margin-top:5px;font-size:13px}';document.head.append(st);
 const box=document.createElement('div');box.id='rmSound';box.setAttribute('role','group');box.setAttribute('aria-label','Sound');box.innerHTML='<h4>Sound</h4>'+CATS.filter(([k])=>k==='master'||k==='amb'||k==='wd'||FEATURES[k==='fx'?'fx':k==='ui'?'ui':k==='mus'?'music':'none']).map(([k,l])=>'<label class="rmvol"><span>'+l+'</span><input type="range" min="0" max="100" step="1" data-k="'+k+'" aria-label="'+l+' volume"><output>0</output></label>').join('')+'<label class="rmbg"><input type="checkbox" data-k="bg"> Mute when the game is in the background</label>';
 const close=document.getElementById('setClose');S.insertBefore(box,close&&close.parentNode===S?close.previousElementSibling&&close.previousElementSibling.classList.contains('hint')?close.previousElementSibling:close:null);
 box.addEventListener('input',e=>{const k=e.target.dataset.k;if(!k)return;if(k==='bg'){E.prefs.bg=e.target.checked?1:0;onVisibility()}else{if(Math.floor(+e.target.value/10)!==Math.floor(E.prefs[k]/10))play('ui.hover',{gain:0.8});E.prefs[k]=+e.target.value;const o=e.target.parentNode.querySelector('output');if(o)o.textContent=e.target.value}setGains();savePrefs()});
 box.addEventListener('change',e=>{const k=e.target.dataset.k;if(k&&k!=='bg'&&E.ctx){unlock();play(k==='vo'?'cmd.move':k==='wd'?'wd.boom':k==='mus'?'ui.save':k==='amb'?'bird.song':k==='fx'?'chop':'ui.click');if(k==='vo'){const u=selectedUnits()[0];speak(u&&u.race||'human',genderOf(u),'select')}}});
 syncUI()}

// --- the HUD's other settings outlive the app: its web view forgets page storage on quit, so these keys are mirrored to
// the player's profile (Audio.dm, rm=hudprefs) and put back from the first HUD model of the next start ---
const PERSIST=['rmSettings','dm3dIso','rm-edgescroll','rm-rclick','rm-scrollspeed','rm-rosterfold','rm-hfmore','rm-hftab','rm-gftab'];
function lsGet(k){try{return localStorage.getItem(k)}catch(e){return null}}
function persistSnap(){const o={};for(const k of PERSIST){const v=lsGet(k);if(v!=null)o[k]=v}return JSON.stringify(o)}
function persistRestore(saved){let S={};try{S=JSON.parse(saved||'{}')||{}}catch(e){}const changed=[];
 for(const k of PERSIST)if(typeof S[k]==='string'&&lsGet(k)!==S[k]){try{localStorage.setItem(k,S[k]);changed.push(k)}catch(e){}}
 if(!changed.length)return changed;
 // re-apply through each owner's own code
 try{if(changed.includes('rmSettings')&&typeof applySettings==='function')applySettings()}catch(e){log(e)}
 try{if(changed.includes('dm3dIso')&&typeof v3iso==='function')v3iso(lsGet('dm3dIso')!=='0')}catch(e){log(e)}
 try{if(typeof RF!=='undefined'&&RF){if(typeof rfEdgeOn==='function'){RF.edgeOk=rfEdgeOn();const c=document.getElementById('setEdge');if(c)c.checked=RF.edgeOk}if(typeof rfRightOrders==='function'){RF.rclick=rfRightOrders();const s=document.getElementById('setRclick');if(s)s.value=RF.rclick?'orders':'menu'}}}catch(e){log(e)}
 try{window.dispatchEvent(new CustomEvent('rm-prefs-restored',{detail:{keys:changed}}))}catch(e){}
 return changed}
function persistModel(m){if(typeof m.hudPrefs!=='string')return;E.persistServer=m.hudPrefs;   /* what the server holds, every model */
 if(E.persistDone)return;E.persistDone=true;E.persistRestored=persistRestore(m.hudPrefs);E.persistSent=m.hudPrefs;   /* the server's copy is the baseline: anything set here before it arrived is sent too */
 setInterval(()=>{persistTick(false);audioTick()},3000)}
// Sent until the server holds it (its copy comes back in the HUD model as hudPrefs): a send lost on the way (another
// command in the same moment, the app closing) is sent again, not taken as saved (hud-craft, 10-25: the user's Health
// choice never reached their profile)
function persistTick(now){if(!E.persistDone)return;const s=persistSnap();if(s==='{}'||s===E.persistServer)return;
 const t=Date.now();if(!now&&s===E.persistSent&&t-(E.persistAt||0)<2500)return;   /* again on the next 3 s check */
 E.persistSent=s;E.persistAt=t;try{if(typeof send==='function')send('hudprefs',s)}catch(e){log(e)}}
// the Sound settings the same way: sent (savePrefs) and sent again until the server's copy (HUD model "audio") is them
function audioTick(){const s=JSON.stringify(E.prefs);if(!E.sentPrefs||s!==E.sentPrefs||s===E.serverPrefs)return;
 const t=Date.now();if(t-(E.audioAt||0)<2500)return;E.audioAt=t;try{if(typeof send==='function')send('audioprefs',s)}catch(e){log(e)}}
// a setting just changed (the page's saveSettings): to the profile at once, not on the next 3 s check
window.rmPersistNow=()=>{clearTimeout(E.persistNowT);E.persistNowT=setTimeout(()=>persistTick(true),300)};

// --- background: fade out and rest the audio thread while the window is hidden ---
// the window hidden, minimized or covered (page visibility), or, in the app, another app in front (the bridge calls
// window.dmAppActive, WebKitBridge.swift)
// (muting is the master gain; the audio thread is only suspended to save CPU once the page has had real input: WebKit won't
// resume a context without a click before that, and the world should be heard when the window comes up)
function onVisibility(){E.hidden=document.visibilityState==='hidden'||!!E.appInactive;setGains();if(E.hidden)try{persistTick(true)}catch(e){}   /* the window going away (the app may be closing): settings to the profile now */
 if(!E.ctx)return;if(E.hidden&&E.prefs.bg){setTimeout(()=>{if(E.hidden&&E.prefs.bg&&E.gestured&&E.ctx.state==='running')E.ctx.suspend().catch(()=>{})},400)}else if(E.ctx.state==='suspended')E.ctx.resume().catch(()=>{})}
document.addEventListener('visibilitychange',onVisibility);
window.dmAppActive=a=>{E.appInactive=!a;onVisibility()};
// and ask once where things stand (an app started and left in the background while it loads stays quiet)
try{window.webkit.messageHandlers.dmOverlay.postMessage({appActive:1})}catch(e){}

// --- wiring into the page ---
// what audio itself costs the page's main thread (its share of the wrapped calls and its own timers), for checks
function cost(k,ms){const c=E.cost||(E.cost={});const s=c[k]||(c[k]={n:0,ms:0,max:0});s.n++;s.ms+=ms;if(ms>s.max)s.max=ms}
function timed(k,f){return function(){const t0=performance.now();try{return f.apply(this,arguments)}finally{cost(k,performance.now()-t0)}}}
function wrap(name,after,before){const f=window[name];if(typeof f!=='function'||f.__rmAudio)return false;const w=function(){const t0=performance.now();if(before)try{before.apply(this,arguments)}catch(e){log(e)}const t1=performance.now(),r=f.apply(this,arguments),t2=performance.now();if(after)try{after.apply(this,arguments)}catch(e){log(e)}cost(name,t1-t0+performance.now()-t2);return r};w.__rmAudio=true;window[name]=w;(E.wired||(E.wired=[])).push(name);return true}
// the world first comes into view (the loading cover lifts): a soft swell, once
function watchArrival(){const c=document.getElementById('bootcover');if(!c||!FEATURES.ui)return;const go=(n)=>{n=n||0;if(E.arrived)return;if(E.ctx&&E.ctx.state==='running'&&getBuf('ui.arrive#0','snd',['ui.arrive',0])){E.arrived=true;play('ui.arrive');if(!E.mus.phrase)E.mus.next=Math.max(E.mus.next||0,now()+7);return}if(n<60)setTimeout(()=>go(n+1),250)};   /* waits (up to 15 s) for the audio and the sound */
 if(c.classList.contains('off'))return;new MutationObserver((l,o)=>{if(c.classList.contains('off')||!c.isConnected){o.disconnect();go()}}).observe(c,{attributes:true,attributeFilter:['class']})}
function wire(){wrap('updateHUD',()=>onModel(M()));wrap('update3D',raw=>{const v=V();if(v&&v.gl&&typeof v.z==='number')on3D({z:v.z,night:v.night,work:v.work?[...v.work.values()].map(e=>[e.x,e.y,e.dmg,e.blows,e.dx,e.dy,e.broken]):[]});   // what update3D just stored: no second parse of a big payload
  else try{on3D(typeof raw==='string'?JSON.parse(raw):raw)}catch(e){}});wrap('send',null,(a,v)=>onSend(a,v));wrap('logPush',null,(t,k)=>onLog(t,k));settingsUI();watchPanels();watchArrival();loadLocal();onVisibility();setTimeout(prewarm,1500);setTimeout(tryEarly,2000)}
// the page's main script has run by now (this file is inserted after it), so wire at once: don't wait for DOMContentLoaded,
// which a page whose load the ready request interrupts (byond://) may never reach in the app's WebKit
wire();
// later rows in Settings (rts-feel's) go in before its last hint: keep Sound after them
function placeSound(){const S=document.getElementById('settings'),box=document.getElementById('rmSound');if(!S||!box)return;const hints=S.querySelectorAll('p.hint'),h=hints[hints.length-1];if(h&&h.parentNode===S&&box.nextElementSibling!==h)S.insertBefore(box,h)}
setTimeout(placeSound,400);document.addEventListener('DOMContentLoaded',placeSound);

// the public hook
// names other code uses for moments rather than sounds (rts-feel): a select click, control groups, a click that orders nothing
const ALIAS={select:()=>{play('ui.pick');E.pendingSelect=performance.now()},'group-recall':()=>{play('ui.pick');E.pendingSelect=performance.now()},'group-set':()=>play('ui.groupset'),deny:()=>play('ui.error',{gain:0.7})};
const api=function(name,o){if(ALIAS[name])return ALIAS[name](o);if(String(name).startsWith('vo.')){const u=selectedUnits()[0];return speak(o&&o.race||u&&u.race,o&&o.gender||genderOf(u),String(name).slice(3),o)}return play(name,o)};
api.order=order;api.weather=w=>{E.weather=/^(rain|storm|snow)$/.test(String(w))?String(w):null};   /* for a weather visual: rain, storm, snow or null */
api.at=(name,x,y,o)=>name==='impact'?onImpact(x,y,o):name==='fall'?onFall(x,y):name==='built'?play(/wood|bridge|floor|door|bed|table|chair/i.test(String(o&&o.kind||''))?'built.wood':'built',{x,y}):play(name,Object.assign({x,y},o||{}));api.speak=speak;api.prefs=()=>Object.assign({},E.prefs);api.set=p=>{applyPrefs(p);savePrefs()};
api.stats=()=>{let peak=0;const pending=E.wait.size,worker=W?'yes':W===false?'no':'not yet';if(E.meter){const d=new Float32Array(E.meter.fftSize);E.meter.getFloatTimeDomainData(d);for(const x of d)peak=Math.max(peak,Math.abs(x))}return {state:E.ctx?E.ctx.state:'none',played:E.played,skipped:E.skipped,errors:E.errors,live:E.live.length,buffers:E.buffers.size,amb:[...E.amb.layers.keys()],music:!!E.mus.phrase,bed:!!(E.bed&&E.bed.src),drums:WDS?{theme:WD_THEMES[WDS.th].name,level:WDS.level,bar:WDS.n}:null,rec:{sounds:REC.size,files:E.recLoad?E.recLoad.n:0,loaded:E.recLoad?E.recLoad.ok:0,failed:E.recLoad?E.recLoad.fail:0},pending,worker,cost:Object.fromEntries(Object.entries(E.cost||{}).map(([k,s])=>[k,{n:s.n,avg:Math.round(s.ms/s.n*1000)/1000,max:Math.round(s.max*100)/100}])),peak:Math.round(peak*1000)/1000,prefs:Object.assign({},E.prefs)}};
api.unlock=unlock;api.hush=hush;
// for checks: ask for buffers ({name,v} | {voice:[race,g,kind,v]} | {inst:[kind,args]}) and wait for them
const evKey=ev=>ev.file?ev.file:ev.voice?vkey(...ev.voice):ev.inst?ev.inst[0]+JSON.stringify(ev.inst[1]):ev.name+'#'+(ev.v||0);
api.fetch=list=>Promise.all(list.map(ev=>new Promise(res=>{const k=evKey(ev),kind=ev.voice?'voice':ev.inst?'inst':'snd',args=ev.voice||ev.inst||[ev.name,ev.v||0];if(E.buffers.has(k))return res(true);
 if(ev.file||ev.name&&SND[ev.name]&&SND[ev.name].rec){const t0=performance.now(),w=()=>E.buffers.has(k)?res(true):performance.now()-t0>20000?res(false):setTimeout(w,50);return w()}getBuf(k,kind,args,()=>res(true));setTimeout(()=>res(E.buffers.has(k)),20000)})));
// the engine's own chain (rooms, compressor, limiter) rendered offline at the current volumes: events {t, name|voice|inst, gain, pan, loop}
api.offline=(secs,events)=>{const OC=window.OfflineAudioContext||window.webkitOfflineAudioContext,ctx=new OC(2,Math.ceil(secs*44100),44100),G=graph(ctx,{}),missing=[];
 for(const [k] of CATS)(k==='master'?G.master:G.bus[k]).gain.value=curve(E.prefs[k]);
 G.wdOut.gain.value=curve(E.prefs.master)*WD_MAKE;
 for(const ev of events){const key=evKey(ev),b0=E.buffers.get(key);if(!b0){missing.push(key);continue}let b=b0;if(b0.ch){b=ctx.createBuffer(b0.ch.length,b0.ch[0].length,b0.sr);b0.ch.forEach((a,c)=>b.getChannelData(c).set(a))}
  const cat=ev.file?ev.cat||'amb':ev.voice?'vo':ev.inst?'mus':SND[ev.name].cat,g=(ev.file?1:ev.voice?0.9:ev.inst?1:SND[ev.name].gain)*(ev.gain==null?1:ev.gain),src=ctx.createBufferSource();src.buffer=b;src.loop=!!ev.loop;
  const gn=ctx.createGain();gn.gain.value=g;src.connect(gn);let n=gn;if(ev.pan){const p=ctx.createStereoPanner();p.pan.value=ev.pan;gn.connect(p);n=p}n.connect(G.bus[cat]);
  const wet=ev.wet!=null?ev.wet:cat==='fx'?0.5:cat==='vo'?0.3:cat==='amb'?0.4:0.12;if(wet){const s=ctx.createGain();s.gain.value=wet;n.connect(s);s.connect(G.verbIn)}src.start(ev.t);if(ev.loop)src.stop(secs)}
 return ctx.startRendering().then(B=>({sr:B.sampleRate,ch:[B.getChannelData(0),B.getChannelData(1)],missing}))};
const recDone=()=>!E.recLoad||E.recLoad.ok+E.recLoad.fail>=E.recLoad.n;
api.ready=()=>new Promise(res=>{const t0=performance.now(),f=()=>{if((E.warmed&&!E.wait.size&&recDone())||performance.now()-t0>20000)res(!E.wait.size&&recDone());else setTimeout(f,100)};prewarm();f()});
// a battle's drums written out (theme 0-2; levels: one per bar, 0 = the end), as offline events {t,name,v,gain,pan,wet}
api.drumScore=(th,levels,t0)=>{const r=rng(7),S=60/WD_THEMES[th].bpm*4,ev=[];let t=(t0||0)+0.05+wdRoll();const add=l=>{for(const [at,name,take,g,pan] of l)ev.push({t:at,name,v:take>=0?take:Math.floor(r()*SND[name].vars),gain:g,pan,wet:0.38})};
 add([[(t0||0)+0.05,'wd.roll',0,0.8,WD_PAN['wd.roll']],[t,'wd.crash',0,0.7,WD_PAN['wd.crash']]]);levels.forEach((lv,i)=>{add(wdBar(th,lv||1,t,lv?(i%4===3?'fill':''):'end',r));t+=S});return ev};
api.features=FEATURES;api._E=E;api.synth=SYNTH;
G.rmSfx=api;
})(typeof window!=='undefined'?window:globalThis);
