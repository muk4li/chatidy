// Optional integration check: Node + Playwright + a system Chromium are required.
// Uses only synthetic data and an isolated temporary database.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const {spawn}=require('node:child_process');

(async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'chatidy-browser-'));
  const reservation=net.createServer();await new Promise(r=>reservation.listen(0,'127.0.0.1',r));
  const port=reservation.address().port;await new Promise(r=>reservation.close(r));
  const root=path.resolve(__dirname,'..'),base=`http://127.0.0.1:${port}`;
  const server=spawn(process.env.PYTHON||'python',['-m','chatidy'],{cwd:root,
    env:{...process.env,CHATIDY_PORT:String(port),CHATIDY_DB:path.join(directory,'synthetic.sqlite3')},stdio:'ignore'});
  let browser;
  try{
    for(let i=0;i<100;i++){
      try{const response=await fetch(base+'/api/stats');if(response.ok)break}catch{}
      if(server.exitCode!==null)throw new Error('Server startup failed');
      await new Promise(r=>setTimeout(r,50));
    }
    browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true});
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    page.setDefaultTimeout(10000);
    const errors=[],remote=[];page.on('pageerror',e=>errors.push(e.message));
    page.on('request',r=>{if(!r.url().startsWith(base))remote.push(r.url())});
    page.on('dialog',d=>d.accept());
    console.log('Browser checkpoint: page loaded');await page.goto(base);await page.locator('#stat-folders').filter({hasText:'19'}).waitFor();
    const chats=[{id:'synthetic-one',title:'Synthetic One',messages:[{role:'user',content:'Synthetic SQLite question',files:[{url:'https://example.invalid/private.png'}]}]},
      {id:'synthetic-two',title:'Synthetic Two',messages:[{role:'assistant',content:'Synthetic second answer'}]}];
    await page.locator('#file-input').setInputFiles({name:'synthetic.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(chats))});
    await page.waitForFunction(()=>document.getElementById('stat-chats').textContent==='2');
    console.log('Browser checkpoint: upload finished');await page.locator('#select-loaded').check();
    assert.match(await page.locator('#selected-count').textContent(),/^2 /);
    const folders=await (await fetch(base+'/api/folders')).json();
    const target=folders.find(f=>f.name==='ChatGPT'&&f.parent_id===null);
    await page.locator('#bulk-folder').selectOption(String(target.id));await page.locator('#bulk-assign').click();
    await page.waitForFunction(()=>document.getElementById('selected-count').textContent==='0 ausgewählt');
    for(const c of chats){const detail=await (await fetch(base+'/api/chat/'+c.id)).json();assert(detail.folders.includes(target.id))}
    console.log('Browser checkpoint: opening chat');await page.getByRole('button',{name:/Synthetic One/}).click();
    await page.getByRole('button',{name:'Tags bearbeiten',exact:true}).click();
    await page.getByLabel('Tags, durch Komma getrennt').fill('Alpha, Wissen');await page.locator('#modal-confirm').click();
    await page.locator('#detail .chip').filter({hasText:'# alpha'}).waitFor();
    const dropTarget=folders.find(f=>f.name==='Privat'&&f.parent_id===null);
    await page.locator('.chat-row').filter({hasText:'Synthetic One'}).dragTo(page.getByRole('button',{name:/▤ Privat/}));
    await page.waitForFunction(async({base,id})=>{
      const r=await fetch(base+'/api/chat/synthetic-one');return (await r.json()).folders.includes(id);
    },{base,id:dropTarget.id});
    console.log('Browser checkpoint: drag completed');await page.locator('#tag-filter').selectOption('alpha');
    await page.waitForFunction(()=>document.querySelectorAll('.chat-row').length===1);
    console.log('Browser checkpoint: tag filtered');await page.locator('#save-smart').click();await page.getByLabel('Name des intelligenten Ordners').fill('Synthetic Alpha');
    await page.locator('#modal-confirm').click();
    await page.getByRole('button',{name:'◇ Synthetic Alpha',exact:true}).waitFor();
    await page.getByRole('button',{name:'◇ Synthetic Alpha',exact:true}).click();
    assert(await page.locator('#search').isDisabled());
    const third={id:'synthetic-three',title:'Synthetic Three',messages:[{role:'user',content:'Synthetic third'}]};
    let response=await fetch(base+'/api/import',{method:'POST',headers:{'X-Filename':'synthetic.json'},body:JSON.stringify(third)});assert(response.ok);
    response=await fetch(base+'/api/bulk/tags',{method:'POST',body:JSON.stringify({conversation_ids:[third.id],tags:['alpha']})});assert(response.ok);
    await page.locator('#refresh').click();await page.waitForFunction(()=>document.querySelectorAll('.chat-row').length===2);
    console.log('Browser checkpoint: opening chat');await page.getByRole('button',{name:/Synthetic One/}).click();
    await page.locator('#detail summary').filter({hasText:'Quellen, Anhänge und Metadaten'}).click();
    assert.match(await page.locator('#detail').textContent(),/example.invalid/);
    assert.deepEqual(remote,[],'Imported references must not load remote assets');
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>{const buttons=[...document.querySelectorAll('#views button')];return buttons.slice(1).every((b,i)=>b.getBoundingClientRect().left>=buttons[i].getBoundingClientRect().right)}),'Mobile navigation buttons must not overlap');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile layout must fit viewport without horizontal overflow');
    await page.screenshot({path:path.join(directory,'mobile.png'),fullPage:true});
    assert(await page.locator('#bulk-tags').isVisible());
    assert.deepEqual(errors,[],'Browser must not raise JavaScript errors');
    console.log('PASS: streamed upload/progress, bulk selection, confirmed assignment, tags, drag-and-drop, dynamic smart folders, metadata safety, mobile layout');
    console.log('Synthetic screenshot: '+path.join(directory,'mobile.png'));
  }finally{
    if(browser)await browser.close();
    server.kill('SIGTERM');await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
    // Kept only when requested for inspecting synthetic screenshots.
    if(!process.env.KEEP_TEST_ARTIFACTS)await fs.rm(directory,{recursive:true,force:true});
  }
})().catch(e=>{console.error(e);process.exitCode=1});
