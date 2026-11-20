// Synthetic unit tests for web/reading.js (run via tests/test_reading_view.py or `node`).
const assert=require('node:assert/strict');
const path=require('node:path');
const {readingItems}=require(path.join(__dirname,'..','web','reading.js'));

const msg=(id,role,content,meta)=>({id,role,content,metadata:meta===undefined?{}:meta});
const thoughts=(steps)=>({source:'chatgpt',content:{content_type:'thoughts',thoughts:steps}});
const recap=(text)=>({source:'chatgpt',content:{content_type:'reasoning_recap',content:text}});
const P='[Nicht-textueller Inhalt]';

// Normal messages pass through unchanged and in order.
let items=readingItems([msg('a','user','Frage'),msg('b','assistant','Antwort',{content:{content_type:'text'}})]);
assert.deepEqual(items.map(x=>x.kind),['message','message']);
assert.equal(items[1].message.id,'b');

// Thoughts followed by recap become one block labelled with the recap text.
items=readingItems([msg('a','user','Frage'),
  msg('t','assistant',P,thoughts([{summary:'Plan',content:'Erst A',chunks:[]},{summary:'Prüfen',content:'',chunks:['B','C']},{summary:'Leer',content:'',chunks:[]}])),
  msg('r','assistant',P,recap('Nachgedacht für 12s')),
  msg('b','assistant','Antwort')]);
assert.deepEqual(items.map(x=>x.kind),['message','thinking','message']);
assert.equal(items[1].label,'Nachgedacht für 12s');
assert.deepEqual(items[1].steps,[{title:'Plan',text:'Erst A'},{title:'Prüfen',text:'B\nC'},{title:'Leer',text:''}]);
assert.deepEqual(items[1].messages.map(m=>m.id),['t','r'],'raw source messages kept for metadata view');

// Standalone recap and thoughts without recap get their own block; default label.
items=readingItems([msg('r','assistant',P,recap('Nachgedacht')),msg('t','assistant',P,thoughts([]))]);
assert.deepEqual(items.map(x=>[x.kind,x.label,x.steps.length]),[['thinking','Nachgedacht',0],['thinking','Denkprozess',0]]);

// Malformed metadata never throws and never hides a message.
items=readingItems([msg('x','assistant','T',null),msg('y','assistant','T',{content:'text'}),
  msg('z','assistant',P,{content:{content_type:'thoughts',thoughts:'kaputt'}}),
  msg('w','assistant',P,{content:{content_type:'thoughts',thoughts:[null,{summary:5,content:7,chunks:[1,'ok']}]}})]);
assert.deepEqual(items.map(x=>x.kind),['message','message','thinking','thinking']);
assert.deepEqual(items[3].steps,[{title:'',text:'ok'}]);
assert.deepEqual(readingItems(undefined),[]);

// Values from export data are returned as plain strings only (rendered via textContent).
items=readingItems([msg('h','assistant',P,thoughts([{summary:'<img src=x onerror=alert(1)>',content:'<b>x</b>'}]))]);
assert.equal(items[0].steps[0].title,'<img src=x onerror=alert(1)>');

console.log('reading_view: ok');
