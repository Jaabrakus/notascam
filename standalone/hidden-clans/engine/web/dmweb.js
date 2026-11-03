/* The web link's main script (engine/web/, U4): put at the end of <body> by RmWebServer. One WebSocket to the
   server (<this page's folder>ws): the game's output() calls come in as {f, a} and are called by name; the page's
   byond:// links, prompt answers and its size go out. The game's native prompts (input(), alert()) show as a card. */
(function(){
var W=window.__dmWeb,ws=null,retry=0,banner=null,prompts={},done=false;
var base=location.pathname.replace(/[^\/]*$/,'');
function show(text){if(!banner){banner=document.createElement('div');banner.style.cssText='position:fixed;top:0;left:0;right:0;z-index:99999;background:#5a1d1d;color:#fff;font:14px/1.4 sans-serif;text-align:center;padding:6px';document.body.appendChild(banner)}banner.textContent=text;banner.style.display=''}
function hide(){if(banner)banner.style.display='none'}
function post(o){var s=JSON.stringify(o);if(ws&&ws.readyState===1)ws.send(s);else W.q.push(s)}
W.post=post;
function size(){return {w:window.innerWidth,h:window.innerHeight}}
function call(name,args){var f=window,parts=name.split('.');for(var i=0;i<parts.length&&f;i++)f=f[parts[i]];
  if(typeof f!=='function'){console.warn('[web] the page has no '+name+'()');return}f.apply(null,args)}
/* The socket compressed (RmWebServer.cs, 10-31): when this browser can inflate (DecompressionStream), the hello says
   so and the server sends each message as a binary frame, its length (4 bytes) and then its part of one deflate stream
   kept for the connection. Frames are handled strictly in order, text and binary alike; one that fails to inflate
   closes the socket, and the page comes back without compression. */
var canZ=typeof DecompressionStream==='function'&&typeof TextDecoder==='function',noZ=false,chain=null,inf=null,conn=0;
function inflater(){if(inf)return inf;
  var ds=new DecompressionStream('deflate-raw'),w=ds.writable.getWriter(),r=ds.readable.getReader(),buf=new Uint8Array(0),dec=new TextDecoder();
  inf={put:function(bytes){w.write(bytes)},
    take:function(n){   /* the next n bytes the stream gives, as text */
      function more(){if(buf.length>=n){var out=buf.subarray(0,n);buf=buf.slice(n);return Promise.resolve(dec.decode(out))}
        return r.read().then(function(x){if(x.done)throw new Error('the inflate stream ended');var nb=new Uint8Array(buf.length+x.value.length);nb.set(buf);nb.set(x.value,buf.length);buf=nb;return more()})}
      return more()}};
  return inf}
function connect(){
  try{ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+base+'ws?v='+W.v)}catch(e){show('Cannot reach the game.');return}
  ws.binaryType='arraybuffer';chain=Promise.resolve();inf=null;var mine=++conn;   /* an old connection's messages still in hand are dropped */
  ws.onopen=function(){retry=0;hide();var h=size();h.pv=W.pv;if(canZ&&!noZ)h.z=1;ws.send(JSON.stringify({hello:h}));while(W.q.length)ws.send(W.q.shift())};
  ws.onmessage=function(e){var d=e.data,sock=ws;
    chain=chain.then(function(){if(mine!==conn)return;if(typeof d==='string')return got(d);
      var n=new DataView(d).getUint32(0),I=inflater();I.put(new Uint8Array(d,4));return I.take(n).then(function(t){if(mine===conn)got(t)})})
    .catch(function(err){console.error('[web] a message could not be read',err);noZ=true;try{sock.close()}catch(x){}})};
  ws.onclose=function(e){if(done)return;
    if(e.code===4001){done=true;show('The game was updated. Reload this page.');return}
    show('Connection to the game lost. Reconnecting…');
    /* the server forgets a player away longer than its grace (or restarts): then this page's address is gone (410) */
    setTimeout(function(){fetch(base+'alive',{cache:'no-store'}).then(function(r){if(r.status===410){done=true;show('This game session has ended. Reload the page to join again.')}else connect()},connect)},
      Math.min(5000,500*Math.pow(2,retry++)))};
  ws.onerror=function(){};
}
function got(text){var m;try{m=JSON.parse(text)}catch(err){return}
    if(m.f){try{call(m.f,m.a||[])}catch(err){console.error('[web] '+m.f+'() failed',err)}}
    else if(m.keys){gameKeys={};m.keys.forEach(function(s){var i=s.indexOf('|'),k=s.slice(i+1);(gameKeys[k]=gameKeys[k]||[]).push(+s.slice(0,i))})}
    else if(m.prompt)showPrompt(m.prompt);
    else if(m.promptClose!=null)closePrompt(m.promptClose);
    else if(m.reload!=null){done=true;location.reload()}
    else if(m.out!=null)console.log('[game]'+(m.to?' '+m.to:''),m.out);
    else if(m.bye!=null){done=true;show(m.bye)}}
var resized=0;window.addEventListener('resize',function(){clearTimeout(resized);resized=setTimeout(function(){post({size:size()})},250)});
/* keys: in the native app the game window runs the skin's macros. Here the keys that have one (the server sends them
   as "MODS|KEY": 1 Shift, 2 Ctrl, 4 Alt, in BYOND's key names) go to the server, which runs the macro's command; the
   page's own handlers don't see them. Every other key, typing in a field, a prompt card, Escape and Cmd stay with the
   page. A key held down is sent once; the server repeats its +REP macro until the key comes up. */
var gameKeys={},held={};
var named={Space:'SPACE',Tab:'TAB',Escape:'ESCAPE',Enter:'RETURN',NumpadEnter:'RETURN',Backspace:'BACK',Insert:'INSERT',Delete:'DELETE',Pause:'PAUSE',
  ArrowUp:'NORTH',ArrowDown:'SOUTH',ArrowRight:'EAST',ArrowLeft:'WEST',Home:'NORTHWEST',End:'SOUTHWEST',PageUp:'NORTHEAST',PageDown:'SOUTHEAST',
  NumpadMultiply:'MULTIPLY',NumpadAdd:'ADD',NumpadSubtract:'SUBTRACT',NumpadDivide:'DIVIDE',Semicolon:';',Comma:',',Period:'.',Backquote:'`'};
function keyName(c){if(/^Key[A-Z]$/.test(c))return c.slice(3);if(/^Digit\d$/.test(c))return c.slice(5);if(/^Numpad\d$/.test(c))return 'NUMPAD'+c.slice(6);
  if(/^F([1-9]|1[0-5])$/.test(c))return c;return named[c]||null}
function typing(t){return t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable)}
function onKey(e,down){var k=keyName(e.code);if(!k||k==='ESCAPE'||e.metaKey)return;
  if(down){var t=e.target;if(typing(t)||(t&&t.closest&&t.closest('#dmPrompt')))return;
    var m=(e.shiftKey?1:0)|(e.ctrlKey?2:0)|(e.altKey?4:0);if(!(gameKeys[k]||[]).some(function(x){return (x&~m)===0}))return;
    if(!e.repeat){held[k]=m;post({key:{k:k,m:m,d:1}})}}
  else{if(!(k in held))return;post({key:{k:k,m:held[k],d:0}});delete held[k]}
  e.preventDefault();e.stopImmediatePropagation()}
window.addEventListener('keydown',function(e){onKey(e,true)},true);
window.addEventListener('keyup',function(e){onKey(e,false)},true);
window.addEventListener('blur',function(){for(var k in held)post({key:{k:k,m:held[k],d:0}});held={}});
/* native prompts (input()/alert()) as a card */
var css='#dmPrompt{position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;font:15px/1.4 sans-serif}'+
 '#dmPrompt .c{background:#1d1a16;color:#eee3c8;border:1px solid #6b5a3a;border-radius:8px;min-width:300px;max-width:520px;padding:16px 18px;box-shadow:0 8px 30px rgba(0,0,0,.6)}'+
 '#dmPrompt h3{margin:0 0 8px;font-size:16px;font-weight:600}#dmPrompt p{margin:0 0 12px;white-space:pre-wrap}'+
 '#dmPrompt input,#dmPrompt textarea{width:100%;box-sizing:border-box;background:#0f0d0b;color:#eee3c8;border:1px solid #6b5a3a;border-radius:4px;padding:6px 8px;font:inherit}'+
 '#dmPrompt .items{max-height:260px;overflow:auto;margin:0 0 12px;border:1px solid #6b5a3a;border-radius:4px}#dmPrompt .items div{padding:6px 10px;cursor:pointer}#dmPrompt .items div:hover,#dmPrompt .items div.sel{background:#4a3a22}'+
 '#dmPrompt .btns{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}#dmPrompt button{background:#4a3a22;color:#f3e9d2;border:1px solid #8a7446;border-radius:4px;padding:6px 14px;font:inherit;cursor:pointer}#dmPrompt button:hover{background:#5d4a2b}';
function closePrompt(id){var box=prompts[id];if(box){box.remove();delete prompts[id]}}
function showPrompt(p){closePrompt(p.id);if(!document.getElementById('dmPromptCss')){var s=document.createElement('style');s.id='dmPromptCss';s.textContent=css;document.head.appendChild(s)}
  var box=document.createElement('div');box.id='dmPrompt';var card=document.createElement('div');card.className='c';box.appendChild(card);
  var h=document.createElement('h3');h.textContent=p.title||'';card.appendChild(h);
  if(p.message){var m=document.createElement('p');m.textContent=p.message;card.appendChild(m)}
  var field=null,selected=-1;
  if(p.kind==='TextPrompt'||p.kind==='NumberPrompt'){field=document.createElement('input');field.type=p.kind==='NumberPrompt'?'number':'text';field.value=p.value||'';card.appendChild(field)}
  else if(p.kind==='MessagePrompt'){field=document.createElement('textarea');field.rows=5;field.value=p.value||'';card.appendChild(field)}
  else if(p.kind==='ListPrompt'){var list=document.createElement('div');list.className='items';(p.items||[]).forEach(function(t,i){var d=document.createElement('div');d.textContent=t;
    if(t===p.value){selected=i;d.className='sel'}
    d.onclick=function(){selected=i;Array.prototype.forEach.call(list.children,function(c,j){c.classList.toggle('sel',j===i)})};d.ondblclick=function(){selected=i;answer('Ok')};list.appendChild(d)});card.appendChild(list)}
  var btns=document.createElement('div');btns.className='btns';
  var names=(p.buttons&&p.buttons.length)?p.buttons:['Ok'];
  function answer(name){if(name==='Cancel'&&p.kind!=='AlertWindow'){post({prompt:{id:p.id,cancel:true}})}
    else if(p.kind==='ListPrompt'){if(selected<0)return;post({prompt:{id:p.id,button:name,value:selected}})}
    else post({prompt:{id:p.id,button:name,value:field?field.value:name}});
    closePrompt(p.id)}
  names.forEach(function(name){var b=document.createElement('button');b.textContent=name;b.onclick=function(){answer(name)};btns.appendChild(b)});
  card.appendChild(btns);
  box.addEventListener('keydown',function(e){e.stopPropagation();if(e.key==='Enter'&&p.kind!=='MessagePrompt'){e.preventDefault();answer(names[0])}else if(e.key==='Escape'&&names.indexOf('Cancel')>=0){e.preventDefault();answer('Cancel')}});
  document.body.appendChild(box);prompts[p.id]=box;if(field)field.focus();else{box.tabIndex=-1;box.focus()}
}
if(document.readyState==='complete')connect();else window.addEventListener('load',connect);
})();
