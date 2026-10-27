// Isolated behavioral tests: no Google requests and no fabricated real SEB claims.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function harness({query='?exam=math&challenge=demo', seb=true, fetcher} = {}) {
  const elements = new Map(), timers = new Map(), listeners = {}, calls = [];
  let id=0;
  const element = name => {
    if (!elements.has(name)) elements.set(name, {hidden:false,textContent:'',src:'',addEventListener(event, fn){this[event]=fn;}});
    return elements.get(name);
  };
  const context = {URL, URLSearchParams, AbortController, Date, Math, Promise, Error, console,
    document:{readyState:'complete',getElementById:element,hidden:false,addEventListener:(name,fn)=>listeners[name]=fn},
    location:{search:query,href:'https://school.netlify.app/'+query,replace(url){context.redirect=url;}},
    setTimeout(fn, ms){timers.set(++id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);},
    confirm:()=>true,
    fetch:async (url, options)=>{calls.push({url,options});return fetcher ? fetcher(url, options) : response(url);},
    addEventListener:(name,fn)=>{const old=listeners[name];listeners[name]=old ? (...args)=>{old(...args);fn(...args);} : fn;},removeEventListener:()=>{}};
  function response(url) {
    const data = url.endsWith('/api/verify') ? {session:'session-token',title:'Toán',form_url:'https://docs.google.com/forms/d/e/demo/viewform?usp=sharing&entry.123=abc',heartbeat_seconds:240} : {status:'ready',page_url:'https://school.netlify.app/?exam=math&challenge=new'};
    return {ok:true,status:200,json:async()=>data};
  }
  context.window=context;
  if(seb) context.SafeExamBrowser={security:{browserExamKey:'a'.repeat(64)}};
  vm.createContext(context);vm.runInContext(source,context);
  return {context,elements,timers,listeners,calls,element,response};
}
async function flush(){for(let i=0;i<30;i++)await Promise.resolve();}
(async()=>{
  let h=harness();await flush();
  assert.equal(h.context.redirect,'https://docs.google.com/forms/d/e/demo/viewform?usp=sharing&entry.123=abc');
  assert.equal(h.timers.size,0);
  assert.deepEqual(h.calls.map(c=>c.url),['/api/verify']);
  assert.equal(h.calls.some(c=>c.url.endsWith('/api/heartbeat')),false);
  h.listeners.pagehide();assert.equal(h.timers.size,0);

  h=harness({seb:false});await flush();
  [...h.timers.values()].find(t=>t.ms===10000).fn();await flush();
  assert.equal(h.context.redirect,undefined);assert.match(h.element('message').textContent,/Không thể xác minh/);
  assert.equal(h.calls.some(c=>c.url.endsWith('/api/verify')),false);

  // SEB can inject its API after the inline script has already run.
  h=harness({seb:false});await flush();
  assert.equal(h.calls.length,0);
  h.context.SafeExamBrowser={security:{browserExamKey:'b'.repeat(64)}};
  [...h.timers.values()].find(t=>t.ms===100).fn();await flush();
  assert.match(h.context.redirect,/docs.google.com/);
  assert.equal(h.timers.size,0);

  // updateKeys must wait for load and may return asynchronously.
  h=harness({seb:false});h.context.document.readyState='loading';
  let callback, updates=0;
  h.context.SafeExamBrowser={security:{updateKeys(fn){updates++;callback=fn;}}};
  [...h.timers.values()].find(t=>t.ms===100).fn();await flush();
  assert.equal(updates,0);
  h.context.document.readyState='complete';
  [...h.timers.values()].find(t=>t.ms===100).fn();await flush();
  assert.equal(updates,1);
  h.context.SafeExamBrowser.security.browserExamKey='c'.repeat(64);callback();await flush();
  assert.match(h.context.redirect,/docs.google.com/);assert.equal(h.timers.size,0);

  h=harness({seb:false});await flush();h.listeners.pagehide();await flush();
  assert.equal(h.timers.size,0);assert.equal(h.calls.length,0);

  h=harness({fetcher:async()=>{throw new TypeError('offline');}});await flush();
  assert.match(h.element('message').textContent,/Đang gọi backend/);
  assert.equal([...h.timers.values()].some(t=>t.ms===8000),true);
  assert.equal(h.context.redirect,undefined);h.listeners.pagehide();assert.equal(h.timers.size,0);

  h=harness({fetcher:async()=>({ok:false,status:503,json:async()=>{throw new Error('HTML startup page');}})});await flush();
  assert.match(h.element('message').textContent,/Đang gọi backend/);

  h=harness({fetcher:async url=>url.endsWith('/api/verify')?{ok:false,status:403,json:async()=>({error:'Sai cấu hình'})}:{ok:true,status:200,json:async()=>({status:'ready'})}});await flush();
  assert.equal(h.context.redirect,undefined);assert.equal(h.element('detail').textContent,'Sai cấu hình');

  h=harness({query:'?exam=math'});await flush();
  assert.equal(h.context.redirect,'https://school.netlify.app/?exam=math&challenge=new');

  let resolveVerification;
  h=harness({fetcher:async url=>url.endsWith('/api/verify')?new Promise(resolve=>{resolveVerification=resolve;}):{ok:true,status:200,json:async()=>({status:'ready'})}});
  await flush();h.listeners.pagehide();
  resolveVerification({ok:true,status:200,json:async()=>({form_url:'https://docs.google.com/forms/d/e/demo/viewform'})});
  await flush();assert.equal(h.context.redirect,undefined);
  for(const status of [200,404]) {
    h=harness({fetcher:async()=>({ok:status===200,status,json:async()=>{throw new Error('HTML instead of API');}})});
    await flush();assert.equal(h.context.redirect,undefined);assert.equal(h.timers.size,0);
    assert.match(h.element('detail').textContent,/proxy/);
  }
  h=harness({fetcher:async()=>({ok:true,status:200,json:async()=>({})})});
  await flush();assert.equal(h.context.redirect,undefined);assert.equal(h.timers.size,0);
  h=harness({fetcher:async()=>{throw new TypeError('offline');}});await flush();
  for(let n=1;n<6;n++) {const [id,timer]=[...h.timers.entries()].find(([,t])=>t.ms===8000);h.timers.delete(id);timer.fn();await flush();}
  assert.equal(h.timers.size,0);assert.equal(h.element('retry').hidden,false);
  assert.match(h.element('message').textContent,/Không kết nối/);
  console.log('Gateway tests passed: same-origin API, immediate redirect, failures, proxy errors, bounded retries.');
})().catch(error=>{console.error(error);process.exitCode=1;});
