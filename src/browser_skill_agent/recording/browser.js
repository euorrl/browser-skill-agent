// 每个页面及 iframe 独立安装；只观察用户事件，不阻止网页原有行为。
(async () => {
  if (window.__bsaRecorderInstalled) return;
  window.__bsaRecorderInstalled = true;
  const config = await window.__bsaRecorderReady();
  if (!config) return;
  const documentId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random();
  let active = true;
  let sequence = 0, nodeSequence = 0, lastAction = null, observationTimer = null, lastSnapshot = '';
  const keys = new WeakMap();
  const pending = new Set();
  const short = (v, n=300) => String(v ?? '').replace(/\s+/g, ' ').trim().slice(0,n);
  const sensitive = e => e && (e.matches('input[type=password]') ||
    /password|one-time-code/i.test(e.autocomplete || '') ||
    /password|passwd|secret|token|验证码|密码|captcha|(^|[_-])otp([_-]|$)/i.test([e.name,e.id,e.getAttribute('aria-label')].join(' ')));
  const safeText = e => {
    if (!e || sensitive(e)) return '';
    const copy = e.cloneNode(true);
    copy.querySelectorAll('script,style,noscript,input,textarea,[contenteditable],svg').forEach(n => n.remove());
    return short(copy.textContent, 300);
  };
  const label = e => short(e.getAttribute('aria-label') ||
    (e.getAttribute('aria-labelledby') || '').split(' ').map(id => document.getElementById(id)?.textContent || '').join(' ') ||
    [...(e.labels || [])].map(l => safeText(l)).join(' '));
  const role = e => e.getAttribute('role') || ({BUTTON:'button',A:e.hasAttribute('href')?'link':null,
    SELECT:'combobox',TEXTAREA:'textbox',INPUT:({checkbox:'checkbox',radio:'radio',number:'spinbutton',button:'button',submit:'button'})[e.type] || 'textbox'})[e.tagName] || null;
  function describe(e) {
    if (!e || e.nodeType !== 1) return {};
    const r = role(e), l = label(e);
    const name = l || (['button','link','option','tab'].includes(r) ? safeText(e) : '');
    const candidates = [];
    if (r && name) candidates.push({role:r,name});
    if (l) candidates.push({label:l});
    if (e.placeholder) candidates.push({placeholder:short(e.placeholder)});
    if (e.id) candidates.push({id:e.id});
    const test = e.getAttribute('data-testid') || e.getAttribute('data-test');
    if (test) candidates.push({test_id:test});
    const text = safeText(e);
    if (text && !['INPUT','TEXTAREA','SELECT'].includes(e.tagName)) candidates.push({text});
    const container = e.parentElement?.closest('form,dialog,[role=dialog],article,[role=row],li,main');
    return {tag:e.tagName.toLowerCase(),role:r,name,label:l,id:e.id || null,
      input_type:e.type || null, candidates, sensitive:!!sensitive(e),
      container:container ? {tag:container.tagName.toLowerCase(),id:container.id || null,role:role(container),name:label(container),text:safeText(container)} : null};
  }
  function snapshot() {
    const root = document.querySelector('main,[role=main]') || document.body;
    if (!root) return {text:'',truncated:false};
    const walker = document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const texts = []; let length = 0, truncated = false;
    while (walker.nextNode()) {
      const node = walker.currentNode, e = node.parentElement;
      if (!e || e.closest('script,style,noscript,input,textarea,[contenteditable],[hidden],[aria-hidden=true]')) continue;
      if (!e.getClientRects().length || getComputedStyle(e).visibility === 'hidden') continue;
      const text = short(node.textContent,1000);
      if (!text) continue;
      texts.push(text); length += text.length;
      if (length > 4000) {truncated=true;break;}
    }
    const nodes=[...root.querySelectorAll('input,textarea,select,button,[role=button],[aria-expanded],[aria-selected],[aria-busy]')].filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
    const controls=nodes.slice(0,30).map(e=>({id:e.id||null,role:role(e),name:label(e)||(['BUTTON','A'].includes(e.tagName)?safeText(e):''),
      enabled:!e.matches(':disabled')&&e.getAttribute('aria-disabled')!=='true',
      checked:['checkbox','radio'].includes(e.type)?e.checked:null,
      expanded:e.getAttribute('aria-expanded'),selected:e.getAttribute('aria-selected'),busy:e.getAttribute('aria-busy'),
      value:!sensitive(e)&&e.type!=='file'&&'value' in e?String(e.value).slice(0,300):null}));
    return {text:texts.join('\n').slice(0,4000),truncated,controls,controls_truncated:nodes.length>30};
  }
  function emit(type, data={}) {
    const eventId = documentId + ':' + (++sequence);
    const message = {recording_id:config.id,event_id:eventId,document_id:documentId,
      client_time:Date.now(),type,url:location.href,title:short(document.title),...data};
    const promise = window.__bsaRecord(message).catch(() => {}).finally(() => pending.delete(promise));
    pending.add(promise);
    return eventId;
  }
  function action(type,e,data={}) {
    if (!active) return null;
    if (!keys.has(e)) keys.set(e,documentId+':node'+(++nodeSequence));
    lastAction = emit(type,{element_key:keys.get(e),target:describe(e),before:{url:location.href,context:safeText(e.parentElement)},...data});
    observeSoon();
    return lastAction;
  }
  function observe() {
    const content = snapshot(), signature = JSON.stringify(content) + location.href;
    if (signature !== lastSnapshot) {
      lastSnapshot = signature;
      emit('observation',{related_event:lastAction,...content});
    }
  }
  function observeSoon() {
    if (!active || observationTimer) return;
    observationTimer=setTimeout(() => {observationTimer=null;observe();},500);
  }
  const element = event => event.composedPath().find(n => n instanceof Element);
  const usable = e => e?.closest('input,textarea,select,[contenteditable=true]');
  document.addEventListener('input', event => {
    if (!active || !event.isTrusted) return;
    const e=usable(element(event));
    if (!e || e.matches('input[type=file],input[type=checkbox],input[type=radio],select')) return;
    action('input',e,{value:sensitive(e)?null:String(e.isContentEditable?e.innerText:e.value).slice(0,8000),value_truncated:!sensitive(e)&&String(e.isContentEditable?e.innerText:e.value).length>8000,redacted:!!sensitive(e)});
  },true);
  document.addEventListener('click', event => {
    if (!active || !event.isTrusted) return;
    const raw=element(event), e=raw?.closest('button,a,[role=button],[role=option],[role=tab],[role=treeitem],input,select,label') || raw;
    if (!e || e.matches('input,select,textarea') || (e.tagName==='LABEL' && e.control)) return;
    action(event.detail===2?'double_click':'click',e);
  },true);
  document.addEventListener('change', async event => {
    if (!active || !event.isTrusted) return;
    const e=element(event);
    if (e?.matches('select')) action('select',e,{options:[...e.selectedOptions].map(o=>({label:o.label,value:o.value}))});
    else if(e?.matches('input[type=checkbox],input[type=radio]')) action('set_checked',e,{checked:e.checked});
    else if(e?.matches('input[type=file]')) {
      const files=[...e.files].map(f=>({name:f.name,size:f.size,mime:f.type,last_modified:f.lastModified,sha256:null}));
      const related=action('upload',e,{files});
      const originals=[...e.files];
      const hashes=Promise.all(originals.map(async (f,i)=>{
        if (crypto.subtle && f.size<=16*1024*1024) {
          try {const hash=await crypto.subtle.digest('SHA-256',await f.arrayBuffer()); files[i].sha256=[...new Uint8Array(hash)].map(v=>v.toString(16).padStart(2,'0')).join('');}
          catch {files[i].hash_note='无法计算哈希';}
        } else files[i].hash_note='文件超过16MiB或当前页面不支持摘要计算';
      })).then(()=>emit('file_hash',{related_event:related,files})).finally(()=>pending.delete(hashes));
      pending.add(hashes);
    }
  },true);
  document.addEventListener('keydown',event=>{
    if (!active || !event.isTrusted || !['Enter','Tab','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)) return;
    const e=element(event);if(e) action('press',e,{key:event.key});
  },true);
  let scrollTimer;
  document.addEventListener('scroll',()=>{
    clearTimeout(scrollTimer);scrollTimer=setTimeout(()=>emit('scroll',{x:scrollX,y:scrollY,related_event:lastAction}),350);
  },true);
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')emit('page_active');});
  window.addEventListener('focus',()=>emit('page_active'));
  window.addEventListener('hashchange',()=>{emit('navigation_observed');observeSoon();});
  window.addEventListener('popstate',()=>{emit('navigation_observed');observeSoon();});
  const observer = new MutationObserver(observeSoon);
  observer.observe(document,{subtree:true,childList:true,characterData:true,attributes:true,
    attributeFilter:['disabled','hidden','aria-busy','aria-expanded','aria-selected','aria-checked','class','style']});
  const stateTimer=setInterval(()=>{if(active)observe();},1000);
  window.__bsaRecorderFlush=async(freeze=false)=>{if(freeze){active=false;observer.disconnect();clearTimeout(observationTimer);clearTimeout(scrollTimer);clearInterval(stateTimer);}observe();while(pending.size)await Promise.allSettled([...pending]);};
  emit('document_ready');observeSoon();
})();
