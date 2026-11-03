// The script the relay adds to remastered.html when it serves the page to a browser:
// the WebSocket that carries the game's output() calls in and byond:// commands out,
// the native prompts drawn as a card, and the keys the page leaves to the skin's macros.
namespace Robust.Client.WebView;

internal static class RelayShim {
    public const string Waiting = @"<!doctype html><html><head><meta charset='utf-8'><title>Kin &amp; Stone</title>
<style>html,body{height:100%;margin:0;background:#141210;color:#e8dcc0;font:16px/1.4 Georgia,serif;display:flex;align-items:center;justify-content:center}
.b{text-align:center}.b h1{font-weight:normal;letter-spacing:.08em;margin:0 0 .4em}.b p{opacity:.7;margin:0}</style></head>
<body><div class='b'><h1>Kin &amp; Stone</h1><p>Joining the world…</p></div>
<script>(function poll(){fetch('/health',{cache:'no-store'}).then(r=>r.text()).then(t=>{if(t==='ready')location.reload();else setTimeout(poll,1200)}).catch(()=>setTimeout(poll,1500))})()</script></body></html>";

    /// <summary>Goes in the head: the page calls send() while it loads, before the main shim runs.</summary>
    public const string Early = @"window.__relayQueue=[];window.__relayNav=function(u){window.__relayQueue.push(u)};";

    public const string Script = @"(function(){
var ws=null,retry=0,pending=[],banner=null,prompts={};
(window.__relayQueue||[]).forEach(function(u){pending.push(JSON.stringify({nav:u}))});window.__relayQueue=[];
function show(text){if(!banner){banner=document.createElement('div');banner.style.cssText='position:fixed;top:0;left:0;right:0;z-index:99999;background:#5a1d1d;color:#fff;font:14px/1.4 sans-serif;text-align:center;padding:6px';document.body.appendChild(banner)}banner.textContent=text;banner.style.display=''}
function hide(){if(banner)banner.style.display='none'}
function post(o){var s=JSON.stringify(o);if(ws&&ws.readyState===1)ws.send(s);else pending.push(s)}
function connect(){
  try{ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws')}catch(e){show('Cannot reach the game.');return}
  ws.onopen=function(){retry=0;hide();ws.send(JSON.stringify({ready:1}));while(pending.length)ws.send(pending.shift())};
  ws.onmessage=function(e){var m;try{m=JSON.parse(e.data)}catch(err){return}
    if(m.js){try{(0,eval)(m.js)}catch(err){console.error('[relay] script failed',err,String(m.js).slice(0,120))}}
    else if(m.prompt)showPrompt(m.prompt);
    else if(m.promptClose!=null)closePrompt(m.promptClose)};
  ws.onclose=function(){show('Connection to the game lost. Reconnecting…');setTimeout(connect,Math.min(5000,500*Math.pow(2,retry++)))};
  ws.onerror=function(){};
}
window.__relayNav=function(u){post({nav:u})};
window.__relayCmd=function(c){post({cmd:c})};   /* a skin command (verb name, .winset ...), as a macro would run it */
if(typeof window.send!=='function'||String(window.send).indexOf('__relayNav')<0){
  window.send=function(action,value){var u='byond://?rm='+encodeURIComponent(action)+'&value='+encodeURIComponent(value==null?'':value);
    try{if(typeof commandSelectionBound==='function'&&commandSelectionBound(action,value))u+='&selection='+encodeURIComponent(currentSelectionToken())}catch(e){}
    post({nav:u})}}
/* keys: in the native app the game window has the keyboard and the skin's macros (letters, digits, Space, arrows,
   F-keys...) act on every key; the page only sees keys typed into its own fields. The same here: keys go to the
   engine and the page's handlers are skipped, except while typing in a field, in a prompt card, or for Escape. */
function typing(t){return t&&(t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable)}
function ours(t){return t&&t.closest&&t.closest('#relayPrompt')}
function keymsg(e,down){return {key:{code:e.code,down:down,alt:e.altKey,ctrl:e.ctrlKey,shift:e.shiftKey}}}
function onkey(e,down){if(e.metaKey||typing(e.target)||ours(e.target)||e.code==='Escape')return;
  if(!e.repeat)post(keymsg(e,down));e.stopImmediatePropagation();e.preventDefault()}
window.addEventListener('keydown',function(e){onkey(e,true)},true);
window.addEventListener('keyup',function(e){onkey(e,false)},true);
/* native prompts (input()/alert()) as a card */
var css='#relayPrompt{position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;font:15px/1.4 sans-serif}'+
 '#relayPrompt .c{background:#1d1a16;color:#eee3c8;border:1px solid #6b5a3a;border-radius:8px;min-width:300px;max-width:520px;padding:16px 18px;box-shadow:0 8px 30px rgba(0,0,0,.6)}'+
 '#relayPrompt h3{margin:0 0 8px;font-size:16px;font-weight:600}#relayPrompt p{margin:0 0 12px;white-space:pre-wrap}'+
 '#relayPrompt input,#relayPrompt textarea{width:100%;box-sizing:border-box;background:#0f0d0b;color:#eee3c8;border:1px solid #6b5a3a;border-radius:4px;padding:6px 8px;font:inherit}'+
 '#relayPrompt .items{max-height:260px;overflow:auto;margin:0 0 12px;border:1px solid #6b5a3a;border-radius:4px}#relayPrompt .items div{padding:6px 10px;cursor:pointer}#relayPrompt .items div:hover,#relayPrompt .items div.sel{background:#4a3a22}'+
 '#relayPrompt .btns{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}#relayPrompt button{background:#4a3a22;color:#f3e9d2;border:1px solid #8a7446;border-radius:4px;padding:6px 14px;font:inherit;cursor:pointer}#relayPrompt button:hover{background:#5d4a2b}';
function closePrompt(id){var box=prompts[id];if(box){box.remove();delete prompts[id]}}
function showPrompt(p){closePrompt(p.id);if(!document.getElementById('relayPromptCss')){var s=document.createElement('style');s.id='relayPromptCss';s.textContent=css;document.head.appendChild(s)}
  var box=document.createElement('div');box.id='relayPrompt';var card=document.createElement('div');card.className='c';box.appendChild(card);
  var h=document.createElement('h3');h.textContent=p.title||'';card.appendChild(h);
  if(p.message){var m=document.createElement('p');m.textContent=p.message;card.appendChild(m)}
  var field=null,selected=-1;
  if(p.kind==='TextPrompt'||p.kind==='NumberPrompt'){field=document.createElement('input');field.type=p.kind==='NumberPrompt'?'number':(p.title==='Join password'?'password':'text');field.value=p.value||'';card.appendChild(field)}
  else if(p.kind==='MessagePrompt'){field=document.createElement('textarea');field.rows=5;field.value=p.value||'';card.appendChild(field)}
  else if(p.kind==='ListPrompt'){var list=document.createElement('div');list.className='items';(p.items||[]).forEach(function(t,i){var d=document.createElement('div');d.textContent=t;d.onclick=function(){selected=i;Array.prototype.forEach.call(list.children,function(c,j){c.classList.toggle('sel',j===i)})};d.ondblclick=function(){selected=i;answer('Ok')};list.appendChild(d)});card.appendChild(list)}
  var btns=document.createElement('div');btns.className='btns';
  var names=(p.buttons&&p.buttons.length)?p.buttons:['Ok'];
  function answer(name){if(name==='Cancel'){post({prompt:{id:p.id,cancel:true}})}
    else if(p.kind==='ListPrompt'){if(selected<0)return;post({prompt:{id:p.id,button:name,value:selected}})}
    else post({prompt:{id:p.id,button:name,value:field?field.value:name}});
    closePrompt(p.id)}
  names.forEach(function(name){var b=document.createElement('button');b.textContent=name;b.onclick=function(){answer(name)};btns.appendChild(b)});
  card.appendChild(btns);
  box.addEventListener('keydown',function(e){e.stopPropagation();if(e.key==='Enter'&&p.kind!=='MessagePrompt'){e.preventDefault();answer(names[0])}else if(e.key==='Escape'&&names.indexOf('Cancel')>=0){e.preventDefault();answer('Cancel')}});
  document.body.appendChild(box);prompts[p.id]=box;if(field)field.focus();else box.tabIndex=-1,box.focus();
}
if(document.readyState==='complete')connect();else window.addEventListener('load',connect);
})();";
}
