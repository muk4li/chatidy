'use strict';
const $=id=>document.getElementById(id);
let view='all',folder=null,folders=[],chats=[],selected=null,offset=0,loading=false,searchTimer=null,details=null;
const PAGE=100;
async function api(path,options={}){
  const res=await fetch(path,options);const body=await res.json();
  if(!res.ok)throw new Error(body.error||'Anfrage fehlgeschlagen');return body;
}
function post(path,payload){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})}
function message(text,error=false){const node=$('notice');node.textContent=text;node.hidden=!text;node.style.borderColor=error?'#c36d95':'#584268'}
function element(tag,className='',text){const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e}
function button(label,fn,cls='soft'){const e=element('button',cls,label);e.type='button';e.onclick=fn;return e}
function field(label,value='',type='text'){const wrapper=element('label');wrapper.append(document.createTextNode(label));const input=element('input');input.type=type;input.value=value;wrapper.append(input);return {wrapper,input}}
function select(label,choices,value=''){const wrapper=element('label');wrapper.append(document.createTextNode(label));const menu=element('select');for(const [id,name] of choices){const op=new Option(name,String(id));menu.add(op)}menu.value=String(value??'');wrapper.append(menu);return {wrapper,input:menu}}
function modal(title,contents,onSave,saveLabel='Speichern'){
  $('modal-title').textContent=title;const root=$('modal-content');root.replaceChildren();
  for(const content of contents)root.append(content);
  $('modal-confirm').textContent=saveLabel;
  const dialog=$('modal');dialog.onclose=async()=>{
    if(dialog.returnValue!=='ok')return;
    try{await onSave();await refresh();message('Änderung gespeichert.')}
    catch(e){message(e.message,true)}
  };
  dialog.showModal();
}
function currentName(){if(folder!==null)return folders.find(f=>f.id===folder)?.name||'Ordner';return ({all:'Alle Gespräche',inbox:'Posteingang',archived:'Archivierte Gespräche',unfiled:'Ohne Gruppe'})[view]}
function setView(v,id=null){view=v;folder=id;offset=0;selected=null;details=null;renderSidebar();renderDetail();loadChats()}
async function loadFolders(){folders=await api('/api/folders');$('stat-folders').textContent=folders.length;renderSidebar()}
function renderSidebar(){
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',folder===null&&view===b.dataset.view));
  const nav=$('folders');nav.replaceChildren();
  function walk(parent,depth,seen){
    if(depth>15)return;
    for(const f of folders.filter(x=>x.parent_id===parent)){
      if(seen.has(f.id))continue;
      const b=button('',()=>setView('all',f.id),'folderbtn'+(folder===f.id?' active':''));
      b.style.paddingLeft=(12+depth*13)+'px';const name=element('span','','▤ '+f.name);
      const count=element('small','',String(f.item_count));b.append(name,count);b.title='Ordner öffnen: '+f.name;
      nav.append(b);walk(f.id,depth+1,new Set([...seen,f.id]));
    }
  }walk(null,0,new Set());
}
async function loadStats(){const stats=await api('/api/stats');for(const key of ['chats','messages','folders','inbox'])$('stat-'+key).textContent=Number(stats[key]||0).toLocaleString('de-DE');$('count-all').textContent=stats.chats;$('count-inbox').textContent=stats.inbox}
function date(value){if(!value)return 'Ohne Datum';const number=Number(value);const d=new Date(number<1e11?number*1000:number);return isNaN(d)?'Ohne Datum':d.toLocaleDateString('de-DE')}
async function loadChats(append=false){
  if(loading)return;loading=true;
  try{
    const params=new URLSearchParams();if($('search').value.trim())params.set('q',$('search').value.trim());
    if(folder!==null)params.set('folder',folder);else params.set('mode',view);
    params.set('limit',PAGE);params.set('offset',append?offset:0);
    const result=await api('/api/chats?'+params);
    if(append){chats.push(...result);offset+=result.length}else{chats=result;offset=result.length}
    $('view-title').textContent=currentName();$('results-label').textContent=chats.length+' Ergebnisse geladen';
    $('more').hidden=result.length<PAGE;renderChats();
  }catch(e){message('Suche fehlgeschlagen: '+e.message,true)}finally{loading=false}
}
function renderChats(){
  const list=$('chat-list');list.replaceChildren();
  if(!chats.length){list.append(element('div','empty','Noch keine Chats in dieser Ansicht. Importiere einen Export oder passe die Filter an.'));return}
  for(const chat of chats){
    const b=button('',()=>showChat(chat.id),'chat-card'+(chat.id===selected?' selected':''));
    b.append(element('div','chat-title',chat.title||'Ohne Titel'));
    const meta=element('div','chat-meta');meta.append(element('span','',date(chat.updated||chat.created)));
    meta.append(element('span','',chat.message_count+' Nachrichten'));
    if(chat.groups_count)meta.append(element('span','pill',chat.groups_count+' Gruppen'));
    if(!chat.reviewed)meta.append(element('span','pill','Neu'));
    b.append(meta);list.append(b);
  }
}
function renderDetail(){
  const detail=$('detail');detail.replaceChildren();
  if(!details){const blank=element('div','empty detail-empty');blank.append(element('div','empty-icon','✦'),element('strong','','Dein Wissen ist hier.'),element('p','','Wähle einen Chat, um den Verlauf und seine Gruppen zu sehen.'));detail.append(blank);return}
  const c=details.chat;detail.append(element('h2','',c.title),element('div','muted',(c.project?'Projekt: '+c.project+' · ':'')+details.messages.length+' Nachrichten · '+date(c.updated||c.created)));
  const chips=element('div','chipbox');for(const id of details.folders){const f=folders.find(x=>x.id===id);if(f)chips.append(element('span','chip',f.name))}detail.append(chips);
  const actions=element('div','detail-actions');
  actions.append(button('▤ Gruppen bearbeiten',()=>editGroups(c.id)));
  actions.append(button('✦ KI-Kategorien',()=>suggest(c.id)));
  actions.append(button(c.reviewed?'↺ Erneut prüfen':'✓ Geprüft',async()=>{
    try{await post('/api/review',{conversation_id:c.id,reviewed:!c.reviewed});await refresh();await showChat(c.id)}catch(e){message(e.message,true)}
  }));
  actions.append(button('↓ Chat exportieren',()=>exportChats([c.id])));
  detail.append(actions);
  if(details.suggestions.length){
    const info=element('div','notice','KI-Vorschläge: '+details.suggestions.map(x=>folders.find(f=>f.id===x.folder_id)?.name||x.folder_id).join(', ')+' – bitte in Gruppen bearbeiten bestätigen.');
    detail.append(info);
  }
  for(const m of details.messages){
    const box=element('div','bubble '+(m.role==='user'?'user':'assistant'));
    box.append(element('div','role',m.role==='user'?'DU':m.role==='assistant'?'ASSISTENT':'TOOL'));
    box.append(document.createTextNode(m.content));detail.append(box);
  }
}
async function showChat(id){selected=id;try{details=await api('/api/chat/'+encodeURIComponent(id));renderChats();renderDetail();$('detail').scrollTop=0}catch(e){message(e.message,true)}}
function editGroups(cid){
  if(!details)return;
  const list=element('div');
  const chosen=new Set(details.folders);
  for(const f of folders){
    const label=element('label','check');const input=element('input');input.type='checkbox';input.checked=chosen.has(f.id);
    input.onchange=()=>input.checked?chosen.add(f.id):chosen.delete(f.id);
    label.append(input,document.createTextNode(f.name));list.append(label);
  }
  modal('Chat zu Gruppen zuordnen',[element('p','muted','Mehrfachauswahl ist möglich. Zuordnungen bleiben nach erneutem Import erhalten.'),list],async()=>{
    await post('/api/assign',{conversation_id:cid,folder_ids:[...chosen]});await showChat(cid)
  },'Zuordnung bestätigen');
}
function createFolder(){
  const name=field('Ordnername');const parent=select('Übergeordneter Ordner',[['','Hauptverzeichnis'],...folders.map(f=>[f.id,f.name])],folder??'');
  const controls=element('div','actionrow');
  if(folder!==null){
    controls.append(button('Aktuellen Ordner umbenennen',()=>{const current=folders.find(f=>f.id===folder);if(!current)return;
      const label=field('Neuer Name',current.name);
      modal('Ordner umbenennen',[label.wrapper],async()=>post('/api/folders/update',{id:current.id,name:label.input.value}))}));
    controls.append(button('Ordner löschen',async()=>{if(!confirm('Ordner und Unterordner wirklich löschen? Chat-Inhalte bleiben erhalten.'))return;
      try{await post('/api/folders/delete',{id:folder});setView('all');await refresh()}catch(e){message(e.message,true)}}));
  }
  modal('Neuer Ordner',[name.wrapper,parent.wrapper,controls],async()=>post('/api/folders',{name:name.input.value,parent_id:parent.input.value?Number(parent.input.value):null}),'Ordner anlegen');
}
async function rulesModal(){
  let list=[];try{list=await api('/api/rules')}catch(e){message(e.message,true)}
  const fieldType=select('Suchfeld',[['title','Titel'],['content','Nachrichteninhalt'],['project','Projekt']]);
  const word=field('Enthaltenes Stichwort');const target=select('Zielgruppe',folders.map(f=>[f.id,f.name]));
  const entries=element('div');
  entries.append(element('strong','','Bestehende Regeln'));
  if(!list.length)entries.append(element('p','muted','Noch keine Regeln.'));
  for(const rule of list){
    const row=element('div','detail-actions');row.append(element('span','muted',rule.field+' enthält "'+rule.needle+'" → '+(folders.find(f=>f.id===rule.folder_id)?.name||'?')));
    row.append(button('Entfernen',async()=>{if(!confirm('Regel entfernen? Bestehende Zuordnungen bleiben erhalten.'))return;try{await post('/api/rules/delete',{id:rule.id});await refresh();message('Regel entfernt.')}catch(e){message(e.message,true)}}));
    entries.append(row);
  }
  modal('Automatische Sortierung',[fieldType.wrapper,word.wrapper,target.wrapper,entries],async()=>{
    await post('/api/rules',{field:fieldType.input.value,needle:word.input.value,folder_id:Number(target.input.value)})
  },'Regel erstellen');
}
async function suggest(cid){
  if(!confirm('Sollen Titel und bis zu 6.000 Zeichen dieses Chats an Ollama auf deinem eigenen Rechner (127.0.0.1:11434) gesendet werden? Es entstehen nur Vorschläge, keine automatische Zuordnung.'))return;
  message('Lokale KI erstellt Vorschläge …');
  try{const result=await post('/api/ai/suggest',{ids:[cid]});const suggestions=result.suggestions[0]?.folder_ids||[];
    await showChat(cid);message(suggestions.length?'Vorgeschlagene Gruppen: '+suggestions.map(id=>folders.find(f=>f.id===id)?.name||id).join(', '):'Keine passenden Gruppen gefunden.');
  }catch(e){message(e.message,true)}
}
function exportChats(ids=null){
  post('/api/export',{ids}).then(data=>{
    const blob=new Blob([JSON.stringify(data.exported,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=element('a');a.href=url;a.download='chatidy-export.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    message(data.exported.length+' Chats als JSON exportiert.');
  }).catch(e=>message(e.message,true));
}
async function refresh(){await Promise.all([loadFolders(),loadStats()]);await loadChats()}
async function importFile(file){
  if(!file)return;
  if(!/\.(json|zip)$/i.test(file.name)){message('Bitte eine ZIP- oder JSON-Datei auswählen.',true);return}
  if(file.size>200*1024*1024){message('Datei zu groß (maximal 200 MB).',true);return}
  message('Import läuft lokal …');$('pick-file').disabled=true;
  try{const result=await api('/api/import',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Filename':file.name.replace(/[^a-zA-Z0-9_.-]/g,'_')},body:file});
    setView('all');await refresh();message(result.imported+' Chat(s) importiert. Bereits vorhandene Gruppenzuordnungen bleiben erhalten.');
  }catch(e){message('Import fehlgeschlagen: '+e.message,true)}finally{$('pick-file').disabled=false}
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
$('new-folder').onclick=createFolder;$('new-rule').onclick=rulesModal;$('export').onclick=()=>exportChats();
$('refresh').onclick=refresh;$('more').onclick=()=>loadChats(true);$('clear').onclick=()=>{$('search').value='';loadChats()};
$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{offset=0;loadChats()},250)};
$('pick-file').onclick=()=>$('file-input').click();$('file-input').onchange=e=>importFile(e.target.files[0]);
const drop=$('dropzone');for(const type of ['dragenter','dragover'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('drag')});
for(const type of ['dragleave','drop'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('drag')});
drop.addEventListener('drop',e=>importFile(e.dataTransfer.files[0]));
refresh().catch(e=>message('Startfehler: '+e.message,true));
