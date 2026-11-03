/* HUD sends packed by the server (Remastered/HudPack.dm, the engine's rm_pack: UTF-8, raw deflate, base64url, sent with
   a leading "~"). This wraps updateHUD from the outside, last, so the page's own updateHUD and every wrapper inside it
   get the JSON text as before. It tells the server it can unpack ("hudpack" 1); if a send ever fails to unpack it says
   "hudpack" 0 and asks for a full model, which then comes as plain JSON. (server-cost, 2026-10-24) */
(function(){
const A='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',D=new Uint8Array(128);
for(let i=0;i<64;i++)D[A.charCodeAt(i)]=i;
function unb64(s){const n=s.length,out=new Uint8Array((n*3)>>2);let o=0,i=0;
 for(;i+4<=n;i+=4){const v=D[s.charCodeAt(i)]<<18|D[s.charCodeAt(i+1)]<<12|D[s.charCodeAt(i+2)]<<6|D[s.charCodeAt(i+3)];out[o++]=v>>16;out[o++]=v>>8&255;out[o++]=v&255}
 const r=n-i;if(r>=2){const v=D[s.charCodeAt(i)]<<18|D[s.charCodeAt(i+1)]<<12|(r>2?D[s.charCodeAt(i+2)]<<6:0);out[o++]=v>>16;if(r>2)out[o++]=v>>8&255}
 return out.subarray(0,o)}
// RFC 1951 inflate (after zlib's puff.c): stored, fixed and dynamic blocks
const LB=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258],
 LE=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0],
 DB=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577],
 DE=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13],
 CO=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15];
function table(len,n){const cnt=new Uint16Array(16),off=new Uint16Array(16),sym=new Uint16Array(n);
 for(let i=0;i<n;i++)cnt[len[i]]++;cnt[0]=0;for(let i=1;i<16;i++)off[i]=off[i-1]+cnt[i-1];
 for(let i=0;i<n;i++)if(len[i])sym[off[len[i]]++]=i;return{cnt,sym}}
let FL=null,FD=null;
function fixed(){if(FL)return;const l=new Uint8Array(288);for(let i=0;i<288;i++)l[i]=i<144?8:i<256?9:i<280?7:8;FL=table(l,288);FD=table(new Uint8Array(30).fill(5),30)}
function inflate(src){
 let pos=0,buf=0,cnt=0,o=0,out=new Uint8Array(Math.max(4096,src.length*6));
 const bits=n=>{while(cnt<n){if(pos>=src.length)throw new Error('hudpack: input ended');buf|=src[pos++]<<cnt;cnt+=8}const v=buf&((1<<n)-1);buf>>>=n;cnt-=n;return v};
 const room=n=>{if(o+n<=out.length)return;let m=out.length*2;while(m<o+n)m*=2;const t=new Uint8Array(m);t.set(out.subarray(0,o));out=t};
 const decode=h=>{let code=0,first=0,index=0;for(let len=1;len<16;len++){code|=bits(1);const c=h.cnt[len];if(code-c<first)return h.sym[index+code-first];index+=c;first+=c;first<<=1;code<<=1}throw new Error('hudpack: bad code')};
 let last=0;
 do{last=bits(1);const type=bits(2);
  if(type===0){buf=0;cnt=0;if(pos+4>src.length)throw new Error('hudpack: stored block cut');const len=src[pos]|src[pos+1]<<8;pos+=4;
   if(pos+len>src.length)throw new Error('hudpack: stored block cut');room(len);out.set(src.subarray(pos,pos+len),o);o+=len;pos+=len;continue}
  let L,Dt;
  if(type===1){fixed();L=FL;Dt=FD}
  else if(type===2){const nl=bits(5)+257,nd=bits(5)+1,nc=bits(4)+4,cl=new Uint8Array(19);for(let i=0;i<nc;i++)cl[CO[i]]=bits(3);
   const ct=table(cl,19),len=new Uint8Array(nl+nd);let i=0;
   while(i<nl+nd){const s=decode(ct);if(s<16){len[i++]=s;continue}let r=0,v=0;
    if(s===16){if(!i)throw new Error('hudpack: repeat with no length');v=len[i-1];r=3+bits(2)}else if(s===17)r=3+bits(3);else r=11+bits(7);
    if(i+r>nl+nd)throw new Error('hudpack: too many lengths');while(r--)len[i++]=v}
   L=table(len.subarray(0,nl),nl);Dt=table(len.subarray(nl),nd)}
  else throw new Error('hudpack: bad block');
  for(;;){const s=decode(L);
   if(s<256){room(1);out[o++]=s;continue}
   if(s===256)break;
   const k=s-257;if(k>=29)throw new Error('hudpack: bad length');const n=LB[k]+bits(LE[k]);
   const d=decode(Dt);if(d>=30)throw new Error('hudpack: bad distance');const dist=DB[d]+bits(DE[d]);if(dist>o)throw new Error('hudpack: distance too far');
   room(n);for(let j=0;j<n;j++,o++)out[o]=out[o-dist]}
 }while(!last);
 return out.subarray(0,o)}
const utf8=new TextDecoder('utf-8');
function unpack(raw){return utf8.decode(inflate(unb64(raw.slice(1))))}
window.rmHudUnpack=unpack;   // tests (tests/hudpack_test.js)
const hud=window.updateHUD;
if(typeof hud!=='function'||typeof send!=='function')return;
// Commands are byond:// navigations: none while the page loads (WebKit stops reading it; ready is the page's last line),
// and never two in one go (one replaces the other), so each goes on its own timer. A lost "hudpack" 1 only leaves the
// sends plain; a lost "hudpack" 0 is said again while packed sends keep coming.
let told=false,failedAt=0;
window.updateHUD=function(raw){
 if(typeof raw==='string'&&raw.charCodeAt(0)===126){
  if(failedAt){const t=Date.now();if(t-failedAt>=1000){failedAt=t;setTimeout(()=>send('hudpack','0'),0)}return}
  try{raw=unpack(raw)}catch(e){console.error(e);failedAt=Date.now();setTimeout(()=>send('hudpack','0'),0);setTimeout(()=>send('hudfull',''),300);return}
 }else failedAt=0;
 const r=hud(raw);
 if(!told){told=true;setTimeout(()=>{if(!failedAt)send('hudpack','1')},400)}   // after the first model: the page has loaded
 return r};
})();
