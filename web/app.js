'use strict';
const $=id=>document.getElementById(id);
let view='all',folder=null,folders=[],chats=[],selected=null,offset=0,loading=false,searchTimer=null,details=null;
const PAGE=100;
let chosen=new Set(),smartFolders=[],smart=null,loadEpoch=0,tags=[],page='library';
let sourceFilter='',sourceCounts={};
const store={get(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v)}catch{return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch{}}};
let collapsed=new Set(store.get('chatidy-collapsed-folders',[]));
function showPage(name,skipHistory=false){
  if(!skipHistory)pushRoute(name==='import'?'/app/import':'/app');
  page=name;$('import-page').hidden=name!=='import';$('library-page').hidden=name!=='library';document.body.classList.toggle('page-import',name==='import');
  if(name==='import')closeReader();
  renderSidebar();
}
function closeReader(){document.body.classList.remove('reading')}
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
function currentName(){if(smart!==null)return smartFolders.find(f=>f.id===smart)?.name||'Intelligenter Ordner';if(folder!==null)return folders.find(f=>f.id===folder)?.name||'Ordner';return ({all:'Alle Gespräche',inbox:'Posteingang',archived:'Archivierte Gespräche',unfiled:'Ohne Gruppe',topics:'Themencluster'})[view]}
function setView(v,id=null,{keepTag=false,skipHistory=false}={}){
  if(!keepTag)$('tag-filter').value='';
  page='library';$('import-page').hidden=true;$('library-page').hidden=false;
  document.body.classList.remove('page-import');smart=null;
  $('search').disabled=false;$('tag-filter').disabled=false;
  chosen.clear();renderSelection();view=v;folder=id;offset=0;selected=null;details=null;
  if(!skipHistory)pushRoute(id!==null?'/app/folders/'+id:
    ({inbox:'/app/inbox',archived:'/app/archive',unfiled:'/app/unfiled',topics:'/app/topics'})[v]||'/app');
  renderSidebar();renderDetail();loadChats()
}
async function loadFolders(){
  folders=await api('/api/folders');$('stat-folders').textContent=folders.length;
  const target=$('bulk-folder'),current=target.value;target.replaceChildren(new Option('Zielordner wählen',''));
  for(const f of folders)target.add(new Option(f.name,String(f.id)));target.value=current;renderSidebar();
}
async function loadOrganisation(){
  const [tagResult,smartResult]=await Promise.all([api('/api/tags'),api('/api/smart-folders')]);smartFolders=smartResult;tags=tagResult;
  const target=$('tag-filter'),current=target.value;target.replaceChildren(new Option('Alle Tags',''));
  for(const tag of tags)target.add(new Option(tag.name+' ('+tag.count+')',tag.name));target.value=current;
  renderSidebar();
}
function setSmart(id,skipHistory=false){
  const item=smartFolders.find(f=>f.id===id);if(!item)return;
  page='library';$('import-page').hidden=true;$('library-page').hidden=false;document.body.classList.remove('page-import');
  smart=id;folder=null;view='all';offset=0;chosen.clear();selected=null;details=null;
  $('search').value=item.query.q||'';$('search').disabled=true;$('tag-filter').value=item.query.tag||'';$('tag-filter').disabled=true;
  if(!skipHistory)pushRoute('/app/smart/'+id);
  renderSelection();renderSidebar();renderDetail();loadChats();
}
function renderSelection(){
  $('selected-count').textContent=chosen.size+' ausgewählt';
  $('bulk-assign').disabled=$('bulk-tags').disabled=!chosen.size;
  $('select-loaded').checked=chats.length>0&&chats.slice(0,500).every(c=>chosen.has(c.id));
}
async function assignChats(ids,target){
  if(!target){message('Bitte einen Zielordner wählen.',true);return}
  if(!confirm(ids.length+' Chats zusätzlich diesem Ordner zuordnen?'))return;
  try{await post('/api/bulk/assign',{conversation_ids:ids,folder_id:Number(target)});chosen.clear();await refresh();renderSelection();message('Chats zugeordnet.')}
  catch(e){message(e.message,true)}
}
function editTags(ids,replace=false){
  const existing=replace?(details?.tags||[]):[];const tags=field('Tags, durch Komma getrennt',existing.join(', '));
  modal(replace?'Tags bearbeiten':'Tags zur Auswahl hinzufügen',[tags.wrapper],async()=>{
    const names=tags.input.value.split(',').map(t=>t.trim()).filter(Boolean);
    if(replace)await post('/api/tags/set',{conversation_id:ids[0],tags:names});
    else await post('/api/bulk/tags',{conversation_ids:ids,tags:names});
    if(selected)await showChat(selected);
    await loadOrganisation();
  },'Tags übernehmen');
}
const PROVIDER_LABELS={chatgpt:'ChatGPT',claude:'Claude'};
const SOURCE_LABELS={chatgpt:'ChatGPT',codex:'Codex',claude:'Claude',claude_code:'Claude Code',extractor:'Extractor'};
let providers={},providerFilter='';
function providerLabel(id){return PROVIDER_LABELS[id]||String(id||'Unbekannt')}
function renderProviders(){
  const nav=$('provider-list');nav.replaceChildren();
  const ids=Object.keys(providers);
  $('provider-section').hidden=ids.length<2&&!providerFilter;
  for(const id of ids){
    const active=providerFilter===id;
    const b=button(providerLabel(id),()=>{if(smart!==null)return;providerFilter=active?'':id;setView('all',null,{keepTag:true})},'tagbtn'+(active?' active':''));
    b.append(element('small','',Number(providers[id]).toLocaleString('de-DE')));b.title='Nach Anbieter filtern: '+providerLabel(id);nav.append(b);
  }
}
function renderSources(){
  const nav=$('source-list');nav.replaceChildren();
  for(const id of ['chatgpt','codex','claude','claude_code','extractor']){
    const count=Number(sourceCounts[id]||0);
    if(!count&&sourceFilter!==id)continue; // Claude Code only if explicitly identifiable.
    const active=sourceFilter===id;
    const b=button(SOURCE_LABELS[id],()=>{
      sourceFilter=active?'':id;
      setView('all',null,{keepTag:true})
    },'tagbtn'+(active?' active':''));
    b.append(element('small','',count.toLocaleString('de-DE')));
    b.title='Nach Quelle filtern: '+SOURCE_LABELS[id];nav.append(b);
  }
  $('source-section').hidden=!nav.childElementCount;
}
function routeQuery(){
  const params=new URLSearchParams();
  if($('search').value.trim())params.set('q',$('search').value.trim());
  if($('tag-filter').value)params.set('tag',$('tag-filter').value);
  if(providerFilter)params.set('provider',providerFilter);
  if(sourceFilter)params.set('source',sourceFilter);
  if($('date-from').value)params.set('from',$('date-from').value);
  if($('date-to').value)params.set('to',$('date-to').value);
  if($('undated').checked)params.set('undated','1');
  if($('date-sort').value!=='newest')params.set('sort',$('date-sort').value);
  return params.toString()
}
function pushRoute(path,replace=false){
  const query=path.startsWith('/app')&&path!=='/app/import'?routeQuery():'';
  const target=path+(query?'?'+query:'');
  if(location.pathname+location.search===target)return;
  history[replace?'replaceState':'pushState']({},'',target)
}
function syncRouteQuery(){
  const path=location.pathname.startsWith('/app')?location.pathname:'/app';
  pushRoute(path,true)
}
function restoreFilters(){
  const q=new URLSearchParams(location.search);
  $('search').value=q.get('q')||'';
  $('tag-filter').value=q.get('tag')||'';
  providerFilter=q.get('provider')||'';
  sourceFilter=q.get('source')||'';
  $('date-from').value=q.get('from')||'';
  $('date-to').value=q.get('to')||'';
  $('undated').checked=q.get('undated')==='1';
  $('date-sort').value=q.get('sort')==='oldest'?'oldest':'newest';
  updateUndatedControls()
}
function applyRoute(){
  restoreFilters();
  const path=location.pathname;
  if(path==='/app/import'){showPage('import',true);loadJobs();return}
  if(path==='/app/inbox'){setView('inbox',null,{keepTag:true,skipHistory:true});return}
  if(path==='/app/archive'){setView('archived',null,{keepTag:true,skipHistory:true});return}
  if(path==='/app/unfiled'){setView('unfiled',null,{keepTag:true,skipHistory:true});return}
  if(path==='/app/topics'){setView('topics',null,{keepTag:true,skipHistory:true});return}
  let match=path.match(/^\/app\/folders\/(\d+)$/);
  if(match){
    const id=Number(match[1]);
    if(!folders.some(f=>f.id===id)){setView('all',null,{keepTag:true,skipHistory:true});message('Ordner nicht gefunden.',true);return}
    setView('all',id,{keepTag:true,skipHistory:true});return
  }
  match=path.match(/^\/app\/smart\/(\d+)$/);
  if(match){
    const id=Number(match[1]);
    if(!smartFolders.some(f=>f.id===id)){setView('all',null,{keepTag:true,skipHistory:true});message('Intelligenter Ordner nicht gefunden.',true);return}
    setSmart(id,true);return
  }
  if(path.startsWith('/app/chats/')){
    const id=path.slice('/app/chats/'.length);
    setView('all',null,{keepTag:true,skipHistory:true});
    try{showChat(decodeURIComponent(id),true)}catch{message('Ungültiger Chat-Link.',true)}
    return
  }
  if(path==='/app'||path==='/app/'){setView('all',null,{keepTag:true,skipHistory:true});return}
  setView('all',null,{keepTag:true,skipHistory:true});message('Ansicht nicht gefunden.',true)
}
function updateUndatedControls(){
  for(const id of ['date-from','date-to'])$(id).disabled=$('undated').checked
}
function renderSidebar(){
  const library=page==='library';
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',library&&smart===null&&folder===null&&view===b.dataset.view));
  document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',page===b.dataset.page));
  const nav=$('folders');nav.replaceChildren();
  const hasChildren=id=>folders.some(x=>x.parent_id===id);
  function walk(parent,depth,seen){
    if(depth>15)return;
    for(const f of folders.filter(x=>x.parent_id===parent)){
      if(seen.has(f.id))continue;
      const row=element('div','folderrow');row.style.paddingLeft=(depth*12)+'px';
      const open=!collapsed.has(f.id);
      const twisty=element('button','twisty'+(hasChildren(f.id)?'':' leafpad'));twisty.type='button';
      if(hasChildren(f.id)){twisty.setAttribute('aria-expanded',String(open));twisty.setAttribute('aria-label',(open?'Zuklappen: ':'Aufklappen: ')+f.name);
        twisty.onclick=()=>{open?collapsed.add(f.id):collapsed.delete(f.id);store.set('chatidy-collapsed-folders',[...collapsed]);renderSidebar()}}
      else{twisty.tabIndex=-1;twisty.setAttribute('aria-hidden','true')}
      const b=button('',()=>setView('all',f.id),'folderbtn'+(library&&folder===f.id?' active':''));
      const name=element('span','',' '+f.name);
      const count=element('small','',String(f.item_count));b.append(element('span','ficon','▤'),name,count);b.title='Ordner öffnen: '+f.name;
      b.ondragover=e=>{if(e.dataTransfer.types.includes('application/x-chatidy-ids')){e.preventDefault();b.classList.add('drop-target')}};
      b.ondragleave=()=>b.classList.remove('drop-target');
      b.ondrop=e=>{e.preventDefault();b.classList.remove('drop-target');try{const ids=JSON.parse(e.dataTransfer.getData('application/x-chatidy-ids'));if(Array.isArray(ids)&&ids.length&&ids.length<=500)assignChats(ids,f.id)}catch(error){message('Ungültige Drag-and-drop-Auswahl.',true)}};
      row.append(twisty,b);nav.append(row);
      if(open||!hasChildren(f.id))walk(f.id,depth+1,new Set([...seen,f.id]));
    }
  }walk(null,0,new Set());
  if(!folders.length)nav.append(element('p','muted','Noch keine Ordner.'));
  const smartNav=$('smart-folders');smartNav.replaceChildren();
  for(const f of smartFolders){
    const row=element('div','smart-row');
    const smartButton=button('',()=>setSmart(f.id),'folderbtn'+(library&&smart===f.id?' active':''));smartButton.append(element('span','ficon','◇'),element('span','',' '+f.name));
    row.append(smartButton,
      button('×',async()=>{if(!confirm('Intelligenten Ordner löschen? Chats bleiben erhalten.'))return;try{await post('/api/smart-folders/delete',{id:f.id});if(smart===f.id)setView('all');await loadOrganisation()}catch(e){message(e.message,true)}},'textbtn'));
    smartNav.append(row);
  }
  if(!smartFolders.length)smartNav.append(element('p','muted','Speichere eine Suche, um sie hier abzulegen.'));
  const tagNav=$('tag-list');tagNav.replaceChildren();const activeTag=$('tag-filter').value;
  for(const tag of tags){
    const b=button('# '+tag.name,()=>{if(smart!==null)return;$('tag-filter').value=activeTag===tag.name?'':tag.name;setView('all',null,{keepTag:true})},'tagbtn'+(activeTag===tag.name?' active':''));
    b.append(element('small','',String(tag.count)));b.title='Nach Tag filtern: '+tag.name;tagNav.append(b);
  }
  if(!tags.length)tagNav.append(element('p','muted','Noch keine Tags.'));
  renderProviders();renderSources();
}
async function loadStats(){
  const stats=await api('/api/stats');const n=v=>Number(v||0).toLocaleString('de-DE');
  for(const key of ['chats','messages','folders','inbox'])$('stat-'+key).textContent=n(stats[key]);
  $('count-all').textContent=n(stats.chats);$('count-inbox').textContent=n(stats.inbox);
  $('count-archived').textContent=n(stats.archived);$('count-unfiled').textContent=n(stats.unfiled);
  providers=stats.providers&&typeof stats.providers==='object'?stats.providers:{};
  sourceCounts=stats.sources&&typeof stats.sources==='object'?stats.sources:{};
  renderProviders();renderSources();
  // Topic views are computed from titles; only their number is shown here.
  try{$('count-topics').textContent=n((await api('/api/topics')).length)}catch{$('count-topics').textContent=''}
}
function date(value){if(!value)return 'Ohne Datum';const number=Number(value);const d=new Date(number<1e11?number*1000:number);return isNaN(d)?'Ohne Datum':d.toLocaleDateString('de-DE')}
async function loadChats(append=false){
  if(append&&loading)return;
  const epoch=++loadEpoch;
  if(view==='topics'&&folder===null){loading=false;return showTopics(epoch)}
  loading=true;
  try{
    const params=new URLSearchParams();if(smart!==null)params.set('smart',smart);if($('search').value.trim())params.set('q',$('search').value.trim());
    if(folder!==null)params.set('folder',folder);else params.set('mode',view);
    if($('tag-filter').value)params.set('tag',$('tag-filter').value);
    if(smart===null&&providerFilter)params.set('provider',providerFilter);
    if(smart===null&&sourceFilter)params.set('source',sourceFilter);
    if($('date-from').value&&!$('undated').checked){
      const start=new Date($('date-from').value+'T00:00:00');
      params.set('date_from',$('date-from').value);
      params.set('date_from_offset',String(start.getTimezoneOffset()))
    }
    if($('date-to').value&&!$('undated').checked){
      const end=new Date($('date-to').value+'T00:00:00');
      end.setDate(end.getDate()+1);
      params.set('date_to',$('date-to').value);
      params.set('date_to_offset',String(end.getTimezoneOffset()))
    }
    if($('undated').checked)params.set('undated','1');
    params.set('sort',$('date-sort').value);
    params.set('limit',PAGE);params.set('offset',append?offset:0);
    const result=await api('/api/chats?'+params);
    if(epoch!==loadEpoch)return;
    if(append){chats.push(...result);offset+=result.length}else{chats=result;offset=result.length}
    $('view-title').textContent=currentName();$('results-label').textContent=chats.length+' Ergebnisse geladen';
    $('more').hidden=result.length<PAGE;renderChats();renderSelection();
  }catch(e){message('Suche fehlgeschlagen: '+e.message,true)}finally{if(epoch===loadEpoch)loading=false}
}
async function showTopics(epoch){
  try{
    const topics=await api('/api/topics');if(epoch!==loadEpoch)return;const q=$('search').value.trim().toLowerCase();
    const visible=topics.filter(t=>!q||t.label.toLowerCase().includes(q)||t.examples.some(x=>x.toLowerCase().includes(q)));
    $('view-title').textContent='Themencluster';$('results-label').textContent=visible.length+' Themen gefunden';
    $('more').hidden=true;const list=$('chat-list');list.replaceChildren();
    if(!visible.length){list.append(element('div','empty','Noch keine Themen erkannt. Importiere Chats mit ähnlichen Titeln oder Hashtags.'));return}
    for(const topic of visible){
      const b=button('',()=>showTopicDetail(topic),'chat-card topic');
      b.append(element('div','chat-title',topic.type==='hashtag'?'# '+topic.label:topic.label));
      const meta=element('div','chat-meta');meta.append(element('span','',topic.count+' Chats'),element('span','pill',topic.type==='group'?'Ordner':topic.type==='title'?'Titel':'Hashtag'));b.append(meta);
      list.append(b);
    }
  }catch(e){message(e.message,true)}
}
function showTopicDetail(topic){
  details=null;selected=null;document.body.classList.add('reading');
  const panel=$('detail');panel.replaceChildren();
  panel.append(element('h2','',topic.label));
  panel.append(element('p','muted',topic.count+' unterschiedliche Gespräche · '+topic.type+'. Themen sind unverbindliche lokale Ansichten, keine KI-Videoanalyse.'));
  panel.append(element('h3','','Beispielgespräche'));
  for(const title of topic.examples)panel.append(element('div','bubble',title));
  panel.append(button('↗ Chats dieses Themas zuordnen',()=>{
    const target=select('Zielgruppe',folders.map(f=>[f.id,f.name]));
    modal('Themencluster zu Gruppe hinzufügen',[
      element('p','muted','Bis zu 500 Chats werden nach deiner Bestätigung zusätzlich einer Gruppe zugeordnet. Bestehende Zuordnungen bleiben erhalten.'),
      target.wrapper
    ],async()=>{
      if(!confirm(topic.conversation_ids.length+' Chats zu dieser Gruppe hinzufügen?'))return;
      const response=await post('/api/bulk/assign',{conversation_ids:topic.conversation_ids,folder_id:Number(target.input.value)});
      message(response.assigned+' Chats zugeordnet.');await refresh();
    },'Zuordnung bestätigen')
  },'primary'));
}
function renderChats(){
  const list=$('chat-list');list.replaceChildren();
  if(!chats.length){list.append(element('div','empty','Noch keine Chats in dieser Ansicht. Importiere einen Export oder passe die Filter an.'));return}
  for(const chat of chats){
    const row=element('div','chat-card chat-row'+(chat.id===selected?' selected':''));row.draggable=true;
    row.ondragstart=e=>{const ids=chosen.has(chat.id)?[...chosen]:[chat.id];e.dataTransfer.setData('application/x-chatidy-ids',JSON.stringify(ids));e.dataTransfer.effectAllowed='copy'};
    const check=element('input');check.type='checkbox';check.checked=chosen.has(chat.id);check.setAttribute('aria-label','Chat auswählen: '+chat.title);
    check.onchange=()=>{if(check.checked&&chosen.size>=500){check.checked=false;message('Maximal 500 Chats auswählen.',true);return}check.checked?chosen.add(chat.id):chosen.delete(chat.id);renderSelection()};
    const b=button('',()=>showChat(chat.id),'chat-open');row.append(check,b);
    b.append(element('div','chat-title',chat.title||'Ohne Titel'),element('span','chat-date',date(chat.updated||chat.created)),element('span','chat-count',String(chat.message_count)));
    b.title=(chat.title||'Ohne Titel')+' · '+chat.message_count+' Nachrichten';
    const meta=element('div','chat-meta');
    const subtype=(()=>{try{return JSON.parse(chat.metadata||'{}').source||''}catch{return ''}})();
    const visibleSource=SOURCE_LABELS[subtype]||providerLabel(chat.provider);
    if(visibleSource)meta.append(element('span','pill provider provider-'+String(chat.provider||'').replace(/[^a-z0-9_-]/gi,''),visibleSource));
    if(!chat.reviewed)meta.append(element('span','pill new','Neu'));
    if(chat.groups_count)meta.append(element('span','pill',chat.groups_count+(chat.groups_count===1?' Gruppe':' Gruppen')));
    b.append(meta);list.append(row);
  }
}
// Splits ``` fenced blocks into <pre>; everything stays textContent (no HTML from chats).
function appendContent(box,content){
  const text=String(content??'');const parts=text.split(/```/);
  if(parts.length<3){box.append(document.createTextNode(text));return}
  parts.forEach((part,i)=>{
    if(i%2===0||i===parts.length-1&&parts.length%2===0){if(part)box.append(document.createTextNode(i%2===0?part.replace(/^\n/,''):'```'+part));return}
    const newline=part.indexOf('\n');const head=newline>=0?part.slice(0,newline).trim():'';
    const code=element('pre','code',(/^[\w+#.-]{1,20}$/.test(head)?part.slice(newline+1):part).replace(/\n$/,''));
    if(/^[\w+#.-]{1,20}$/.test(head))code.dataset.lang=head;box.append(code);
  });
}
function thinkingBlock(item){
  const box=element('details','thinking');
  box.append(element('summary','','💭 '+item.label+(item.steps.length?' · '+item.steps.length+(item.steps.length===1?' Schritt':' Schritte'):'')));
  for(const step of item.steps){
    if(step.title)box.append(element('div','thinking-title',step.title));
    if(step.text)box.append(element('div','thinking-text',step.text));
  }
  const raw=element('details');raw.append(element('summary','','Metadaten'));
  raw.append(element('pre','metadata-json',JSON.stringify(item.messages.map(m=>m.metadata),null,2)));box.append(raw);
  return box;
}
function activityDetails(activity,cls='activity'){
  const box=element('details',cls);box.append(element('summary','',activity.label));
  for(const name of activity.tools)box.append(element('div','thinking-text','🔧 '+name));
  if(activity.results)box.append(element('div','thinking-text','↳ '+activity.results+(activity.results===1?' Ergebnis':' Ergebnisse')+(activity.errors?', davon '+activity.errors+' mit Fehler':'')));
  for(const text of activity.thinking){box.append(element('div','thinking-title','Denkprozess'),element('div','thinking-text',text))}
  if(activity.other.length)box.append(element('div','thinking-text','Weitere Blöcke: '+[...new Set(activity.other)].join(', ')));
  return box;
}
function section(title,open=true){const d=element('details','section');d.open=open;d.append(element('summary','',title));const body=element('div','sectionbody');d.append(body);return [d,body]}
function renderDetail(){
  const detail=$('detail');detail.replaceChildren();
  if(!details){const blank=element('div','empty detail-empty');blank.append(element('div','empty-icon','✳'),element('strong','','Kein Chat geöffnet'),element('p','','Wähle in der Liste einen Chat, um Verlauf, Gruppen und Tags zu sehen.'));detail.append(blank);return}
  const c=details.chat;detail.append(element('h2','',c.title),element('div','muted',providerLabel(c.provider)+(c.metadata&&c.metadata.source==='codex'?' · Codex':'')+' · '+(c.project?'Projekt: '+c.project+' · ':'')+visibleMessageCount(details.messages)+' Nachrichten · '+date(c.updated||c.created)+(c.reviewed?' · geprüft':' · noch nicht geprüft')));
  const actions=element('div','detail-actions');
  actions.append(button(c.reviewed?'↺ Erneut prüfen':'✓ Geprüft',async()=>{
    try{await post('/api/review',{conversation_id:c.id,reviewed:!c.reviewed});await refresh();await showChat(c.id)}catch(e){message(e.message,true)}
  },c.reviewed?'soft':'primary'));
  actions.append(button('✦ KI-Kategorien',()=>suggest(c.id)));
  actions.append(button('↓ Chat exportieren',()=>exportChats([c.id])));
  detail.append(actions);
  const [groups,groupBody]=section('Gruppen & Tags');
  const chips=element('div','chipbox');for(const id of details.folders){const f=folders.find(x=>x.id===id);if(f)chips.append(element('span','chip','▤ '+f.name))}
  if(!chips.childElementCount)chips.append(element('span','muted','Keiner Gruppe zugeordnet.'));
  const tagChips=element('div','chipbox');for(const name of details.tags||[])tagChips.append(element('span','chip tag','# '+name));
  const groupActions=element('div','detail-actions');groupActions.append(button('▤ Gruppen bearbeiten',()=>editGroups(c.id)),button('Tags bearbeiten',()=>editTags([c.id],true)));
  groupBody.append(chips,tagChips,groupActions);
  if(details.suggestions.length)groupBody.append(element('div','notice','KI-Vorschläge: '+details.suggestions.map(x=>folders.find(f=>f.id===x.folder_id)?.name||x.folder_id).join(', ')+' – bitte über „Gruppen bearbeiten“ bestätigen.'));
  detail.append(groups);
  if(c.metadata&&Object.keys(c.metadata).length){const [meta,metaBody]=section('Gesprächsmetadaten',false);metaBody.append(element('pre','metadata-json',JSON.stringify(c.metadata,null,2)));detail.append(meta)}
  detail.append(element('div','msglabel','Verlauf · '+visibleMessageCount(details.messages)+' Nachrichten'));
  for(const item of readingItems(details.messages)){
    if(item.kind==='thinking'){detail.append(thinkingBlock(item));continue}
    if(item.kind==='activity'){
      const block=activityDetails(item.activity,'thinking activity');
      const raw=element('details');raw.append(element('summary','','Metadaten'));
      raw.append(element('pre','metadata-json',JSON.stringify(item.message.metadata,null,2)));block.append(raw);
      detail.append(block);continue;
    }
    const m=item.message;
    const box=element('div','bubble '+(m.role==='user'?'user':'assistant'));
    box.append(element('div','role',m.role==='user'?'DU':m.role==='assistant'?'ASSISTENT':String(m.role||'Unbekannt').toUpperCase()));
    appendContent(box,m.content);
    if(item.activity)box.append(activityDetails(item.activity,'thinking activity inline'));
    if(m.metadata&&Object.keys(m.metadata).length){
      const extra=element('details');extra.append(element('summary','','Quellen, Anhänge und Metadaten'));
      extra.append(element('pre','metadata-json',JSON.stringify(m.metadata,null,2)));box.append(extra);
    }
    detail.append(box);
  }
}
async function showChat(id,skipHistory=false){
  selected=id;
  try{
    details=await api('/api/chat/'+encodeURIComponent(id));
    if(!skipHistory)pushRoute('/app/chats/'+encodeURIComponent(id));
    renderChats();renderDetail();$('detail').scrollTop=0;document.body.classList.add('reading')
  }catch(e){selected=null;message(e.message,true)}
}
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
async function refresh(){await Promise.all([loadFolders(),loadStats(),loadOrganisation()]);await loadChats()}
let importJob=localStorage.getItem('chatidy-import-job'), importPoll=null;
let jobListEpoch=0;
const jobLabels={uploading:'Wird hochgeladen',uploaded:'Hochgeladen',validating:'In Prüfung',committing:'Wird übernommen',done:'Erfolgreich',error:'Fehlgeschlagen',interrupted:'Unterbrochen',awaiting_confirmation:'Vorschau bereit – Bestätigung erforderlich',cleanup_pending:'Bereinigung unterbrochen',blocked:'Jobdaten gesperrt'};
function jobSize(bytes){return new Intl.NumberFormat('de-DE',{maximumFractionDigits:1}).format(Number(bytes||0)/1048576)+' MB'}
async function loadJobs(){
  const epoch=++jobListEpoch;
  try{
    const result=await api('/api/import/jobs');
    if(epoch!==jobListEpoch)return;
    const unknown=result.jobs.some(job=>job.state==='blocked');
    $('job-summary').textContent=result.count+' gespeicherte Jobs · '+jobSize(result.storage_bytes)+' erfasste Dateigröße'+(unknown?' · Größe gesperrter Jobs unbekannt':'')+(result.ignored_entries?' · Fremde Einträge werden nicht verwaltet':'');
    const list=$('job-list');list.replaceChildren();
    if(!result.jobs.length)list.append(element('p','muted','Keine gespeicherten Importjobs.'));
    for(const job of result.jobs){
      const row=element('section','job-row');row.dataset.jobId=job.id;
      row.append(element('strong','job-state',jobLabels[job.state]||job.state));
      const created=job.created?new Date(job.created*1000).toLocaleString('de-DE'):'unbekannt';
      row.append(element('p','muted',job.id.slice(0,8)+' · Erstellt: '+created+' · '+(job.validated||0)+' Gespräche geprüft · '+jobSize(job.storage_bytes)));
      if(job.error)row.append(element('p','muted',job.error));
      if(job.state==='interrupted')row.append(element('p','muted',job.can_resume?'Nach Prozessunterbrechung wiederaufnehmbar.':'Upload unvollständig; bitte erneut hochladen.'));
      if(job.state==='cleanup_pending')row.append(element('p','muted','Ein Teil der Jobdaten wurde bereits entfernt. Zum Abschließen Löschung erneut bestätigen.'));
      const actions=element('div','job-actions');
      if(job.state==='awaiting_confirmation')actions.append(button('Vorschau öffnen',async()=>{importJob=job.id;localStorage.setItem('chatidy-import-job',job.id);await pollImport();$('import-preview').scrollIntoView({block:'start'})}));
      if(job.can_resume&&job.state!=='awaiting_confirmation')actions.append(button('Fortsetzen',async()=>{
        try{await post('/api/import/jobs/'+job.id+'/resume',{});importJob=job.id;localStorage.setItem('chatidy-import-job',job.id);clearTimeout(importPoll);pollImport();await loadJobs()}
        catch(e){message(e.message,true)}
      }));
      const remove=button('Jobdaten löschen',async()=>{
        const detail=job.state==='done'?'Dieser Import ist erfolgreich abgeschlossen.':job.state==='cleanup_pending'?'Die unterbrochene Bereinigung wird abgeschlossen.':'Dieser Import ist nicht erfolgreich abgeschlossen. Seine Wiederaufnahme ist danach nicht mehr möglich.';
        if(!confirm(detail+' Lokale Jobdaten ('+jobSize(job.storage_bytes)+') wirklich löschen? Importierte Chats und die ursprüngliche Exportdatei bleiben erhalten.'))return;
        try{
          await post('/api/import/jobs/'+job.id+'/delete',{confirm:true});
          if(importJob===job.id){importJob=null;clearTimeout(importPoll);localStorage.removeItem('chatidy-import-job');$('import-status').hidden=true;$('import-preview').hidden=true}
          await loadJobs();message('Lokale Jobdaten gelöscht. Importierte Chats bleiben erhalten.');
        }catch(e){message(e.message,true);await loadJobs()}
      });
      remove.disabled=!job.can_delete;
      if(job.active)remove.title='Aktive Importjobs können nicht gelöscht werden.';
      actions.append(remove);row.append(actions);list.append(row);
    }
  }catch(e){if(epoch!==jobListEpoch)return;$('job-summary').textContent='Jobverwaltung nicht verfügbar: '+e.message;$('job-list').replaceChildren()}
}
$('refresh-jobs').onclick=loadJobs;
$('job-management').ontoggle=()=>{if($('job-management').open)loadJobs()};
loadJobs();
function renderImportPreview(job){
  const root=$('import-preview');root.hidden=job.state!=='awaiting_confirmation'||Boolean(job.active);
  if(root.hidden)return;
  root.replaceChildren();const plan=job.preview;if(!plan)return;
  root.append(element('h2','','Import-Vorschau'));
  const layout=plan.inventory;
  const format={official_segments:'Nummerierter offizieller Export',official_classic:'Klassischer offizieller Export',structured_json_archive:'Strukturiertes JSON-Archiv',single_json:'Einzelne JSON-Datei'}[layout.format]||'JSON-Export';
  root.append(element('p','muted',format+' · '+layout.segment_count+' Konversationsdateien · '+plan.conversations+' erkannte Gespräche'));
  const resources=element('ul');const labels={conversation_segment:'Konversationsdateien',metadata:'Zusätzliche JSON-Metadaten',attachment:'Anhang-/Binärressourcen',html_viewer:'HTML-Darstellung',supported_resource:'Begleitdateien',unknown:'Unbekannte Zusatzdateien'};
  for(const [kind,count] of Object.entries(layout.counts||{}))resources.append(element('li','',String(count)+' '+(labels[kind]||kind)));
  const roles=layout.metadata_roles||{};
  if(layout.manifests||roles.codex||layout.sensitive_metadata_files)root.append(element('p','muted',(layout.manifests||0)+' Manifeste · '+(roles.codex||0)+' Codex-Dateien · '+(layout.sensitive_metadata_files||0)+' sensible Konto-/Werbe-/Einstellungsdateien: nur inventarisiert.'));
  if(layout.codex_conversations)root.append(element('p','muted',layout.codex_conversations+' Codex-Aufgaben aus codex.json werden als eigene Chats importiert (gekennzeichnet „Codex“).'));
  root.append(resources,element('p','muted','Grob geschätzter zusätzlicher Speicher: '+jobSize(plan.estimated_additional_bytes)+'. '+plan.estimate_note));
  const kinds={new:'Neu',identical:'Bereits identisch vorhanden – bleibt unverändert',newer:'Neuere vollständige Version',complete:'Vollständige Ergänzung',older:'Älter oder ohne erforderlichen Änderungszeitpunkt',branch:'Abweichender/unvollständiger Gesprächszweig',identity:'Unklare Nachrichten-/Versionsidentität'};
  const decisions={};
  for(const [kind,count] of Object.entries(plan.classes)){
    if(!count)continue;
    root.append(element('p','',count+' · '+kinds[kind]));
    if(kind==='older'||kind==='branch'){
      const choice=select('Entscheidung für alle Fälle dieser Klasse in diesem Import',[
        ['abort','Import bei dieser Klasse abbrechen'],['skip','Diese Gespräche vollständig unverändert lassen']]);
      decisions[kind]=choice.input;root.append(choice.wrapper);
    }
  }
  for(const warning of plan.warnings||[])root.append(element('p','muted',warning));
  if(!plan.can_confirm)root.append(element('p','','Unklare Identitäten blockieren diesen Batch. Es gibt kein pauschales Fehler-Ignorieren.'));
  const confirm=button('Diesen Batch importieren',async()=>{
    confirm.disabled=true;
    try{
      await post('/api/import/jobs/'+job.id+'/confirm',{confirm:true,policies:Object.fromEntries(Object.entries(decisions).map(([kind,input])=>[kind,input.value]))});
      importJob=job.id;localStorage.setItem('chatidy-import-job',job.id);clearTimeout(importPoll);pollImport();
    }catch(e){message(e.message,true);updateConfirm()}
  },'primary');confirm.id='confirm-batch';
  function updateConfirm(){confirm.disabled=!plan.can_confirm||Object.values(decisions).some(input=>input.value!=='skip')}
  for(const input of Object.values(decisions))input.onchange=updateConfirm;
  updateConfirm();root.append(confirm,element('p','muted','Eine Bestätigung gilt nur für diesen Batch. Bis dahin wurden keine Chats übernommen. Alle Entscheidungen werden beim Übernehmen erneut geprüft.'));
}
async function pollImport(){
  if(!importJob)return;
  const polled=importJob;
  $('import-status').hidden=false;
  try{
    const result=await api('/api/import/jobs/'+polled);
    // A newer import may have started while this request was in flight.
    if(importJob!==polled)return;
    const labels=jobLabels;
    renderImportPreview(result);
    $('import-status-text').textContent=(labels[result.state]||result.state)+' · '+(result.validated||0)+' Chats geprüft'+(result.error?' · '+result.error:'')+(result.result?' · '+result.result.imported+' übernommen, '+result.result.unchanged+' unverändert':'');
    $('resume-import').hidden=!result.can_resume||result.state==='awaiting_confirmation';
    if(result.state==='done'){
      clearTimeout(importPoll);localStorage.removeItem('chatidy-import-job');importJob=null;
      $('pick-file').disabled=false;await Promise.all([refresh(),loadJobs()]);
      if(page==='import'){setView('all');message('Import abgeschlossen'+(result.result?': '+result.result.imported+' übernommen, '+result.result.unchanged+' unverändert.':'.'))}
      return;
    }
    if($('job-management').open)await loadJobs();
    if(result.active||result.state==='uploaded')importPoll=setTimeout(pollImport,1500);
  }catch(e){
    $('import-status-text').textContent='Importstatus nicht erreichbar: '+e.message;
    $('resume-import').hidden=true;
    await loadJobs();
  }
}
$('resume-import').onclick=async()=>{
  if(!importJob)return;
  try{await post('/api/import/jobs/'+importJob+'/resume',{});clearTimeout(importPoll);pollImport()}
  catch(e){message(e.message,true)}
};
async function importFile(file){
  if(!file)return;
  if(!/\.(json|zip)$/i.test(file.name)){message('Bitte eine ZIP- oder JSON-Datei auswählen.',true);return}
  if(file.size>200*1024*1024){message('Datei zu groß (maximal 200 MB).',true);return}
  // Stop following the previous job so its late results cannot switch pages or clear the new job.
  clearTimeout(importPoll);importJob=null;
  showPage('import');$('pick-file').disabled=true;message('Upload läuft lokal …');
  try{
    const result=await api('/api/import/analyze',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Filename':file.name.replace(/[^a-zA-Z0-9_.-]/g,'_')},body:file});
    importJob=result.id;localStorage.setItem('chatidy-import-job',importJob);clearTimeout(importPoll);pollImport();
  }catch(e){message('Import fehlgeschlagen: '+e.message,true)}finally{$('pick-file').disabled=false}
}
// F-003: A multi-selection creates separate, inspectable import jobs. Each
// file retains its own progress, failure and explicit preview confirmation.
function uploadWithProgress(file,progress){
  return new Promise((resolve,reject)=>{
    const req=new XMLHttpRequest();
    req.open('POST','/api/import/analyze');
    req.setRequestHeader('Content-Type','application/octet-stream');
    req.setRequestHeader('X-Filename',file.name.replace(/[^a-zA-Z0-9_.-]/g,'_'));
    req.upload.onprogress=e=>{if(e.lengthComputable)progress(Math.round(e.loaded/e.total*100))};
    req.onload=()=>{
      let data;
      try{data=JSON.parse(req.responseText)}catch{reject(new Error('Ungültige Serverantwort.'));return}
      if(req.status>=200&&req.status<300)resolve(data);
      else reject(new Error(data.error||'Upload fehlgeschlagen ('+req.status+').'))
    };
    req.onerror=()=>reject(new Error('Verbindung beim Upload unterbrochen.'));
    req.send(file)
  })
}
function multiStatus(file){
  const row=element('div','multi-upload-row');
  const name=element('strong','',file.name);
  const state=element('span','muted','Wartet auf Upload');
  const actions=element('div','multi-upload-actions');
  row.append(name,state,actions);$('multi-upload-status').append(row);
  return {state,actions}
}
async function monitorMultiJob(id,row){
  try{
    const status=await api('/api/import/jobs/'+id);
    row.state.textContent=jobLabels[status.state]||status.state;
    if(status.error)row.state.textContent+=' · '+status.error;
    if(status.state==='awaiting_confirmation'){
      row.actions.replaceChildren(button('Vorschau öffnen',async()=>{
        importJob=id;localStorage.setItem('chatidy-import-job',id);
        showPage('import');await pollImport();
        $('import-preview').scrollIntoView({block:'start'});
      }));
    }else if(status.active||status.state==='uploaded'||status.state==='committing'){
      setTimeout(()=>monitorMultiJob(id,row),1800);
    }
  }catch(e){row.state.textContent='Statusfehler: '+e.message}
}
async function importFiles(files){
  const list=Array.from(files||[]);
  if(!list.length)return;
  if(list.length===1){await importFile(list[0]);return}
  // A previous single-file job keeps its server-side status, but must not
  // unexpectedly redirect away from the newly selected multi-file queue.
  clearTimeout(importPoll);
  importJob=null;
  localStorage.removeItem('chatidy-import-job');
  $('import-status').hidden=true;
  $('import-preview').hidden=true;
  showPage('import');
  $('multi-upload-status').hidden=false;
  $('multi-upload-status').replaceChildren(element('strong','','Mehrfachauswahl: '+list.length+' Dateien – jede Vorschau einzeln prüfen und bestätigen'));
  if(list.length>20){message('Bitte höchstens 20 Dateien gleichzeitig auswählen.',true);return}
  $('pick-file').disabled=true;
  try{
    for(const file of list){
      const row=multiStatus(file);
      if(!/\.(json|zip)$/i.test(file.name)){row.state.textContent='Fehler: nur ZIP/JSON erlaubt';continue}
      if(!file.size||file.size>200*1024*1024){row.state.textContent='Fehler: leer oder größer als 200 MB';continue}
      try{
        row.state.textContent='Upload läuft: 0 %';
        const result=await uploadWithProgress(file,value=>row.state.textContent='Upload läuft: '+value+' %');
        row.state.textContent='Hochgeladen · Server prüft …';
        monitorMultiJob(result.id,row);
      }catch(e){row.state.textContent='Fehler: '+e.message}
    }
    await loadJobs();
    message('Dateien übermittelt. Bitte für jede Datei die Vorschau öffnen und den Import bestätigen.');
  }finally{$('pick-file').disabled=false}
}
if(importJob){page='import';$('import-page').hidden=false;$('library-page').hidden=true;document.body.classList.add('page-import');pollImport()}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{showPage(b.dataset.page);if(b.dataset.page==='import')loadJobs()});
$('close-reader').onclick=closeReader;
$('select-loaded').onchange=()=>{chosen=$('select-loaded').checked?new Set(chats.slice(0,500).map(c=>c.id)):new Set();renderChats();renderSelection()};
$('bulk-assign').onclick=()=>assignChats([...chosen],$('bulk-folder').value);
$('bulk-tags').onclick=()=>editTags([...chosen]);
$('tag-filter').onchange=()=>setView('all',null,{keepTag:true});
$('save-smart').onclick=()=>{
  const name=field('Name des intelligenten Ordners');
  modal('Aktuelle Suche speichern',[name.wrapper],async()=>{
    const query=smart!==null?smartFolders.find(f=>f.id===smart).query:{q:$('search').value,tag:$('tag-filter').value,provider:providerFilter,mode:['all','inbox','archived','unfiled'].includes(view)?view:'all'};
    await post('/api/smart-folders',{name:name.input.value,query});await loadOrganisation();
  },'Suche speichern');
};
$('new-folder').onclick=createFolder;$('new-rule').onclick=rulesModal;$('export').onclick=()=>exportChats();
$('refresh').onclick=refresh;$('more').onclick=()=>loadChats(true);$('clear').onclick=()=>{$('search').value='';offset=0;syncRouteQuery();loadChats();$('search').focus()};
$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{offset=0;syncRouteQuery();loadChats()},250)};
for(const id of ['date-from','date-to','date-sort','undated'])$(id).onchange=()=>{updateUndatedControls();offset=0;syncRouteQuery();loadChats()};
$('pick-file').onclick=()=>$('file-input').click();
$('file-input').onchange=e=>{const files=Array.from(e.target.files);e.target.value='';importFiles(files)};
const drop=$('dropzone');for(const type of ['dragenter','dragover'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('drag')});
for(const type of ['dragleave','drop'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('drag')});
drop.addEventListener('drop',e=>importFiles(e.dataTransfer.files));
// Collapsible sidebar sections (state is a per-browser convenience only).
const closedSections=new Set(store.get('chatidy-closed-sections',[]));
document.querySelectorAll('.navsection').forEach(section=>{
  const toggle=section.querySelector('.sectiontoggle'),body=$(toggle.getAttribute('aria-controls'));
  const apply=()=>{const open=!closedSections.has(section.dataset.section);toggle.setAttribute('aria-expanded',String(open));body.hidden=!open};
  toggle.onclick=()=>{closedSections.has(section.dataset.section)?closedSections.delete(section.dataset.section):closedSections.add(section.dataset.section);store.set('chatidy-closed-sections',[...closedSections]);apply()};
  apply();
});
// Resizable navigation and reader. Widths are clamped so the chat list keeps its minimum width.
const sizes=store.get('chatidy-pane-widths',{});
const CENTER_MIN=340,NAV_MIN=180,NAV_MAX=480,READER_MIN=320;
function navWidth(){return parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--nav'))||244}
function applySizes(){
  const root=document.documentElement.style;
  if(sizes.nav)root.setProperty('--nav',Math.round(Math.min(NAV_MAX,Math.max(NAV_MIN,sizes.nav)))+'px');else root.removeProperty('--nav');
  if(sizes.reader){const max=Math.max(READER_MIN,innerWidth-navWidth()-CENTER_MIN);root.setProperty('--reader',Math.round(Math.min(max,Math.max(READER_MIN,sizes.reader)))+'px')}else root.removeProperty('--reader');
  for(const [id,key] of [['resize-nav','nav'],['resize-reader','reader']]){const w=key==='nav'?navWidth():$('reader').getBoundingClientRect().width;$(id).setAttribute('aria-valuenow',String(Math.round(w)))}
}
function setSize(key,value){sizes[key]=value;applySizes();store.set('chatidy-pane-widths',sizes)}
for(const [id,key] of [['resize-nav','nav'],['resize-reader','reader']]){
  const handle=$(id);handle.setAttribute('aria-valuemin',String(key==='nav'?NAV_MIN:READER_MIN));
  handle.onpointerdown=e=>{
    e.preventDefault();handle.setPointerCapture(e.pointerId);handle.classList.add('dragging');document.body.classList.add('resizing');
    handle.onpointermove=m=>setSize(key,key==='nav'?m.clientX:innerWidth-m.clientX);
    handle.onpointerup=handle.onpointercancel=()=>{handle.onpointermove=null;handle.classList.remove('dragging');document.body.classList.remove('resizing')};
  };
  handle.ondblclick=()=>{delete sizes[key];applySizes();store.set('chatidy-pane-widths',sizes)};
  handle.onkeydown=e=>{
    const step=e.shiftKey?64:16,current=key==='nav'?navWidth():$('reader').getBoundingClientRect().width;
    const grow=key==='nav'?{ArrowRight:1,ArrowLeft:-1}:{ArrowLeft:1,ArrowRight:-1};
    if(e.key in grow){e.preventDefault();setSize(key,current+grow[e.key]*step)}
  };
}
addEventListener('resize',applySizes);applySizes();
refresh().then(async()=>{
  applyRoute();
  if(location.pathname==='/app'&&!importJob&&Number((await api('/api/stats')).chats||0)===0)showPage('import');
}).catch(e=>message('Startfehler: '+e.message,true));
addEventListener('popstate',applyRoute);

/* AUTH-013: show account controls only when the server confirms an auth session. */
(async()=>{
  try{
    const response=await fetch('/api/session',{credentials:'same-origin'});
    if(!response.ok)return;
    const account=await response.json();
    $('account-name').textContent=account.display_name||'Angemeldet';
    $('account-panel').hidden=false;
  }catch{ /* Local single-user mode has no /api/session endpoint. */ }
})();
$('logout-button').addEventListener('click',async()=>{
  try{
    const response=await fetch('/logout',{method:'POST',credentials:'same-origin'});
    if(!response.ok)throw new Error('Abmeldung fehlgeschlagen.');
    location.assign('/');
  }catch(e){message(e.message,true)}
});
