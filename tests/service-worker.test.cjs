const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function setup(fetch){
 const listeners={},cached=[];
 const context={self:{location:{origin:'https://pluq.test'},clients:{claim:async()=>{}},addEventListener:(k,v)=>listeners[k]=v},URL,Response,AbortController,setTimeout,clearTimeout,fetch,
  caches:{open:async()=>({addAll:async assets=>cached.push(...assets)}),keys:async()=>[],match:async()=>new Response('offline shell')}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/sw.js'),'utf8'),context);
 return {listeners,cached};
}
test('service worker caches only existing shell assets',async()=>{
 const h=setup();let work;h.listeners.install({waitUntil:p=>work=p});await work;
 for(const asset of h.cached)assert.ok(fs.existsSync(path.join(__dirname,'../static',asset==='/'?'index.html':asset)),asset);
 assert.ok(!h.cached.some(x=>x.startsWith('/api/')));
});
test('service worker never handles API calls, scanned hosts, or query strings',()=>{
 const h=setup();
 for(const [url,method] of [['https://pluq.test/api/analyze','POST'],['https://other.test/','GET'],['https://pluq.test/?secret=fixture','GET']]){
  let intercepted=false;h.listeners.fetch({request:{url,method},respondWith:()=>intercepted=true});assert.equal(intercepted,false);
 }
});
test('offline shell is served when network fails',async()=>{
 const h=setup(async()=>{throw Error('offline');});let work;
 h.listeners.fetch({request:{url:'https://pluq.test/',method:'GET'},respondWith:p=>work=p});
 assert.equal(await (await work).text(),'offline shell');
});
test('server errors fall back to shell, not a broken error page',async()=>{
 const h=setup(async()=>new Response('bad gateway',{status:502}));let work;
 h.listeners.fetch({request:{url:'https://pluq.test/app.js',method:'GET'},respondWith:p=>work=p});
 assert.equal(await (await work).text(),'offline shell');
});
