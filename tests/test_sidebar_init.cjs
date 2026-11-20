// Regression: execute the actual sidebar-initialization code without a browser
// so this fails in required CI if any non-collapsible account panel breaks startup.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const app=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
assert.match(html,/id="account-panel" class="account-panel"/);
const first=app.indexOf("const closedSections=new Set(");
const last=app.indexOf("// Resizable navigation",first);
assert(first>=0&&last>first,'sidebar initializer must be present');
const code=app.slice(first,last);
const controlled={hidden:true};
const toggle={
  attr:{},
  getAttribute(name){assert.equal(name,'aria-controls');return 'folders'},
  setAttribute(name,value){this.attr[name]=value},
};
const collapsible={dataset:{section:'folders'},querySelector:selector=>{
  assert.equal(selector,'.sectiontoggle');return toggle;
}};
const account={dataset:{},querySelector:()=>null};
const writes=[];
vm.runInNewContext(code,{
  $(id){assert.equal(id,'folders');return controlled},
  document:{
    querySelectorAll(selector){assert.equal(selector,'.navsection');return [collapsible,account]},
    getElementById(id){assert.equal(id,'folders');return controlled}
  },
  store:{
    get(name,fallback){assert.equal(name,'chatidy-closed-sections');return fallback},
    set(name,value){writes.push({name,value:[...value]})}
  }
});
assert.equal(controlled.hidden,false,'functional folder section must be visible');
assert.equal(toggle.attr['aria-expanded'],'true');
toggle.onclick();
assert.equal(controlled.hidden,true,'toggle must still collapse folder section');
assert.equal(toggle.attr['aria-expanded'],'false');
assert.deepEqual(writes,[{name:'chatidy-closed-sections',value:['folders']}]);
console.log('PASS: sidebar initializes with a non-collapsible account panel');
