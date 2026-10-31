const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 const info=await(await fetch('http://127.0.0.1:8766/api/info')).json(); assert.equal(info.mode,'offline fake');
 assert.ok(info.skyrim_fonts_available, 'This opt-in check needs privately imported game fonts.');
 const pages=await(await fetch('http://127.0.0.1:9223/json/list')).json();const page=pages.find(p=>p.url.startsWith('http://127.0.0.1:8766'));
 const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));let id=0;const requests=new Map(),errors=[];
 ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const p=requests.get(d.id);requests.delete(d.id);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.text);else if(d.method==='Log.entryAdded'&&d.params.entry.level==='error')errors.push(d.params.entry.text);});
 function call(method,params={}){return new Promise((resolve,reject)=>{const n=++id;requests.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});}
 async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
 async function wait(expression){for(let i=0;i<360;i++){if(await run(expression))return;await new Promise(r=>setTimeout(r,25));}throw Error('Timed out: '+expression);}
 async function shot(name){const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.mkdirSync('output/screenshots',{recursive:true});fs.writeFileSync('output/screenshots/'+name+'.png',Buffer.from(r.data,'base64'));}
 await call('Page.enable');await call('Runtime.enable');await call('Log.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});await call('Page.reload',{ignoreCache:true});
 await wait("document.querySelectorAll('.roster-item').length===4");await run('document.fonts.ready');
 assert.equal(await run("document.body.classList.contains('skyrim-font')"),true);
 assert.equal(await run("Array.from(document.fonts).some(f=>f.family==='AnimaSkyrimDialogue'&&f.status==='loaded')"),true);
 console.log('Actual Skyrim dialogue font loaded');
 for(const name of ['mira','elin','daren','iona']){
  await run(`document.querySelector('[data-id=${name}]').click()`);await wait(`profile.id==='${name}'&&document.getElementById('visual-status').textContent==='LOCAL 3D MODEL'&&!document.getElementById('expressions').disabled`);
  assert.equal(await run("document.querySelector('.stage-panel').dataset.scene"),name);
  const state=await run('stage.expressionState()');assert.ok(state.parts>=2);assert.ok('Aah' in state.weights);assert.ok('BlinkLeft' in state.weights);
  console.log(name,'native parts',state.parts,'scene selected');await shot('anima-native-'+name);
 }
 await run("document.querySelector('[data-id=mira]').click()");await wait("profile.id==='mira'&&stage.hasExpressions()");
 await wait('stage.expressionState().weights.BlinkLeft>.8');await shot('anima-native-blink');console.log('Native blink observed');
 await run("stage.setMood('angry')");await wait('stage.expressionState().weights.MoodAnger>.2');await shot('anima-native-angry');
 await run("document.getElementById('expressions').click()");assert.ok(Object.values((await run('stage.expressionState()')).weights).every(x=>x===0));
 await run("document.getElementById('expressions').click();document.getElementById('voice').checked=true;document.getElementById('message').value='Hello';document.getElementById('chat').requestSubmit()");await wait("pending===null&&!!document.getElementById('speech-player').getAttribute('src')");
 await run("document.getElementById('speech-player').currentTime=0;document.getElementById('speech-player').play()");await wait('stage.expressionState().weights.Aah>.1');await shot('anima-native-speaking');
 console.log('Actual Piper playback drives native speech morphs',JSON.stringify(await run('stage.expressionState().weights')));
 await run("document.getElementById('speech-player').pause()");await wait('stage.expressionState().weights.Aah===0');console.log('Speech motion resets when paused');
 await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});await wait('Object.values(stage.expressionState().weights).every(x=>x===0)');console.log('Reduced motion resets expressions');await call('Emulation.setEmulatedMedia',{features:[]});
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);await shot('anima-native-mobile');
 assert.deepEqual(errors,[]);console.log('No browser errors or mobile overflow');ws.close();
})().catch(e=>{console.error(e.message);process.exitCode=1;});
