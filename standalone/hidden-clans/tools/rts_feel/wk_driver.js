// rts-feel check in a real WKWebView (tools/rts_feel/wk_feel.py): the 3D view fed a scene, a click on the ground with a
// unit selected, a click on a hostile, two commands in one task, the wheel; then wkcheck reads window.RFT_OUT.
setTimeout(()=>{try{
 v3set(true);update3D(RFT_SCENE);const M=JSON.parse(JSON.stringify(RFT_MODEL));for(const u of M.units)u.selected=u.ref==='ui-test-1';updateHUD(M);
 const [ux,uy,ground,orc]=RFT_U;if(typeof v3iso==='function')v3iso(false);V3.dist=14;V3.pitch=0.75;V3.yaw=0;V3.cx=V3.tcx=ux;V3.cy=V3.tcy=uy;V3.panAt=performance.now();
 const c=$('world3d'),fire=(type,x,y,o)=>{const z=hudKC(),ev=new MouseEvent(type,Object.assign({bubbles:true,cancelable:true,clientX:x*z,clientY:y*z,button:0,buttons:type==='mouseup'?0:1},o||{}));c.dispatchEvent(ev)};
 const at=(x,y,h)=>v3project([x,v3groundAt(x,y)+(h||0.05),-y]);
 setTimeout(()=>{const g=at(ground[0],ground[1]);fire('mousemove',g[0],g[1]);fire('mousedown',g[0],g[1]);fire('mouseup',g[0],g[1]);
  const o=at(orc[0],orc[1],0.55);setTimeout(()=>{fire('mousemove',o[0],o[1]);setTimeout(()=>{fire('mousedown',o[0],o[1]);fire('mouseup',o[0],o[1]);
   send('rftest','one');send('rftest','two');
   c.dispatchEvent(new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY:240,clientX:o[0]*hudKC(),clientY:o[1]*hudKC()}));
   setTimeout(()=>{window.RFT_OUT=JSON.stringify({stats:rfStats(),cur:RF.cur,dist:V3.dist,navs:(window.__navs||[]).map(u=>decodeURIComponent(u).replace(/^byond:\/\/\?rm=/,'').slice(0,60)),mini:RF.costMini,draw:RF.costDraw,frames:RF.fr,camSent:(()=>{v3panSend(true);return RF.camSent.length})()})},2500)},700)},800)},2500)}catch(e){window.RFT_OUT='driver error '+e}},500);
