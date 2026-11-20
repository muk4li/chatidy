'use strict';
// Pure reading-view helpers (no DOM): testable with Node, see tests/reading_view.test.cjs.
// Stored message content stays unchanged; display is derived from the raw message
// metadata, so existing libraries need no reimport and reimport identity is unaffected.

const THINKING_TYPES=new Set(['thoughts','reasoning_recap']);

function contentType(message){
  const content=message&&message.metadata&&message.metadata.content;
  return content&&typeof content==='object'?content.content_type:undefined;
}

function thoughtSteps(message){
  const thoughts=message.metadata.content.thoughts;
  if(!Array.isArray(thoughts))return [];
  return thoughts.filter(t=>t&&typeof t==='object').map(t=>({
    title:typeof t.summary==='string'?t.summary:'',
    text:typeof t.content==='string'&&t.content?t.content
      :Array.isArray(t.chunks)?t.chunks.filter(x=>typeof x==='string').join('\n'):''
  }));
}

function recapText(message){
  const value=message.metadata.content.content;
  return typeof value==='string'?value:'';
}

const PLACEHOLDER='[Nicht-textueller Inhalt]';

// Claude: summarize non-text content blocks (E11). Only names/counts/thinking text are
// returned; inputs, outputs and URLs stay in the raw metadata view.
function claudeActivity(message){
  const meta=message&&message.metadata;
  if(!meta||meta.source!=='claude'||!Array.isArray(meta.content))return null;
  const tools=[],thinking=[],other=[];let results=0,errors=0;
  for(const block of meta.content){
    if(!block||typeof block!=='object')continue;
    if(block.type==='tool_use')tools.push(typeof block.name==='string'&&block.name?block.name:'Werkzeug');
    else if(block.type==='tool_result'){results++;if(block.is_error===true)errors++}
    else if(block.type==='thinking'){if(typeof block.thinking==='string'&&block.thinking.trim())thinking.push(block.thinking)}
    else if(block.type!=='text'&&typeof block.type==='string')other.push(block.type);
  }
  if(!tools.length&&!results&&!thinking.length&&!other.length)return null;
  const parts=[];
  if(tools.length){
    const names=[...new Set(tools)];
    parts.push('🔧 '+tools.length+(tools.length===1?' Werkzeugaufruf':' Werkzeugaufrufe')+' ('+names.slice(0,4).join(', ')+(names.length>4?', …':'')+')');
  }
  if(errors)parts.push('⚠ '+errors+(errors===1?' Fehler':' Fehler'));
  if(thinking.length)parts.push('💭 Denkprozess');
  if(other.length)parts.push('▫ '+[...new Set(other)].join(', '));
  return {label:parts.join(' · '),tools,results,errors,thinking,other};
}

// Returns display items: {kind:'message',message,activity} or
// {kind:'thinking',label,steps,messages} or {kind:'activity',activity,message}.
function readingItems(messages){
  const items=[];
  const list=Array.isArray(messages)?messages:[];
  for(let i=0;i<list.length;i++){
    const message=list[i],type=contentType(message);
    if(!THINKING_TYPES.has(type)){
      const activity=claudeActivity(message);
      if(activity&&message.content===PLACEHOLDER)items.push({kind:'activity',activity,message});
      else items.push({kind:'message',message,activity});
      continue;
    }
    const sources=[message];let steps=[],label='';
    if(type==='thoughts'){
      steps=thoughtSteps(message);
      const next=list[i+1];
      if(next&&contentType(next)==='reasoning_recap'){label=recapText(next);sources.push(next);i++}
    }else{
      label=recapText(message);
    }
    items.push({kind:'thinking',label:label||'Denkprozess',steps,messages:sources});
  }
  return items;
}

if(typeof module!=='undefined')module.exports={readingItems,claudeActivity};
