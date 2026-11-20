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

// Claude activity blocks (PROV-002b)
{
  const {claudeActivity}=require(path.join(__dirname,'..','web','reading.js'));
  const claude=(id,content,blocks)=>({id,role:'assistant',content,metadata:{source:'claude',content:blocks}});
  const blocks=[{type:'thinking',thinking:'',thinking_hidden:true},{type:'tool_use',name:'web_search',input:{query:'secret'}},
    {type:'tool_result',content:[{type:'text',text:'https://example.invalid'}],is_error:false},
    {type:'tool_use',name:'web_search'},{type:'tool_result',is_error:true},{type:'tool_use',name:''},
    {type:'thinking',thinking:'Synthetic thought'},{type:'injected_prompt_block'},{type:'text',text:'Visible'}];
  const activity=claudeActivity(claude('a','Visible',blocks));
  assert.deepEqual(activity.tools,['web_search','web_search','Werkzeug']);
  assert.equal(activity.results,2);assert.equal(activity.errors,1);
  assert.deepEqual(activity.thinking,['Synthetic thought']);assert.deepEqual(activity.other,['injected_prompt_block']);
  assert.equal(activity.label,'🔧 3 Werkzeugaufrufe (web_search, Werkzeug) · ⚠ 1 Fehler · 💭 Denkprozess · ▫ injected_prompt_block');
  assert(!JSON.stringify(activity).includes('secret')&&!JSON.stringify(activity).includes('example.invalid'),'no tool inputs/outputs or URLs');
  // Text + tools → message with attached activity; tool-only placeholder → activity item.
  const items=readingItems([claude('a','Visible',blocks),claude('b',P,[{type:'tool_use',name:'bash'}]),
    claude('c','Only text',[{type:'text',text:'Only text'},{type:'thinking',thinking:''}]),
    {id:'g',role:'assistant',content:'x',metadata:{source:'chatgpt',content:[{type:'tool_use'}]}}]);
  assert.deepEqual(items.map(x=>x.kind),['message','activity','message','message']);
  assert(items[0].activity);assert.equal(items[1].activity.label,'🔧 1 Werkzeugaufruf (bash)');
  assert.equal(items[2].activity,null,'empty hidden thinking alone adds nothing');
  assert.equal(items[3].activity,null,'only Claude metadata is interpreted');
  // Placeholder without recognizable blocks stays a normal message (nothing hidden).
  assert.equal(readingItems([claude('d',P,[])])[0].kind,'message');
  console.log('reading_view claude: ok');
}

// Visible message count (thinking/tool-only nodes excluded)
{
  const {visibleMessageCount}=require(path.join(__dirname,'..','web','reading.js'));
  assert.equal(visibleMessageCount([{content:'a'},{content:P},{content:'b'},null]),2);
  assert.equal(visibleMessageCount(undefined),0);
  console.log('reading_view count: ok');
}
