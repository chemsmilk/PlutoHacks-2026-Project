'use strict';
const $=id=>document.getElementById(id);
let stream=null, scanning=false, generation=0, current=null, installPrompt=null;
let cameraGeneration=0, frameTimer=null, pendingRequest=null;
const canvas=document.createElement('canvas'), context=canvas.getContext('2d',{willReadFrequently:true});
const uploadLabel=document.querySelector('label[for="upload"]');
uploadLabel.tabIndex=0;uploadLabel.setAttribute('role','button');
uploadLabel.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('upload').click();}};
function el(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n;}
function error(message){$('error').textContent=message;$('error').hidden=!message;}
function stopCamera(){
 cameraGeneration++;scanning=false;clearTimeout(frameTimer);
 if(stream)stream.getTracks().forEach(t=>t.stop());
 stream=null;$('video').srcObject=null;$('video').hidden=true;
 $('camera-placeholder').hidden=false;$('stop').hidden=true;$('camera').hidden=false;$('camera').disabled=false;
}
// A new input invalidates every pending response from an earlier input.
function beginInput(){
 generation++;pendingRequest?.abort();pendingRequest=null;current=null;
 $('result').hidden=true;$('empty').hidden=false;$('result-count').textContent='READY';
 $('analyze').disabled=false;$('analyze').textContent='Check this address →';error('');
 return generation;
}
function decode(source,w,h){const scale=Math.min(1,1200/Math.max(w,h));canvas.width=Math.round(w*scale);canvas.height=Math.round(h*scale);context.drawImage(source,0,0,canvas.width,canvas.height);const data=context.getImageData(0,0,canvas.width,canvas.height);return jsQR(data.data,data.width,data.height,{inversionAttempts:'attemptBoth'});}
async function frame(token){
 if(!scanning||token!==cameraGeneration)return;
 try{
  const video=$('video');
  if(video.readyState>=2&&video.videoWidth&&video.videoHeight){
   const code=decode(video,video.videoWidth,video.videoHeight);
   if(code){stopCamera();$('camera-message').textContent='QR decoded on your device. Destination was not opened.';$('url').value=code.data;await analyze(code.data);return;}
  }
 }catch{stopCamera();error('Could not decode the camera frame. Try uploading an image.');return;}
 if(scanning&&token===cameraGeneration)frameTimer=setTimeout(()=>frame(token),180);
}
async function startCamera(){
 beginInput();stopCamera();
 if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia){$('camera-message').textContent='Camera needs HTTPS or localhost. Use image upload here, or open a trusted HTTPS version on your phone.';return;}
 const token=cameraGeneration;
 $('camera').disabled=true;$('stop').hidden=false;
 $('camera-message').textContent='Waiting for camera permission. You can cancel with Stop camera.';
 try{
  const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280}},audio:false});
  // Permission can arrive after Stop, upload, or a tab switch. Release that camera.
  if(token!==cameraGeneration||document.hidden){acquired.getTracks().forEach(t=>t.stop());return;}
  stream=acquired;$('video').srcObject=stream;
  // A visible inline video is more reliable on mobile Safari.
  $('video').hidden=false;$('camera-placeholder').hidden=true;
  await $('video').play();
  if(token!==cameraGeneration)return;
  $('camera').hidden=true;scanning=true;
  $('camera-message').textContent='Center one QR code in the frame. Scanning stays on this device.';frame(token);
 }catch(e){
  if(token!==cameraGeneration)return;
  stopCamera();$('camera-message').textContent=e.name==='NotAllowedError'?'Camera permission was denied. Allow camera access in browser settings, or upload a QR image.':'Camera unavailable. Close other camera apps, or upload a QR image.';
 }finally{if(token===cameraGeneration)$('camera').disabled=false;}
}
$('camera').onclick=startCamera;
$('stop').onclick=()=>{stopCamera();$('camera-message').textContent='Camera stopped.';};
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopCamera();});window.addEventListener('pagehide',stopCamera);
async function readImage(file){
 if(typeof createImageBitmap==='function'){
  try{return await createImageBitmap(file);}catch{/* Use the image-element fallback below. */}
 }
 const url=URL.createObjectURL(file);
 try{
  const image=new Image();
  await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Unable to read this image. Try PNG or JPEG.'));image.src=url;});
  return image;
 }finally{URL.revokeObjectURL(url);}
}
$('upload').onchange=async event=>{
 const file=event.target.files[0];event.target.value='';if(!file)return;
 stopCamera();const token=beginInput();
 if(file.size>10*1024*1024){error('Choose an image smaller than 10 MB.');return;}
 let bitmap;
 try{
  bitmap=await readImage(file);if(token!==generation)return;
  const width=bitmap.naturalWidth||bitmap.width,height=bitmap.naturalHeight||bitmap.height;
  if(!width||!height||width*height>40000000)throw Error('Image dimensions are too large or invalid.');
  const code=decode(bitmap,width,height);
  if(!code)throw Error('No QR code found. Try a sharp, well-lit image containing the entire code.');
  $('url').value=code.data;await analyze(code.data);
 }catch(e){if(token===generation)error(e.message||'Unable to read that image. Try PNG or JPEG.');}
 finally{bitmap?.close?.();}
};
async function request(path,text){
 const controller=new AbortController();pendingRequest=controller;
 const timer=setTimeout(()=>controller.abort(),18000);
 try{
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:controller.signal});
  if(!response.ok)throw Error(response.status===422?'Please enter between 1 and 4,096 characters.':'The local server could not complete this request.');
  return await response.json();
 }catch(e){
  if(e.name==='AbortError')throw Error('The request timed out or was cancelled. Please try again.');
  if(e instanceof TypeError)throw Error('Cannot reach PluQ. Check that the local server is running, then try again.');
  throw e;
 }finally{clearTimeout(timer);if(pendingRequest===controller)pendingRequest=null;}
}
async function analyze(text){
 const token=beginInput();stopCamera();
 if(!text.trim()||text.length>4096){error('Please enter between 1 and 4,096 characters.');return;}
 $('analyze').disabled=true;$('analyze').textContent='Checking the address…';
 try{
  const data=await request('/api/analyze',text);if(token!==generation)return;
  current=data;render(data);
  if(matchMedia('(max-width:850px)').matches)$('results-title').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
 }catch(e){if(token===generation)error(navigator.onLine?e.message:'You are offline. Scanning can decode QR content, but analysis needs the local server.');}
 finally{if(token===generation){$('analyze').disabled=false;$('analyze').textContent='Check this address →';}}
}
$('scan-form').onsubmit=e=>{e.preventDefault();analyze($('url').value);};document.querySelectorAll('[data-demo]').forEach(b=>b.onclick=()=>{$('url').value=b.dataset.demo;analyze(b.dataset.demo);});
function findings(data,order){$('simple').replaceChildren();$('technical').replaceChildren();const items=order?order.map(id=>data.findings.find(f=>f.id===id)).filter(Boolean):data.findings;for(const f of items){const card=el('article','','finding');card.append(el('h4',f.title));for(const [label,value] of [['What we detected',f.detected],['Why it matters',f.why],['What to do',f.action]]){const p=el('p','',label==='What to do'?'action':'');p.append(el('b',label),document.createTextNode(value));card.append(p);}$('simple').append(card);const technical=el('article','','finding');technical.append(el('h4',f.title),el('pre',f.evidence),el('p',f.why));$('technical').append(technical);}if(!items.length){$('simple').append(el('p',data.message),el('p','For passwords or payments, use an official app or a bookmark you already trust.'));}$('technical').append(el('pre',JSON.stringify({scheme:data.scheme,hostname:data.host,destination_domain:data.domain,domain_basis:data.domain_basis,port:data.port,reputation:data.reputation,destination_contacted:false},null,2)),el('p',data.limitations));}
function render(data){$('empty').hidden=true;$('result').hidden=false;$('result-count').textContent=data.findings.length+' INDICATORS';$('verdict').className='verdict '+data.status;$('verdict-label').textContent=data.status==='caution'?'CAUTION · VERIFY FIRST':data.status==='clear'?'STRUCTURE CHECK COMPLETE':'NOT ASSESSED';$('verdict-title').textContent=data.title;$('verdict-message').textContent=data.message;$('domain').textContent=data.domain||'No web destination identified';$('host').textContent=data.host?'Full hostname: '+data.host:'';$('raw').textContent=data.input;$('limitations').textContent=data.limitations;$('ai-source').textContent='EVIDENCE-BASED GUIDANCE';$('ai-note').textContent='Complete rule-based explanation. Optional AI can prioritize this guidance using only verified findings.';$('explain').disabled=false;findings(data);setTab(false);}
function setTab(technical){$('simple').hidden=technical;$('technical').hidden=!technical;for(const [id,active]of [['simple-tab',!technical],['technical-tab',technical]]){$(id).setAttribute('aria-selected',String(active));$(id).tabIndex=active?0:-1;}}
$('simple-tab').onclick=()=>setTab(false);$('technical-tab').onclick=()=>setTab(true);document.querySelector('.tabs').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const tech=e.key==='End'||e.key==='ArrowRight';setTab(tech);$(tech?'technical-tab':'simple-tab').focus();}};
$('explain').onclick=async()=>{if(!current)return;const data=current,token=generation;$('explain').disabled=true;$('ai-note').textContent='Preparing your explanation…';try{const explanation=await request('/api/explain',data.input);if(token!==generation)return;$('ai-source').textContent=explanation.source==='ai'?'AI-COMPOSED · VERIFIED CLAUSES':'RULE-BASED · NO AI RESPONSE';$('ai-note').textContent=explanation.note;findings(data,explanation.order);}catch{if(token===generation)$('ai-note').textContent='AI unavailable. The complete rule-based explanation remains above.';}finally{if(token===generation)$('explain').disabled=false;}};
$('reset').onclick=()=>{beginInput();stopCamera();$('url').value='';$('raw').textContent='';$('simple').replaceChildren();$('technical').replaceChildren();$('url').focus();};
$('export').onclick=()=>{if(!current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='pluq-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('install').hidden=false;});$('install').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;$('install').hidden=true;}};
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
