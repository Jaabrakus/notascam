(() => {
  'use strict';
  const E=SpriteEngine,$=id=>document.getElementById(id);
  let input=null,prepared=null,spec=null,result=null,packed=null,job=null,api=null,playing=false,playTime=0,polling=false;
  let revision=0,sourceConfig=null,loadingJob=false;
  window.workshopErrors=[];window.workshopReady=false;
  addEventListener('error',e=>window.workshopErrors.push(e.message));
  $('reference').src=ASSETS.reference;
  const controls=['cellWidth','cellHeight','directions','frames','offset','order','name','kind','outputSize','notes'];
  const notice=(message,error=false)=>{$('notice').textContent=message;$('notice').classList.toggle('error',error);};
  const run=fn=>async(...args)=>{try{await fn(...args);}catch(error){notice(error.message,true);}};
  function config() {return {width:+$('cellWidth').value,height:+$('cellHeight').value,dirs:+$('directions').value,frames:+$('frames').value,offset:+$('offset').value,order:$('order').value};}
  function options() {
    const state=input?.metadata?.states[+$('state').value];
    return {name:$('name').value,kind:$('kind').value,outputSize:+$('outputSize').value,notes:$('notes').value,
      state:state?.name??sourceConfig?.source?.state??'custom',movement:state?.movement??sourceConfig?.source?.movement??0,delays:state?.delays??sourceConfig?.source?.delays??[]};
  }
  function clearResult() {
    result=packed=null;$('export').disabled=true;$('outputState').textContent='Waiting for a redraw';
    $('reviewInfo').textContent='The AI redraw will appear here after Codex saves the result. You can also import a finished redraw.';
    $('resultCanvas').getContext('2d').clearRect(0,0,720,420);
    $('stepExport').classList.remove('active');
  }
  function changed() {
    revision++;job=null;$('jobHistory').value='';$('handoff').classList.add('hide');clearResult();
    $('stepRedraw').classList.remove('active');rebuild();
  }
  function rebuild() {
    if(!input)return;
    try {
      prepared=E.prepare(input,config());spec=E.specification(input,prepared,options());
      $('prepare').disabled=$('downloadRequest').disabled=false;
      $('inputInfo').textContent=`${prepared.dirs} directions · ${prepared.frames} frames · ${prepared.width} × ${prepared.height}`;
      const old=$('direction').value;$('direction').replaceChildren(...E.DIRECTIONS[prepared.dirs].map((d,i)=>new Option(d,i)));$('direction').value=+old<prepared.dirs?old:'0';
      $('frame').max=prepared.frames;$('frame').value=Math.min(+$('frame').value||1,prepared.frames);
      notice(`Ready to prepare ${prepared.cells.length} sprite cell${prepared.cells.length===1?'':'s'} for a GOA-style redraw.`);
      draw();
    } catch(error) {
      prepared=spec=null;$('prepare').disabled=$('downloadRequest').disabled=true;notice(error.message,true);
      $('sourceCanvas').getContext('2d').clearRect(0,0,720,420);
    }
  }
  function chooseState() {
    const state=input?.metadata?.states[+$('state').value];if(!state)return;
    $('cellWidth').value=input.metadata.width;$('cellHeight').value=input.metadata.height;
    $('directions').value=state.dirs;$('frames').value=state.frames;$('offset').value=state.offset;$('order').value='frame-major';
    changed();
  }
  async function importFile(file) {
    if(!file)return;
    const imported=await E.inspect(file);input=imported;sourceConfig=null;playing=false;
    $('name').value=file.name.replace(/\.[^.]+$/,'');
    $('state').replaceChildren();$('state').disabled=!input.metadata;
    if(input.metadata) {
      for(const [i,state] of input.metadata.states.entries())$('state').add(new Option(`${state.name||(state.movement?'Walk':'Idle')}${state.movement&&state.name?' · moving':''} · ${state.frames} frame${state.frames===1?'':'s'}`,i));
      chooseState();
    } else {
      $('state').add(new Option('Custom sheet layout',''));
      $('cellWidth').value=input.image.width;$('cellHeight').value=input.image.height;
      $('directions').value=1;$('frames').value=1;$('offset').value=0;$('order').value='frame-major';
      changed();
    }
    $('frame').value=1;$('direction').value=0;
  }
  function drawCanvas(target,image,columns,rows) {
    const c=target.getContext('2d');c.clearRect(0,0,target.width,target.height);if(!image)return;
    c.imageSmoothingEnabled=false;
    let x=0,y=0,w=image.width,h=image.height;
    if($('previewMode').value==='frame') {w/=columns;h/=rows;x=Math.min(+$('direction').value,columns-1)*w;y=(Math.min(+$('frame').value||1,rows)-1)*h;}
    const ratio=Math.min((target.width-40)/w,(target.height-40)/h,12),dw=Math.max(1,Math.round(w*ratio)),dh=Math.max(1,Math.round(h*ratio));
    c.drawImage(image,x,y,w,h,Math.round((target.width-dw)/2),Math.round((target.height-dh)/2),dw,dh);
  }
  function draw() {
    if(prepared)drawCanvas($('sourceCanvas'),prepared.canvas,prepared.dirs,prepared.frames);
    if(packed&&spec)drawCanvas($('resultCanvas'),packed,spec.output.columns,spec.output.rows);
  }
  function download(blob,name) {
    const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  const blobFromURL=async url=>(await fetch(url)).blob();
  const slug=()=>($('name').value.replace(/[^a-zA-Z0-9_-]+/g,'-').slice(0,80)||'sprite');
  async function requestBundle() {
    if(!spec)throw new Error('Import and configure a sprite first.');
    const message=E.requestText(spec);
    const entries=[['input-original.png',await blobFromURL(input.src)],['input-sheet.png',await blobFromURL(prepared.canvas.toDataURL())],
      ['style-reference.png',await blobFromURL(ASSETS.reference)],['request.json',JSON.stringify(spec,null,2)],
      ['request.md',`# GOA-style redraw\n\n${message}\n\n${spec.instructions}\n`]];
    download(await E.zip(entries),slug()+'-redraw.zip');
    return message;
  }
  async function apiCall(path,body) {
    const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Sprite-Token':api.token},body:JSON.stringify(body)});
    const value=await response.json();if(!response.ok)throw new Error(value.error||'Could not save the job.');return value;
  }
  async function prepareJob() {
    if(!spec)throw new Error('Import and configure a sprite first.');
    $('prepare').disabled=true;
    try {
      let message;
      if(api) {
        const pendingRevision=revision;
        const saved=await apiCall('/api/jobs',{spec,original:input.src,sheet:prepared.canvas.toDataURL()});
        if(revision!==pendingRevision)return;
        job=saved;message=E.requestText(spec,JSON.stringify(saved.path));await refreshHistory();
        $('handoffHint').textContent='The job is saved. Send this message in chat; the converted sheet will appear below when Codex saves result.png.';
      } else {
        message=await requestBundle();
        $('handoffHint').textContent='Attach the downloaded ZIP to this chat with this message. Import the finished redraw here afterward, or use the launcher to detect saved results automatically.';
      }
      $('requestMessage').value=message;$('handoff').classList.remove('hide');$('stepRedraw').classList.add('active');
      notice('Conversion job prepared. Send the message below here in Codex to start the AI redraw.');
    } finally {$('prepare').disabled=!spec;}
  }
  async function acceptResult(image,{save=false}={}) {
    if(!spec)throw new Error('Prepare the source sheet before importing its redraw.');
    const candidate=E.pack(image,spec);
    if(save&&job&&api) {
      const cv=E.canvas(image.width,image.height);cv.getContext('2d').drawImage(image,0,0);
      await apiCall('/api/jobs/'+job.id+'/result',{image:cv.toDataURL()});
    }
    result=image;packed=candidate;$('export').disabled=false;$('outputState').textContent='Redraw ready to review';$('stepExport').classList.add('active');
    const context=packed.getContext('2d'),p=context.getImageData(0,0,packed.width,packed.height).data;
    let transparency=false;for(let i=3;i<p.length;i+=4)if(p[i]<255){transparency=true;break;}
    $('reviewInfo').textContent=`${spec.output.columns} columns × ${spec.output.rows} rows · ${spec.output.frameWidth} × ${spec.output.frameHeight} pixels per cell. ${transparency?'Transparency detected.':'This result is fully opaque; review its background.'} Check that each pose and direction matches its source cell.`;
    notice('Redraw loaded. Review the poses and cell alignment, then export the packed sprite sheet.');draw();
  }
  async function exportSprites() {
    if(!packed)throw new Error('Load the finished redraw first.');
    const entries=[['sprites.png',await blobFromURL(packed.toDataURL())],['atlas.json',JSON.stringify(E.manifest(spec),null,2)],['redraw-request.json',JSON.stringify(spec,null,2)]];
    download(await E.zip(entries),slug()+'-sprites.zip');
  }
  async function refreshHistory() {
    if(!api)return;
    const jobs=await apiCall('/api/jobs'),value=job?.id||$('jobHistory').value;
    $('jobHistory').replaceChildren(new Option('Open a saved job…',''),...jobs.map(j=>new Option(`${j.name} · ${j.ready?'redraw ready':'waiting'}`,j.id)));
    $('jobHistory').value=value;
  }
  async function openJob(id) {
    if(!id||loadingJob)return;loadingJob=true;
    try {
      const saved=await apiCall('/api/jobs/'+id);
      const blob=await blobFromURL('/jobs/'+id+'/input-sheet.png');
      await importFile(new File([blob],saved.spec.source.filename,{type:'image/png'}));
      sourceConfig=saved.spec;
      const s=saved.spec;
      $('name').value=s.name;$('kind').value=s.kind;$('notes').value=s.notes;$('outputSize').value=s.output.frameWidth;
      $('cellWidth').value=s.source.frameWidth;$('cellHeight').value=s.source.frameHeight;$('directions').value=s.output.columns;$('frames').value=s.output.rows;
      changed();job=saved;$('jobHistory').value=id;
      // Preserve the original source provenance, DMI delays and state in an opened job.
      spec=s;$('requestMessage').value=E.requestText(spec,JSON.stringify(saved.path));$('handoff').classList.remove('hide');$('stepRedraw').classList.add('active');
      $('handoffHint').textContent='This saved job is ready to send to Codex. The converter will detect its result.png.';
      if(saved.ready)await acceptResult(await E.loadImage('/jobs/'+id+'/result.png?v='+saved.resultVersion));
      else notice('Saved job opened. Waiting for its AI redraw.');
    } finally {loadingJob=false;}
  }
  async function poll() {
    if(!api||!job||result||polling||loadingJob)return;polling=true;
    const id=job.id,jobRevision=revision;
    try {
      const saved=await apiCall('/api/jobs/'+id);
      if(saved.ready) {
        const image=await E.loadImage('/jobs/'+id+'/result.png?v='+saved.resultVersion);
        if(job?.id===id&&revision===jobRevision&&!loadingJob) {await acceptResult(image);await refreshHistory();}
      }
    } catch(error) {if(job?.id===id)notice(error.message,true);}finally{polling=false;}
  }
  $('drop').onclick=()=>$('inputFile').click();$('drop').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('inputFile').click();}};
  for(const event of ['dragenter','dragover'])$('drop').addEventListener(event,e=>{e.preventDefault();$('drop').classList.add('drag');});
  for(const event of ['dragleave','drop'])$('drop').addEventListener(event,e=>{e.preventDefault();$('drop').classList.remove('drag');});
  $('drop').addEventListener('drop',run(e=>importFile(e.dataTransfer.files[0])));
  $('inputFile').onchange=run(async e=>{await importFile(e.target.files[0]);e.target.value='';});
  $('resultFile').onchange=run(async e=>{const f=e.target.files[0];if(!f)return;const {image}=await E.inspect(f);await acceptResult(image,{save:true});e.target.value='';});
  $('example').onclick=run(async()=>{const blob=await blobFromURL(ASSETS.example);await importFile(new File([blob],'Dungeon Master Human.dmi',{type:'image/png'}));});
  $('state').onchange=chooseState;
  for(const id of controls)$(id).addEventListener('change',changed);
  for(const id of ['previewMode','direction','frame'])$(id).addEventListener('change',draw);
  $('prepare').onclick=run(prepareJob);$('downloadRequest').onclick=run(requestBundle);$('export').onclick=run(exportSprites);
  $('jobHistory').onchange=run(e=>openJob(e.target.value));
  $('copyRequest').onclick=run(async()=>{try{await navigator.clipboard.writeText($('requestMessage').value);$('copyRequest').textContent='Copied';}catch{$('requestMessage').select();notice('Select and copy the message, then send it here in Codex.');}});
  $('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'Ⅱ':'▶';$('previewMode').value='frame';draw();};
  function tick(time) {
    if(playing&&prepared&&time-playTime>150) {$('frame').value=(+$('frame').value%prepared.frames)+1;playTime=time;draw();}
    requestAnimationFrame(tick);
  }
  async function initialize() {
    if(location.protocol!=='file:') {
      try {api=await apiCall('/api/info');$('connection').textContent='● Local jobs connected · redraws here in Codex';$('connection').classList.add('ready-dot');await refreshHistory();const requestedJob=new URL(location.href).searchParams.get('job');if(requestedJob)await openJob(requestedJob);}
      catch {$('historyHint').textContent='Open the launcher to save jobs automatically. ZIP bundles still work.';}
    } else {$('historyHint').textContent='Use the launcher for saved jobs, or download a bundle and attach it here.';}
    window.workshopReady=true;requestAnimationFrame(tick);
  }
  window.workshop={get spec(){return spec;},get job(){return job;},get prepared(){return prepared;},get packed(){return packed;},importFile,acceptResult,openJob,prepareJob};
  initialize().catch(error=>notice(error.message,true));setInterval(poll,2000);
})();
