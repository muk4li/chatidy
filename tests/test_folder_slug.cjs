// Browser-independent folder-URL regression: slug generation and ID-based canonicalization.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync(require('node:path').join(__dirname,'../web/app.js'),'utf8');
const start=script.indexOf('function folderSlug(');
const end=script.indexOf('function setView(',start);
assert(start>=0&&end>start);
let location={pathname:'/app/folders/4',search:'?q=test'};
const calls=[];
const context={folders:[{id:4,name:'Meine Projekte ÄÖÜ ß'}],location,
  history:{replaceState:(state,title,url)=>calls.push({state,title,url})}};
vm.createContext(context);
vm.runInContext(script.slice(start,end),context);
const slug=name=>vm.runInContext('folderSlug('+JSON.stringify(name)+')',context);
assert.equal(slug('Meine Projekte ÄÖÜ ß'),'meine-projekte-aeoeue-ss');
assert.equal(slug('   !!!   '),'ordner');
assert.equal(slug('Déjà vu!'),'deja-vu');
assert.equal(vm.runInContext('folderPath(4)',context),'/app/folders/4-meine-projekte-aeoeue-ss');
vm.runInContext('canonicalizeFolderPath(4)',context);
assert.deepEqual(calls,[{state:{},title:'',url:'/app/folders/4-meine-projekte-aeoeue-ss?q=test'}]);
context.folders[0].name='Neu benannt';
vm.runInContext('canonicalizeFolderPath(4)',context);
assert.deepEqual(calls[1],{state:{},title:'',url:'/app/folders/4-neu-benannt?q=test'});
context.location.pathname='/app/folders/4-neu-benannt';
vm.runInContext('canonicalizeFolderPath(4)',context);
assert.equal(calls.length,2);
console.log('PASS: readable folder URL slugs, rename and ID-only compatibility');
