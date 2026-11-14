'use strict';
const $=id=>document.getElementById(id);
let view='all',folder=null,folders=[],chats=[],selected=null,offset=0,loading=false,searchTimer=null,details=null;
const PAGE=100;
let chosen=new Set(),smartFolders=[],smart=null,loadEpoch=0;
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
function setView(v,id=null){smart=null;$('search').disabled=false;$('tag-filter').disabled=false;chosen.clear();renderSelection();view=v;folder=id;offset=0;selected=null;details=null;renderSidebar();renderDetail();loadChats()}
async function loadFolders(){
  folders=await api('/api/folders');$('stat-folders').textContent=folders.length;
  const target=$('bulk-folder'),current=target.value;target.replaceChildren(new Option('Zielordner wählen',''));
  for(const f of folders)target.add(new Option(f.name,String(f.id)));target.value=current;renderSidebar();
}
async function loadOrganisation(){
  const [tags,smartResult]=await Promise.all([api('/api/tags'),api('/api/smart-folders')]);smartFolders=smartResult;
  const target=$('tag-filter'),current=target.value;target.replaceChildren(new Option('Alle Tags',''));
  for(const tag of tags)target.add(new Option(tag.name+' ('+tag.count+')',tag.name));target.value=current;
  renderSidebar();
}
function setSmart(id){
  const item=smartFolders.find(f=>f.id===id);if(!item)return;
  smart=id;folder=null;view='all';offset=0;chosen.clear();selected=null;details=null;
  $('search').value=item.query.q||'';$('search').disabled=true;$('tag-filter').value=item.query.tag||'';$('tag-filter').disabled=true;
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
function renderSidebar(){
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',smart===null&&folder===null&&view===b.dataset.view));
  const nav=$('folders');nav.replaceChildren();
  function walk(parent,depth,seen){
    if(depth>15)return;
    for(const f of folders.filter(x=>x.parent_id===parent)){
      if(seen.has(f.id))continue;
      const b=button('',()=>setView('all',f.id),'folderbtn'+(folder===f.id?' active':''));
      b.style.paddingLeft=(12+depth*13)+'px';const name=element('span','','▤ '+f.name);
      const count=element('small','',String(f.item_count));b.append(name,count);b.title='Ordner öffnen: '+f.name;
      b.ondragover=e=>{if(e.dataTransfer.types.includes('application/x-chatidy-ids')){e.preventDefault();b.classList.add('drop-target')}};
      b.ondragleave=()=>b.classList.remove('drop-target');
      b.ondrop=e=>{e.preventDefault();b.classList.remove('drop-target');try{const ids=JSON.parse(e.dataTransfer.getData('application/x-chatidy-ids'));if(Array.isArray(ids)&&ids.length&&ids.length<=500)assignChats(ids,f.id)}catch(error){message('Ungültige Drag-and-drop-Auswahl.',true)}};
      nav.append(b);walk(f.id,depth+1,new Set([...seen,f.id]));
    }
  }walk(null,0,new Set());
  const smartNav=$('smart-folders');smartNav.replaceChildren();
  for(const f of smartFolders){
    const row=element('div','smart-row');
    row.append(button('◇ '+f.name,()=>setSmart(f.id),'folderbtn'+(smart===f.id?' active':'')),
      button('×',async()=>{if(!confirm('Intelligenten Ordner löschen? Chats bleiben erhalten.'))return;try{await post('/api/smart-folders/delete',{id:f.id});if(smart===f.id)setView('all');await loadOrganisation()}catch(e){message(e.message,true)}},'textbtn'));
    smartNav.append(row);
  }
}
async function loadStats(){const stats=await api('/api/stats');for(const key of ['chats','messages','folders','inbox'])$('stat-'+key).textContent=Number(stats[key]||0).toLocaleString('de-DE');$('count-all').textContent=stats.chats;$('count-inbox').textContent=stats.inbox}
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
      const b=button('',()=>showTopicDetail(topic),'chat-card');
      b.append(element('div','chat-title',topic.type==='hashtag'?'# '+topic.label:topic.label));
      const meta=element('div','chat-meta');meta.append(element('span','',topic.count+' Chats'),element('span','pill',topic.type==='group'?'Ordner':topic.type==='title'?'Titel':'Hashtag'));b.append(meta);
      list.append(b);
    }
  }catch(e){message(e.message,true)}
}
function showTopicDetail(topic){
  details=null;selected=null;
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
    b.append(element('div','chat-title',chat.title||'Ohne Titel'));
    const meta=element('div','chat-meta');meta.append(element('span','',date(chat.updated||chat.created)));
    meta.append(element('span','',chat.message_count+' Nachrichten'));
    if(chat.groups_count)meta.append(element('span','pill',chat.groups_count+' Gruppen'));
    if(!chat.reviewed)meta.append(element('span','pill','Neu'));
    b.append(meta);list.append(row);
  }
}
function renderDetail(){
  const detail=$('detail');detail.replaceChildren();
  if(!details){const blank=element('div','empty detail-empty');blank.append(element('div','empty-icon','✦'),element('strong','','Dein Wissen ist hier.'),element('p','','Wähle einen Chat, um den Verlauf und seine Gruppen zu sehen.'));detail.append(blank);return}
  const c=details.chat;detail.append(element('h2','',c.title),element('div','muted',(c.project?'Projekt: '+c.project+' · ':'')+details.messages.length+' Nachrichten · '+date(c.updated||c.created)));
  if(c.metadata&&Object.keys(c.metadata).length){const extra=element('details');extra.append(element('summary','','Gesprächsmetadaten'),element('pre','metadata-json',JSON.stringify(c.metadata,null,2)));detail.append(extra)}
  const chips=element('div','chipbox');for(const id of details.folders){const f=folders.find(x=>x.id===id);if(f)chips.append(element('span','chip',f.name))}detail.append(chips);
  const actions=element('div','detail-actions');
  actions.append(button('▤ Gruppen bearbeiten',()=>editGroups(c.id)));
  actions.append(button('✦ KI-Kategorien',()=>suggest(c.id)));
  actions.append(button(c.reviewed?'↺ Erneut prüfen':'✓ Geprüft',async()=>{
    try{await post('/api/review',{conversation_id:c.id,reviewed:!c.reviewed});await refresh();await showChat(c.id)}catch(e){message(e.message,true)}
  }));
  actions.append(button('↓ Chat exportieren',()=>exportChats([c.id])));
  actions.append(button('Tags bearbeiten',()=>editTags([c.id],true)));
  detail.append(actions);
  const tagChips=element('div','chipbox');for(const name of details.tags||[])tagChips.append(element('span','chip','# '+name));detail.append(tagChips);
  if(details.suggestions.length){
    const info=element('div','notice','KI-Vorschläge: '+details.suggestions.map(x=>folders.find(f=>f.id===x.folder_id)?.name||x.folder_id).join(', ')+' – bitte in Gruppen bearbeiten bestätigen.');
    detail.append(info);
  }
  for(const m of details.messages){
    const box=element('div','bubble '+(m.role==='user'?'user':'assistant'));
    box.append(element('div','role',m.role==='user'?'DU':m.role==='assistant'?'ASSISTENT':String(m.role||'Unbekannt').toUpperCase()));
    box.append(document.createTextNode(m.content));
    if(m.metadata&&Object.keys(m.metadata).length){
      const extra=element('details');extra.append(element('summary','','Quellen, Anhänge und Metadaten'));
      extra.append(element('pre','metadata-json',JSON.stringify(m.metadata,null,2)));box.append(extra);
    }
    detail.append(box);
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
  const root=$('import-preview');root.hidden=job.state!=='awaiting_confirmation';
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
  $('import-status').hidden=false;
  try{
    const result=await api('/api/import/jobs/'+importJob);
    const labels=jobLabels;
    renderImportPreview(result);
    $('import-status-text').textContent=(labels[result.state]||result.state)+' · '+(result.validated||0)+' Chats geprüft'+(result.error?' · '+result.error:'')+(result.result?' · '+result.result.imported+' übernommen, '+result.result.unchanged+' unverändert':'');
    $('resume-import').hidden=!result.can_resume||result.state==='awaiting_confirmation';
    if(result.state==='done'){
      clearTimeout(importPoll);localStorage.removeItem('chatidy-import-job');importJob=null;
      $('pick-file').disabled=false;await Promise.all([refresh(),loadJobs()]);return;
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
  $('pick-file').disabled=true;message('Upload läuft lokal …');
  try{
    const result=await api('/api/import/analyze',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Filename':file.name.replace(/[^a-zA-Z0-9_.-]/g,'_')},body:file});
    importJob=result.id;localStorage.setItem('chatidy-import-job',importJob);clearTimeout(importPoll);pollImport();
  }catch(e){message('Import fehlgeschlagen: '+e.message,true)}finally{$('pick-file').disabled=false}
}
if(importJob)pollImport();
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
$('select-loaded').onchange=()=>{chosen=$('select-loaded').checked?new Set(chats.slice(0,500).map(c=>c.id)):new Set();renderChats();renderSelection()};
$('bulk-assign').onclick=()=>assignChats([...chosen],$('bulk-folder').value);
$('bulk-tags').onclick=()=>editTags([...chosen]);
$('tag-filter').onchange=()=>setView('all');
$('save-smart').onclick=()=>{
  const name=field('Name des intelligenten Ordners');
  modal('Aktuelle Suche speichern',[name.wrapper],async()=>{
    const query=smart!==null?smartFolders.find(f=>f.id===smart).query:{q:$('search').value,tag:$('tag-filter').value,mode:['all','inbox','archived','unfiled'].includes(view)?view:'all'};
    await post('/api/smart-folders',{name:name.input.value,query});await loadOrganisation();
  },'Suche speichern');
};
$('new-folder').onclick=createFolder;$('new-rule').onclick=rulesModal;$('export').onclick=()=>exportChats();
$('refresh').onclick=refresh;$('more').onclick=()=>loadChats(true);$('clear').onclick=()=>{$('search').value='';loadChats()};
$('search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{offset=0;loadChats()},250)};
$('pick-file').onclick=()=>$('file-input').click();$('file-input').onchange=e=>importFile(e.target.files[0]);
const drop=$('dropzone');for(const type of ['dragenter','dragover'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('drag')});
for(const type of ['dragleave','drop'])drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('drag')});
drop.addEventListener('drop',e=>importFile(e.dataTransfer.files[0]));
refresh().catch(e=>message('Startfehler: '+e.message,true));
