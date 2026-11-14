// Optional integration check: Node + Playwright + a system Chromium are required.
// Uses only synthetic data and an isolated temporary database.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');

(async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'chatidy-browser-'));
  const reservation=net.createServer();await new Promise(r=>reservation.listen(0,'127.0.0.1',r));
  const port=reservation.address().port;await new Promise(r=>reservation.close(r));
  const root=path.resolve(__dirname,'..'),base=`http://127.0.0.1:${port}`;
  const appEnv={...process.env,CHATIDY_PORT:String(port),CHATIDY_DB:path.join(directory,'synthetic.sqlite3')};
  const server=spawn(process.env.PYTHON||'python',['-m','chatidy'],{cwd:root,env:appEnv,stdio:'ignore'});
  let browser,jobWorker;
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
    let acceptDialogs=true;const dialogs=[];
    page.on('dialog',d=>{dialogs.push(d.message());return acceptDialogs?d.accept():d.dismiss()});
    console.log('Browser checkpoint: page loaded');await page.goto(base);await page.locator('#stat-folders').filter({hasText:'19'}).waitFor();
    const chats=[{id:'synthetic-one',title:'Synthetic One',messages:[{role:'user',content:'Synthetic SQLite question',files:[{url:'https://example.invalid/private.png'}]}]},
      {id:'synthetic-two',title:'Synthetic Two',messages:[{role:'assistant',content:'Synthetic second answer'}]}];
    await page.locator('#file-input').setInputFiles({name:'synthetic.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(chats))});
    await page.locator('#confirm-batch').waitFor();
    assert.equal((await (await fetch(base+'/api/stats')).json()).chats,0,'Preview must not import chats');
    const readyJob=await page.evaluate(()=>localStorage.getItem('chatidy-import-job'));
    assert.equal((await (await fetch(base+'/api/import/jobs/'+readyJob)).json()).active,false,'Confirmation waits for the analyzer lease to close');
    assert.match(await page.locator('#import-preview').textContent(),/2 erkannte Gespräche/);
    await page.locator('#confirm-batch').click();
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
    await page.getByText('Lokale Importjobs verwalten',{exact:true}).click();
    await page.locator('#job-list .job-row').waitFor();
    const stored=await (await fetch(base+'/api/import/jobs')).json();
    assert.equal(stored.count,1);assert(stored.storage_bytes>0);
    const successful=page.locator('.job-row[data-job-id="'+stored.jobs[0].id+'"]');
    assert.match(await successful.textContent(),/Erfolgreich.*Erstellt:/s);
    acceptDialogs=false;await successful.getByRole('button',{name:'Jobdaten löschen',exact:true}).click();
    assert.equal((await (await fetch(base+'/api/import/jobs')).json()).count,1);
    acceptDialogs=true;await successful.getByRole('button',{name:'Jobdaten löschen',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('#job-list .job-row').length===0);
    assert.equal((await (await fetch(base+'/api/stats')).json()).chats,3);
    const failedResponse=await fetch(base+'/api/import/jobs',{method:'POST',headers:{'X-Filename':'synthetic.json'},body:'not json'});
    const failed=(await failedResponse.json()).id;
    await page.waitForFunction(async({base,id})=>(await (await fetch(base+'/api/import/jobs/'+id)).json()).state==='error',{base,id:failed});
    jobWorker=spawn(process.env.PYTHON||'python',['-u','-c',
      "import sys,time\nfrom chatidy import jobs\noriginal=jobs.iter_export\ndef paused(*args):\n print('VALIDATING',flush=True)\n time.sleep(60)\n yield from original(*args)\njobs.iter_export=paused\njobs.run(sys.argv[1])",failed],{cwd:root,env:appEnv,stdio:['ignore','pipe','ignore']});
    await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Worker startup timeout')),5000);jobWorker.stdout.on('data',data=>{if(String(data).includes('VALIDATING')){clearTimeout(timeout);resolve()}})});
    await page.locator('#refresh-jobs').click();
    const failedRow=page.locator('.job-row[data-job-id="'+failed+'"]');
    await failedRow.locator('.job-state').filter({hasText:'In Prüfung'}).waitFor();
    assert(await failedRow.getByRole('button',{name:'Jobdaten löschen',exact:true}).isDisabled());
    jobWorker.kill('SIGKILL');await new Promise(resolve=>jobWorker.once('exit',resolve));jobWorker=null;
    await page.locator('#refresh-jobs').click();
    await failedRow.locator('.job-state').filter({hasText:'Unterbrochen'}).waitFor();
    await failedRow.getByRole('button',{name:'Fortsetzen',exact:true}).click();
    await failedRow.locator('.job-state').filter({hasText:'Fehlgeschlagen'}).waitFor();
    acceptDialogs=false;await failedRow.getByRole('button',{name:'Jobdaten löschen',exact:true}).click();
    assert(dialogs.at(-1).includes('Wiederaufnahme ist danach nicht mehr möglich'));
    assert.equal((await (await fetch(base+'/api/import/jobs')).json()).count,1);
    acceptDialogs=true;await failedRow.getByRole('button',{name:'Jobdaten löschen',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('#job-list .job-row').length===0);
    assert.equal((await (await fetch(base+'/api/chats?q=SQLite')).json()).length,1);
    const synthetic=spawnSync(process.env.PYTHON||'python',['-c',
      "import sys,json,base64;sys.path.insert(0,'tests');from test_archives import archive;from test_segmented_exports import segmented,conversation;print(json.dumps({'zip':base64.b64encode(archive(segmented())).decode(),'single':conversation(0)}))"],{cwd:root,encoding:'utf8'});
    assert.equal(synthetic.status,0,synthetic.stderr);const bundle=JSON.parse(synthetic.stdout);
    let seed=await fetch(base+'/api/import',{method:'POST',headers:{'X-Filename':'conversations-000.json'},body:JSON.stringify([bundle.single])});assert(seed.ok);
    async function waitDone(id){await page.waitForFunction(async({base,id})=>{const value=await (await fetch(base+'/api/import/jobs/'+id)).json();return value.state==='done'&&!value.active},{base,id})}
    for(let iteration=0;iteration<2;iteration++){
      await page.locator('#file-input').setInputFiles({name:'synthetic-segmented.zip',mimeType:'application/zip',buffer:Buffer.from(bundle.zip,'base64')});
      await page.locator('#confirm-batch').waitFor();
      assert.match(await page.locator('#import-preview').textContent(),/Nummerierter offizieller Export.*8 Konversationsdateien.*8 erkannte Gespräche/s);
      assert.equal((await (await fetch(base+'/api/stats')).json()).chats,iteration?11:4);
      const planned=await page.evaluate(()=>localStorage.getItem('chatidy-import-job'));
      await page.locator('#confirm-batch').click();await waitDone(planned);
      const report=await (await fetch(base+'/api/import/jobs/'+planned)).json();
      assert.equal(report.result.imported,iteration?0:7);assert.equal(report.result.unchanged,iteration?8:1);
      assert.equal((await (await fetch(base+'/api/stats')).json()).chats,11);
      await page.waitForFunction(()=>document.getElementById('import-preview').hidden);
    }
    const old={...bundle.single,update_time:10};
    await page.locator('#file-input').setInputFiles({name:'synthetic-old.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify([old]))});
    await page.locator('#confirm-batch').waitFor();
    assert(await page.locator('#confirm-batch').isDisabled());
    await page.locator('#import-preview select').selectOption('skip');
    const oldJob=await page.evaluate(()=>localStorage.getItem('chatidy-import-job'));
    await page.locator('#confirm-batch').click();await waitDone(oldJob);
    assert.equal((await (await fetch(base+'/api/chat/synthetic-0')).json()).chat.updated,20);
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>{const buttons=[...document.querySelectorAll('#views button')];return buttons.slice(1).every((b,i)=>b.getBoundingClientRect().left>=buttons[i].getBoundingClientRect().right)}),'Mobile navigation buttons must not overlap');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile layout must fit viewport without horizontal overflow');
    await page.screenshot({path:path.join(directory,'mobile.png'),fullPage:true});
    assert(await page.locator('#bulk-tags').isVisible());
    assert.deepEqual(errors,[],'Browser must not raise JavaScript errors');
    console.log('PASS: preview before writes, segmented ZIP after single-file import, full reimport, class-scoped older skip, native job/organisation baseline and mobile layout');
    console.log('Synthetic screenshot: '+path.join(directory,'mobile.png'));
  }finally{
    if(jobWorker){jobWorker.kill('SIGKILL');await new Promise(resolve=>jobWorker.exitCode!==null||jobWorker.signalCode!==null?resolve():jobWorker.once('exit',resolve))}
    if(browser)await browser.close();
    server.kill('SIGTERM');await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
    // Kept only when requested for inspecting synthetic screenshots.
    if(!process.env.KEEP_TEST_ARTIFACTS)await fs.rm(directory,{recursive:true,force:true});
  }
})().catch(e=>{console.error(e);process.exitCode=1});
