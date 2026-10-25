const $=id=>document.getElementById(id);
let state={flows:[]}, selected=null, pendingId=null, lastList='', confirmAction=null, chatting=false;
let displayedJob=null, completedJob=null, conversationVersion=0, planningAfterJob=false, jobSignature='';
let guidanceShown=null;
const labels={username:'登录账号',password:'登录密码',search_keyword:'搜索关键词',query:'查询内容',keyword:'关键词',topic_a:'第一个主题',topic_b:'第二个主题',quantity:'数量',product_name:'商品名称',category:'分类',source_file:'上传文件',download_dir:'下载目录',output_dir:'保存目录'};
const statusText={unverified:'待验证',passed:'运行通过',verified:'双模式验证通过',blocked:'需要调整'};
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,5500);}
async function api(command,data={}){const result=await window.__flowStudio(command,data);if(result.error){toast(result.error);throw Error(result.error);}return result;}
async function refresh(){try{state=await api('state');render();}catch{}}
function render(){
 $('count').textContent=$('navCount').textContent=state.flows.length;
 const signature=JSON.stringify(state.flows)+$('search').value+$('filter').value;
 if(signature!==lastList){lastList=signature;renderCards();}
 renderJob(state.job);
 if(state.pending){pendingId=state.pending.id;$('approvalDialog').querySelector('h2').textContent=state.pending.kind==='login'?'需要登录':'此操作需要你的确认';$('approve').textContent=state.pending.kind==='login'?'登录完成，继续':'允许操作';$('deny').textContent=state.pending.kind==='login'?'停止任务':'拒绝';$('approvalDialog').querySelector('p.small').textContent=state.pending.kind==='login'?'请在已显示的任务浏览器登录；继续前会检查页面状态。':'仅批准当前这一次操作。';$('approvalMessage').textContent=state.pending.message;$('approvalDetails').textContent=JSON.stringify(state.pending.details,null,2);if(!$('approvalDialog').open)$('approvalDialog').showModal();}
 else if($('approvalDialog').open){$('approvalDialog').close();pendingId=null;}
}
function clearConversation(){conversationVersion++;$('messages').replaceChildren();}
function terminal(job){return ['done','blocked','failed','cancelled'].includes(job?.state);}
function renderJob(job){
 $('job').hidden=!job;if(!job)return;
 if(displayedJob!==job.id){
  displayedJob=job.id;completedJob=null;planningAfterJob=false;jobSignature='';clearConversation();
  message((job.kind==='run'?'开始运行：':'开始任务：')+(job.name||'录制新流程'),'user');
  const running=node('div','message bot','正在准备…');running.id='taskProgress';$('messages').append(running);
  const bar=node('div','job-bar'),label=node('strong','job-label'),actions=node('div','job-actions');label.id='jobLabel';actions.id='jobActions';bar.append(label,actions);
  const logs=node('details','job-logs'),summary=node('summary','','展开运行日志'),pre=node('pre');logs.id='jobLogs';pre.id='logText';logs.append(summary,pre);logs.ontoggle=()=>summary.textContent=logs.open?'收起运行日志':'展开运行日志';
  $('job').replaceChildren(bar,logs);
 }
 $('jobLabel').textContent=({working:'正在准备',running:'正在运行',recording:'正在录制',saving:'正在保存',guidance:'录制完成 · 可补充说明',generating:'正在生成',cancelling:'正在取消 · 清理记录',cancelled:'已取消生成',validating:'正在验证与修复',done:'任务完成',blocked:'任务未完成',failed:'任务失败'})[job.state]||'任务进度';
 if(job.mode)$('jobLabel').textContent+=' · '+(job.mode==='llm'?'LLM 运行':'固定步骤');
 if(job.state==='guidance'&&guidanceShown!==job.id)showGuidance();
 if(job.state!=='guidance'&&$('guidanceDialog').open)$('guidanceDialog').close();
 const signature=JSON.stringify([job.state,job.browser_open,job.flow_id,job.recording_id]);
 if(signature!==jobSignature){
  jobSignature=signature;const actions=$('jobActions');actions.replaceChildren();
  if(job.state==='recording'){
   button(actions,'结束并生成',()=>api('record_stop').then(refresh));
   button(actions,'重新录制',()=>confirm('重新开始录制？','当前记录将被放弃，已发生的网站操作不会撤销。',()=>api('record_restart').then(refresh)));
  }
  if(job.state==='validating')button(actions,'停止验证',()=>api('cancel_validation').then(refresh));
  if(['guidance','generating'].includes(job.state))button(actions,'取消生成并删除记录',cancelGeneration);
  if(job.state==='guidance')button(actions,'补充说明或直接生成',showGuidance,'primary');
  if(job.browser_open)button(actions,'关闭任务浏览器',()=>api('close_browser').then(refresh),'primary');
  if(job.state==='done'&&job.kind==='record'&&job.flow_id)button(actions,'查看新流程',()=>openFlow(job.flow_id));
  if(job.state==='failed'&&job.recording_id)button(actions,'重新生成流程',()=>api('generate_again').then(refresh));
 }
 const pre=$('logText'),text=(job.logs||[]).map(x=>`[${new Date(x.time).toLocaleTimeString()}] ${x.text}`).join('\n');
 if(pre.textContent!==text){const atBottom=pre.scrollHeight-pre.scrollTop-pre.clientHeight<30;pre.textContent=text||'日志将在执行时显示。';if(atBottom)pre.scrollTop=pre.scrollHeight;}
 const running=$('taskProgress');if(running&&!terminal(job))running.textContent=job.message;
 if(terminal(job)&&completedJob!==job.id){
  completedJob=job.id;if(running)running.remove();
  message(`${job.state==='done'?'已完成':job.state==='cancelled'?'已取消':'未完成'} · ${job.name||'录制任务'}\n${job.message}`);
  for(const output of job.result?.outputs||[]){
   const detail=node('details','chat-result'),summary=node('summary','',output.title||'读取结果');
   detail.append(summary,node('pre','',typeof output.data==='string'?output.data:JSON.stringify(output.data,null,2)));$('messages').append(detail);
  }
  if(job.result?.url)message('最后页面：'+job.result.url);
  $('messages').scrollTop=$('messages').scrollHeight;
 }
}
function button(parent,text,action,cls='secondary'){const b=node('button',cls,text);b.onclick=()=>Promise.resolve(action()).catch(()=>{});parent.append(b);return b;}
function showGuidance(){
 const job=state.job;if(!job||job.state!=='guidance')return;
 if(guidanceShown!==job.id){$('guidanceName').value=job.requested_name||'';$('guidanceDescription').value='';$('guidanceParameters').value='';guidanceShown=job.id;}
 if(!$('guidanceDialog').open)$('guidanceDialog').showModal();
}
async function cancelGeneration(){
 await api('cancel_generation',{job_id:state.job.id});
 $('guidanceDialog').close();
 await refresh();
}
$('cancelGeneration').onclick=()=>cancelGeneration().catch(()=>{});
async function submitGuidance(skip){
 const buttons=$('guidanceForm').querySelectorAll('button');buttons.forEach(b=>b.disabled=true);
 try{await api('guidance',{job_id:state.job.id,guidance:skip?{}:{name:$('guidanceName').value,description:$('guidanceDescription').value,parameters:$('guidanceParameters').value}});$('guidanceDialog').close();await refresh();}
 finally{buttons.forEach(b=>b.disabled=false);}
}
$('guidanceForm').onsubmit=e=>{e.preventDefault();submitGuidance(false).catch(()=>{});};
$('skipGuidance').onclick=()=>submitGuidance(true).catch(()=>{});
function renderCards(){
 const items=state.flows.filter(f=>f.name.toLowerCase().includes($('search').value.toLowerCase())&&($('filter').value==='all'||f.status===$('filter').value));
 $('flows').replaceChildren();$('empty').hidden=items.length>0;
 for(const f of items){const card=node('article','card'),top=node('div','card-top');top.append(node('span','flow-icon','↗'),node('span','badge '+f.status,statusText[f.status]||'待验证'));
 card.append(top,node('h3','',f.name),node('p','',f.description));const bottom=node('div','card-bottom'),actions=node('div','card-actions');bottom.append(node('span','',`${Object.keys(f.defaults).length} 项参数 · ${f.validation?'最近已验证':(f.last_result?'最近已运行':'尚未运行')}`),actions);
 button(actions,'···',()=>openFlow(f.id,null,true),'mini').setAttribute('aria-label','编辑'+f.name);
 button(actions,'▶ 运行',()=>openFlow(f.id),'mini run');card.append(bottom);$('flows').append(card);}
}
function parameterFields(container,values){container.replaceChildren();for(const [key,value] of Object.entries(values)){const label=node('label','',labels[key]||key.replaceAll('_',' ')),input=node('input');input.value=value;input.dataset.param=key;if(selected?.secret_params?.includes(key)){input.type='password';input.value='';input.autocomplete='new-password';}input.placeholder=selected?.secret_params?.includes(key)?'仅本次会话使用；留空沿用已填写密码':'请输入'+(labels[key]||key);label.append(input);container.append(label);}if(!Object.keys(values).length)container.append(node('p','small','此流程不需要填写参数。'));}
function parameters(id){return Object.fromEntries([...$(id).querySelectorAll('[data-param]')].map(e=>[e.dataset.param,e.value]));}
function tab(id){for(const name of ['runPanel','editPanel'])$(name).hidden=name!==id;for(const b of document.querySelectorAll('[data-tab]'))b.classList.toggle('selected',b.dataset.tab===id);}
async function openFlow(id,params=null,edit=false){
 $('enableLlm').checked=false;$('approvalMode').value='human';$('approvalMode').onchange();
 const detail=await api('details',{id});selected=detail.flow;$('flowTitle').textContent=selected.name;$('flowDescription').textContent=selected.description;$('editName').value=selected.name;
 parameterFields($('params'),params||selected.defaults);parameterFields($('editParams'),selected.defaults);
 $('steps').replaceChildren(...detail.steps.map(s=>node('li','',s)));
 $('issueBox').hidden=!selected.issues.length;
 $('issueBox').textContent=selected.issues.length?`此流程还有 ${selected.issues.length} 项待验证内容。首次运行可能中止，请留意运行结果。`:'';
 tab(edit?'editPanel':'runPanel');if(!$('flowDialog').open)$('flowDialog').showModal();
}
function confirm(title,text,action){$('confirmTitle').textContent=title;$('confirmText').textContent=text;confirmAction=action;$('confirmDialog').showModal();}
document.querySelectorAll('.close').forEach(b=>b.onclick=()=>b.closest('dialog').close());
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>tab(b.dataset.tab));
$('confirmCancel').onclick=()=>$('confirmDialog').close();$('confirmOk').onclick=async()=>{$('confirmDialog').close();try{await confirmAction();}catch{}};
$('search').oninput=render;$('filter').onchange=render;
$('newFlow').onclick=()=>$('recordDialog').showModal();
$('recordForm').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await api('record',{name:$('recordName').value,url:$('recordUrl').value,auto_validate:$('autoValidate').checked});$('recordDialog').close();await refresh();}finally{b.disabled=false;}};
$('runFlow').onclick=async()=>{try{await api('run',{id:selected.id,params:parameters('params'),close_after:$('closeAfter').checked,approval:$('approvalMode').value,llm:$('enableLlm').checked,background:$('backgroundRun').checked});$('flowDialog').close();$('params').querySelectorAll('input[type=password]').forEach(e=>e.value='');await refresh();}catch{}};
$('saveFlow').onclick=async()=>{try{await api('update',{id:selected.id,name:$('editName').value,defaults:parameters('editParams')});$('flowDialog').close();$('editParams').querySelectorAll('input[type=password]').forEach(e=>e.value='');toast('流程已保存');await refresh();}catch{}};
$('deleteFlow').onclick=()=>confirm('删除这个流程？','将永久删除此流程及关联的录制、Skill 和验证文件。其他流程共用的记录、用户上传原件和日常下载文件会保留，此操作不可撤销。',async()=>{await api('delete',{id:selected.id});$('flowDialog').close();clearConversation();await refresh();toast('流程已删除');});
async function answer(approved){try{await api('answer',{id:pendingId,approved});$('approvalDialog').close();await refresh();}catch{}}
$('approve').onclick=()=>answer(true);$('deny').onclick=()=>answer(false);$('approvalDialog').addEventListener('cancel',e=>{e.preventDefault();answer(false);});
function message(text,who='bot'){const welcome=document.querySelector('.welcome');if(welcome)welcome.remove();$('messages').append(node('div','message '+who,text));$('messages').scrollTop=$('messages').scrollHeight;}
$('chatForm').onsubmit=async e=>{e.preventDefault();if(chatting)return;const text=$('chatInput').value.trim();if(!text)return;if(terminal(state.job)&&!planningAfterJob){clearConversation();planningAfterJob=true;}const version=conversationVersion;chatting=true;$('send').disabled=true;$('chatInput').value='';message(text,'user');const waiting=node('div','message','正在分析需求，准备流程或修改方案…');$('messages').append(waiting);
 try{const result=await api('chat',{text});if(version!==conversationVersion||result.stale)return;waiting.remove();message(result.message);if(result.action==='edit'){renderEdit(result);}else if(result.flow_id&&result.action!=='clarification'){const f=state.flows.find(x=>x.id===result.flow_id),plan=node('div','plan');plan.append(node('strong','',f?f.name:'已选择流程'));for(const [k,v] of Object.entries(result.params))plan.append(node('p','small',`${labels[k]||k}：${v||'待填写'}`));button(plan,'检查参数并运行',()=>openFlow(result.flow_id,result.params),'primary');$('messages').append(plan);}}
 catch{waiting.textContent='暂时无法完成匹配。你仍可在左侧直接选择流程。';}finally{chatting=false;$('send').disabled=false;$('messages').scrollTop=$('messages').scrollHeight;}};
document.querySelectorAll('.suggestion').forEach(b=>b.onclick=()=>{$('chatInput').value=b.dataset.text;$('chatInput').focus();});
$('chatInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('chatForm').requestSubmit();}});
refresh();setInterval(refresh,1000);

$('approvalMode').onchange=()=>{$('approvalHint').textContent=({human:'搜索、筛选和普通导航直接执行；关键操作在此确认。',ai:'关键操作由模型审核，会发送相关页面信息并消耗 Token。',allow:'本次流程的所有操作均直接执行，包括提交、上传、删除等。'})[$('approvalMode').value];};

function renderEdit(result){
 const card=node('div','plan');card.append(node('strong','','修改流程：'+result.before.name));
 for(const [label,value] of [['修改前',result.before],['修改后',result.after]]){
  card.append(node('p','small',label+'：'+value.name));
  card.append(node('pre','',Object.entries(value.defaults).map(([k,v])=>`${labels[k]||k}：${v||'待填写'}`).join('\n')||'无参数'));
  const detail=node('details'),list=node('ol');detail.append(node('summary','',label+'的操作步骤'));
  value.steps.forEach(s=>list.append(node('li','',s)));detail.append(list);card.append(detail);
 }
 card.append(node('p','small','确认后保存为待验证流程，不会自动运行。'));
 const actions=node('div','job-actions');card.append(actions);
 button(actions,'确认修改',async()=>{await api('apply_edit',{edit_id:result.edit_id});actions.remove();message('流程已修改，正在后台验证与修复。验证结果将在对话中显示。');await refresh();},'primary');
 button(actions,'取消修改',async()=>{await api('discard_edit',{edit_id:result.edit_id});card.remove();message('已取消修改，原流程保持不变。');});
 $('messages').append(card);$('messages').scrollTop=$('messages').scrollHeight;
}

$('validateFlow').onclick=()=>{$('validationFiles').checked=true;$('validationDialog').showModal();};
$('startValidation').onclick=async()=>{try{await api('validate',{id:selected.id,allow_files:$('validationFiles').checked});$('validationDialog').close();$('flowDialog').close();await refresh();}catch{}};
