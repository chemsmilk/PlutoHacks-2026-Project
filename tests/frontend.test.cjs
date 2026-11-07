// Run the real browser controller against simulated devices and network responses.
// These tests verify lifecycle logic; they do not replace physical-camera tests.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const code=fs.readFileSync(require('node:path').join(__dirname,'../static/app.js'),'utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const result=(input='https://example.test')=>({input,findings:[],host:'example.test',domain:'example.test',status:'clear',title:'No obvious indicators found',message:'Not verified',limitations:'Structure only',reputation:'Not checked'});
function harness(){
 const nodes=new Map(),listeners={},timers=new Map(),calls=[];let timerId=0;
 function node(){return {hidden:false,disabled:false,textContent:'',value:'',children:[],files:[],attributes:{},videoWidth:100,videoHeight:100,readyState:2,
  append(...x){this.children.push(...x);},replaceChildren(...x){this.children=x;},setAttribute(k,v){this.attributes[k]=v;},focus(){},scrollIntoView(){},click(){this.onclick?.();},play:async()=>{},
  getContext:()=>({drawImage(){},getImageData:()=>({data:new Uint8ClampedArray(40000),width:100,height:100})})};}
 const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
 const sandbox={document:{hidden:false,getElementById:get,querySelector:get,querySelectorAll:()=>[],createElement:node,createTextNode:text=>({textContent:text}),addEventListener:(k,v)=>{listeners[k]=v;}},
  window:{isSecureContext:true,addEventListener:(k,v)=>{listeners[k]=v;}},navigator:{onLine:true,mediaDevices:{getUserMedia:async()=>{throw Object.assign(Error(),{name:'NotAllowedError'});}}},
  URL:{createObjectURL:()=> 'blob:fixture',revokeObjectURL(){}},Blob,AbortController,
  setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId;},clearTimeout:id=>timers.delete(id),
  matchMedia:()=>({matches:false}),jsQR:()=>null,
  createImageBitmap:async()=>({width:100,height:100,close(){}}),
  fetch:async(path,options)=>{calls.push({path,options});return {ok:true,json:async()=>result(JSON.parse(options.body).text)};}
 };
 vm.createContext(sandbox);vm.runInContext(code,sandbox);
 return {s:sandbox,get,run:script=>vm.runInContext(script,sandbox),listeners,timers,calls};
}
test('camera denial leaves upload and paste available',async()=>{
 const h=harness();await h.get('camera').onclick();
 assert.match(h.get('camera-message').textContent,/denied/);assert.equal(h.get('camera').disabled,false);assert.equal(h.calls.length,0);
});
test('late camera permission after Stop releases the acquired track',async()=>{
 const h=harness(),d=deferred();let stopped=0;
 h.s.navigator.mediaDevices.getUserMedia=()=>d.promise;
 const start=h.get('camera').onclick();h.get('stop').onclick();
 d.resolve({getTracks:()=>[{stop(){stopped++;}}]});await start;
 assert.equal(stopped,1);assert.equal(h.get('video').srcObject,null);assert.equal(h.run('scanning'),false);
});
test('tab hiding stops an active camera and polling',async()=>{
 const h=harness();let stopped=0;
 h.s.navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop(){stopped++;}}]});
 await h.get('camera').onclick();assert.equal(h.run('scanning'),true);
 h.s.document.hidden=true;h.listeners.visibilitychange();assert.equal(stopped,1);assert.equal(h.timers.size,0);
});
test('camera frame decodes text and submits only to the local analysis route',async()=>{
 const h=harness();let stopped=0;
 h.s.navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop(){stopped++;}}]});
 h.s.jsQR=()=>({data:'https://example.test/camera'});
 await h.get('camera').onclick();await Promise.resolve();await Promise.resolve();
 assert.equal(stopped,1);assert.equal(h.get('url').value,'https://example.test/camera');
 assert.deepEqual(h.calls.map(x=>x.path),['/api/analyze']);
});
test('empty input clears old result without making a request',async()=>{
 const h=harness();await h.run("analyze('https://example.test')");await h.run("analyze('   ')");
 assert.equal(h.calls.length,1);assert.equal(h.run('current'),null);assert.equal(h.get('result').hidden,true);
});
test('overlapping analysis responses cannot overwrite the latest result',async()=>{
 const h=harness(),first=deferred();let n=0;
 h.s.fetch=async()=>{if(++n===1)return first.promise;return {ok:true,json:async()=>result('second')};};
 const old=h.run("analyze('https://first.test')");await h.run("analyze('https://second.test')");
 first.resolve({ok:true,json:async()=>result('first')});await old;
 assert.equal(h.run('current.input'),'second');
});
test('late image decoding cannot overwrite a new pasted URL',async()=>{
 const h=harness(),image=deferred();let closed=0;
 h.s.createImageBitmap=()=>image.promise;h.s.jsQR=()=>({data:'https://old.test'});
 const upload=h.get('upload').onchange({target:{files:[{size:10}],value:'fixture'}});
 await h.run("analyze('https://new.test')");
 image.resolve({width:100,height:100,close(){closed++;}});await upload;
 assert.equal(h.run('current.input'),'https://new.test');assert.equal(closed,1);
});
test('oversized uploads are rejected without decoding or contacting a server',async()=>{
 const h=harness();let decoded=false;h.s.createImageBitmap=async()=>{decoded=true;};
 await h.get('upload').onchange({target:{files:[{size:11*1024*1024}],value:''}});
 assert.equal(decoded,false);assert.equal(h.calls.length,0);assert.match(h.get('error').textContent,/10 MB/);
});
test('blank image produces a clear error and releases image memory',async()=>{
 const h=harness();let closed=0;h.s.createImageBitmap=async()=>({width:100,height:100,close(){closed++;}});
 await h.get('upload').onchange({target:{files:[{size:1}],value:''}});
 assert.equal(closed,1);assert.match(h.get('error').textContent,/No QR code/);
});
test('older browsers use image-element fallback and revoke the blob URL',async()=>{
 const h=harness();let revoked=0;h.s.createImageBitmap=undefined;
 h.s.Image=class {set src(value){this.onload();}naturalWidth=100;naturalHeight=100;};
 h.s.URL.revokeObjectURL=()=>{revoked++;};await h.run('readImage({})');assert.equal(revoked,1);
});
test('untrusted text is rendered as text, never markup or a URL navigation',async()=>{
 const h=harness();const payload='https://example.test/<img src=https://other.test>';
 h.s.fetch=async()=>({ok:true,json:async()=>result(payload)});
 await h.run("analyze('https://example.test')");assert.equal(h.get('raw').textContent,payload);
 assert.equal(h.get('raw').innerHTML,undefined);
});
test('AI failure leaves complete findings and re-enables its button',async()=>{
 const h=harness();await h.run("analyze('https://example.test')");
 const before=h.get('simple').children.length;h.s.fetch=async()=>{throw Error('mock outage');};
 await h.get('explain').onclick();assert.equal(h.get('simple').children.length,before);
 assert.match(h.get('ai-note').textContent,/AI unavailable/);assert.equal(h.get('explain').disabled,false);
});
test('clearing a scan aborts requests and removes decoded content',async()=>{
 const h=harness();await h.run("analyze('https://example.test')");h.get('reset').onclick();
 assert.equal(h.run('current'),null);assert.equal(h.get('raw').textContent,'');assert.equal(h.get('simple').children.length,0);
});
