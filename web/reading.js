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

// Returns display items: {kind:'message',message} or
// {kind:'thinking',label,steps,messages} where messages are the raw source messages.
function readingItems(messages){
  const items=[];
  const list=Array.isArray(messages)?messages:[];
  for(let i=0;i<list.length;i++){
    const message=list[i],type=contentType(message);
    if(!THINKING_TYPES.has(type)){items.push({kind:'message',message});continue}
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

if(typeof module!=='undefined')module.exports={readingItems};
