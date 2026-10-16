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
    document:{getElementById:element,hidden:false,addEventListener:(name,fn)=>listeners[name]=fn},
    location:{search:query,href:'https://school.netlify.app/'+query,replace(url){context.redirect=url;}},
    setTimeout(fn, ms){timers.set(++id,{fn,ms});return id;},clearTimeout(id){timers.delete(id);},
    confirm:()=>true,
    fetch:async (url, options)=>{calls.push({url,options});return fetcher ? fetcher(url, options) : response(url);},
    addEventListener:(name,fn)=>listeners[name]=fn};
  function response(url) {
    const data = url.endsWith('/api/verify') ? {session:'session-token',title:'Toán',form_url:'https://docs.google.com/forms/d/e/demo/viewform?embedded=true',heartbeat_seconds:240} : {status:'ready',page_url:'https://school.netlify.app/?exam=math&challenge=new'};
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
  assert.equal(h.element('form').src.includes('embedded=true'),true);
  assert.equal([...h.timers.values()].some(t=>t.ms===240000),true);
  h.listeners.pagehide();assert.equal(h.timers.size,0);

  h=harness({seb:false});await flush();
  assert.equal(h.element('form').src,'');assert.match(h.element('message').textContent,/Không thể xác minh/);
  assert.equal(h.calls.some(c=>c.url.endsWith('/api/verify')),false);

  h=harness({fetcher:async()=>{throw new TypeError('offline');}});await flush();
  assert.match(h.element('message').textContent,/Đang gọi backend/);
  assert.equal([...h.timers.values()].some(t=>t.ms===8000),true);
  assert.equal(h.element('form').src,'');h.listeners.pagehide();assert.equal(h.timers.size,0);

  h=harness({fetcher:async()=>({ok:false,status:503,json:async()=>{throw new Error('HTML startup page');}})});await flush();
  assert.match(h.element('message').textContent,/Đang gọi backend/);

  h=harness({fetcher:async url=>url.endsWith('/api/verify')?{ok:false,status:403,json:async()=>({error:'Sai cấu hình'})}:{ok:true,status:200,json:async()=>({status:'ready'})}});await flush();
  assert.equal(h.element('form').src,'');assert.equal(h.element('detail').textContent,'Sai cấu hình');

  h=harness({query:'?exam=math'});await flush();
  assert.equal(h.context.redirect,'https://school.netlify.app/?exam=math&challenge=new');

  h=harness();await flush();const form=h.element('form').src;
  h.context.fetch=async()=>{throw new TypeError('offline');};
  await vm.runInContext('heartbeat()',h.context);await flush();
  assert.equal(h.element('form').src,form);assert.equal(h.element('warning').hidden,false);
  assert.equal([...h.timers.values()].some(t=>t.ms>=15000&&t.ms<20000),true);
  h.element('finish').click();assert.equal(h.timers.size,0);assert.equal(h.element('finish').disabled,true);
  console.log('7 frontend scenarios passed: entry, non-SEB, offline, cold start, rejection, challenge, heartbeat/stop.');
})().catch(error=>{console.error(error);process.exitCode=1;});
