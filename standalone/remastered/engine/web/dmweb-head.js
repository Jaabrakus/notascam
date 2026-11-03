/* The web link's first script (engine/web/, U4): put at the top of <head> by RmWebServer, so it runs before the
   page's own scripts. A DM page talks back by going to byond:// links; here those become socket messages. The server
   rewrites the page's location.href assignments to window.__dmGo, whose setter is below; links clicked in the page
   are caught too. Messages wait in q until the socket opens (dmweb.js). */
(function(){
var W=window.__dmWeb={v:__V__,pv:__PV__,q:[]};
W.post=function(o){W.q.push(JSON.stringify(o))};
function topic(u){return /^byond:/i.test(u)||u.charAt(0)==='?'}
function go(u){u=String(u);if(topic(u))W.post({nav:u});else location.href=u}
Object.defineProperty(window,'__dmGo',{configurable:true,get:function(){return location.href},set:go});
document.addEventListener('click',function(e){var a=e.target&&e.target.closest&&e.target.closest('a[href]');if(!a)return;
  var h=a.getAttribute('href')||'';if(topic(h)){e.preventDefault();go(h)}},true);
})();
