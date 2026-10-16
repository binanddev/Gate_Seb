const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../teacher.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes=new Map(),calls=[];
function element(id){if(!nodes.has(id))nodes.set(id,{value:'',hidden:false,checked:false,disabled:false,textContent:'',children:[],addEventListener(name,fn){this[name]=fn;},append(child){this.children.push(child);},replaceChildren(){this.children=[];},select(){}});return nodes.get(id);}
let signed=false;
const draft={slug:'abc',title:'Toán',form_url:'https://docs.google.com/forms/d/e/demo/viewform',browser_exam_keys:'',enabled:false,start_url:'https://school.netlify.app/?exam=abc',opens_at:'',closes_at:''};
const context={console,URL,Date,Promise,Error,AbortController,setTimeout,clearTimeout,navigator:{clipboard:{writeText:async()=>{}}},
 document:{getElementById:element,querySelectorAll:()=>[],createElement:()=>({children:[],append(child){this.children.push(child);},addEventListener(){}})},addEventListener(){},
 fetch:async(path,options)=>{calls.push({path,options});let body={};
 if(path.endsWith('/account'))body={csrf:'csrf-initial',user:null};
 else if(path.endsWith('/register')){signed=true;body={csrf:'csrf-rotated',user:{username:'teacher'}};}
 else if(path.endsWith('/logout')){signed=false;body={csrf:'csrf-logged-out',user:null};}
 else if(path.endsWith('/exams'))body=options.method==='POST'?{exam:draft}:{exams:[]};
 return {ok:true,status:200,json:async()=>body};}};
context.window=context;vm.createContext(context);vm.runInContext(source,context);
async function flush(){for(let n=0;n<50;n++)await Promise.resolve();}
(async()=>{
 await flush();assert.equal(element('auth').hidden,false);
 element('toggleAuth').click();assert.equal(element('confirmPassword').required,true);
 element('username').value='teacher';element('password').value='example-password';element('confirmPassword').value='example-password';
 element('authForm').submit({preventDefault(){}});await flush();
 assert.equal(signed,true);assert.equal(element('dashboard').hidden,false);assert.equal(element('password').value,'');
 const registration=calls.find(c=>c.path.endsWith('/register'));assert.equal(registration.options.credentials,'same-origin');assert.equal(registration.options.headers['X-CSRFToken'],'csrf-initial');
 element('title').value='Toán';element('formUrl').value=draft.form_url;
 element('examForm').submit({preventDefault(){}});await flush();
 assert.equal(element('startUrl').value,draft.start_url);assert.equal(element('configuration').hidden,false);
 const create=calls.find(c=>c.path.endsWith('/exams')&&c.options.method==='POST');assert.equal(create.options.headers['X-CSRFToken'],'csrf-rotated');
 element('logout').click();await flush();assert.equal(element('dashboard').hidden,true);assert.equal(element('bek').value,'');
 console.log('Teacher UI flow passed: register, CSRF rotation, draft Start URL, logout.');
})().catch(error=>{console.error(error);process.exitCode=1;});
