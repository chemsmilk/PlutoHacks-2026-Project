const CACHE='pluq-v2';
const SHELL=['/','/style.css','/app.js','/vendor/jsQR.js','/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png','/demo.html','/demo-ordinary.png','/demo-disguised.png'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('pluq-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 const url=new URL(e.request.url);
 // Never intercept scans, AI requests, cross-origin URLs, or cache query strings.
 if(e.request.method!=='GET'||url.origin!==self.location.origin||url.search||!SHELL.includes(url.pathname))return;
 e.respondWith((async()=>{
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),4000);
  try{
   const response=await fetch(e.request,{signal:controller.signal});
   if(response.ok)return response;
   return await caches.match(url.pathname)||response;
  }catch{
   return await caches.match(url.pathname)||Response.error();
  }finally{clearTimeout(timeout);}
 })());
});
