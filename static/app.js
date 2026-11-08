'use strict';

const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dollars = value => value == null ? 'Not yet known' : new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', maximumFractionDigits:2}).format(value);
const today = () => new Date(Date.now() - new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
const icons = {
  pin:'<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  heart:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  building:'<path d="M5 21V5h14v16M2 21h20M9 9h1m4 0h1m-6 4h1m4 0h1m-5 8v-4h4v4"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.heart}</svg>`;
const fresh = () => ({city:'Boston',state:'MA',zip:'',lat:null,lon:null,insurance:'',wants_insurance:false,
  service:'primary_care',visit_date:today(),language:'English',description:'',history:'',medications:'',budget:'',
  priority:'balanced',months:1,adult:false,routine_confirmed:false,demo:false,plan:null,
  age:'',checks:[],none_reported:false,feel:'',need:''});
const S = {step:0, input:fresh(), state:{services:{},cases:[]}, preview:null, current:null, busy:false, choices:[], safety:null, sub:'symptoms', open:new Set(), view:'loading', health:null, draft:null};

const trail = new NavigationTrail(window.history, crypto.randomUUID());
let queuedRoute = null;
function routeKey() {
  if(S.expect && S.view==='wizard')return 'expect';
  return S.view==='wizard'?`wizard:${S.step}:${S.step===0?S.sub:''}:${S.step===4?S.current?.id:''}`:S.view;
}
function pageSnapshot(withForms=false) {
  const data={};
  for(const k of ['view','step','sub','input','draft','visit','plans','sbc','expect','found','safety','preparingProvider','journey','reportDraft','activeJourney','homeGoal','homeKind','profileFocus'])data[k]=S[k]??null;
  data.caseId=S.current?.id||null;
  data.open=[...S.open];
  data.formValues=withForms?[...document.querySelectorAll('#app form input[name], #app form select[name], #app form textarea[name]')]
    .filter(el=>!['password','file'].includes(el.type)).map(el=>({name:el.name,value:el.value,checked:el.checked,type:el.type})):[];
  return data;
}
function rememberPage() { if(S.view!=='loading'&&S.view!=='gate')trail.update(pageSnapshot(true)); }
function trackPage() {
  if(S.view==='loading')return;
  if(S.view==='gate'){trail.clear();S.journey=null;S.reportDraft=null;S.homeGoal='';S.activeJourney=null;}
  const previous=trail.current;
  trail.visit(routeKey(),pageSnapshot());
  if(previous!==trail.current)queueMicrotask(()=>{const heading=$('#app h1, #app h2');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}});
}
function backLabel() {
  if(S.view==='wizard'&&S.step===4)return '返回上一页 / Back';
  if(S.view==='wizard'&&S.step>0)return '返回上一步 / Previous step';
  return '返回 / Back';
}
function navigationBar() {
  if(S.view==='gate'||(S.view==='profile'&&!S.state.vault_exists))return '';
  const back=trail.canGoBack||S.view!=='home';
  return `<nav class="page-navigation" aria-label="Page navigation">${back?`<button type="button" class="back-link" data-action="page-back">← ${backLabel()}</button>`:'<span>我的健康 / My health</span>'}${S.view!=='home'?'<button type="button" class="text-button" data-action="home-page">我的健康首页 / My health home</button>':''}<span class="navigation-note">${S.view==='wizard'&&S.step<4?'返回可修改，已填内容会保留 / Your entries stay here':'已保存的任务可随时继续 / Saved tasks stay available'}</span></nav>`;
}
async function restorePage(id) {
  if(S.busy){queuedRoute=id;return;}
  await work(async()=>{
    S.state=await api('/api/state');
    if(!S.state.unlocked){S.view='gate';S.current=null;S.health=null;closeDialog();render();return;}
    const data=trail.restore(id);
    if(!data){S.view='home';S.expect=null;S.current=null;S.health=await api('/api/profile');render();return;}
    let current=null;
    if(data.caseId){
      try{current=await api('/api/case?id='+encodeURIComponent(data.caseId));}
      catch{S.view='home';S.expect=null;S.current=null;S.health=await api('/api/profile');render();toast('这条任务已不可用。 / This journey is no longer available.');return;}
    }
    for(const k of ['view','step','sub','input','draft','visit','plans','sbc','expect','found','safety','preparingProvider','journey','reportDraft','activeJourney','homeGoal','homeKind','profileFocus'])S[k]=data[k];
    S.current=current;S.preview=null;S.open=new Set(data.open);S.health=await api('/api/profile');
    if(S.found?.id)S.found=await api('/api/case?id='+encodeURIComponent(S.found.id));
    if(S.journey?.id)S.journey=await api('/api/journey?id='+encodeURIComponent(S.journey.id));
    closeDialog();render();
    for(const v of data.formValues){
      const el=document.querySelector(`#app form [name="${CSS.escape(v.name)}"]`);
      if(el){if(['checkbox','radio'].includes(v.type))el.checked=v.checked;else el.value=v.value;}
    }
    rememberPage();window.scrollTo(0,0);
  });
}
window.addEventListener('pagehide',()=>dictation.abort());
document.addEventListener('visibilitychange',()=>{if(document.hidden)dictation.abort();});
window.addEventListener('popstate',event=>{if(event.state?.firstvisitRoute)restorePage(event.state.firstvisitRoute);});
document.addEventListener('input',event=>{if(event.target.closest('#app form'))rememberPage();});

async function api(path, body) {
  const response = await fetch(path, {method:body === undefined ? 'GET':'POST', headers:{'X-FirstVisit':'local','Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 423 && S.state.unlocked) {
      S.state.unlocked = false; S.current = null; S.input = fresh(); S.safety = null; S.expect = null; S.found = null; S.sub = 'symptoms'; S.view = 'gate'; S.health = null; S.journey=null;S.reportDraft=null;S.homeGoal='';S.activeJourney=null;dictation.abort(); S.step = 0; S.preview = null; closeDialog(); render();
    }
    throw new Error(data.error || 'Something went wrong. Please try again.');
  }
  return data;
}
function toast(message) { const node = $('#toast'); node.textContent = message; node.classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => node.classList.remove('show'), 6500); }
async function work(task, message='Working locally…') {
  if (S.busy) return;
  S.busy = true;
  document.body.classList.add('busy');
  const status = $('#working'); if (status) status.textContent = message;
  try { await task(); } catch (error) { toast(error.message); }
  finally { S.busy = false; document.body.classList.remove('busy'); if ($('#working')) $('#working').textContent = ''; if(queuedRoute){const id=queuedRoute;queuedRoute=null;restorePage(id);} }
}
function field(label, name, value='', type='text', extra='') {
  return `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
}
function select(label,name,options,value) {
  return `<label class="field"><span>${label}</span><select name="${name}">${options.map(([v,l])=>`<option value="${esc(v)}" ${value===v?'selected':''}>${esc(l)}</option>`).join('')}</select></label>`;
}
function planFields(plan, prefix='plan_') {
  const p = plan || {}, rule = p.rule || 'copay';
  return `<div class="sub-card"><p class="sub-title">The plan</p><div class="form-grid">
    ${field('Exact plan / network name',prefix+'name',p.name,'text','placeholder="Copy the full name from the plan" maxlength="120"')}
    ${field('Monthly premium ($)',prefix+'premium',p.premium,'number','min="0" max="1000000" step="0.01" placeholder="Optional"')}
    ${field('Coverage starts',prefix+'start',p.start,'date')}${field('Coverage ends (if known)',prefix+'end',p.end,'date')}
  </div>${select('Zocdoc product — choose only after checking your exact plan',prefix+'zocdoc_product',[['','No confirmed product · select on Zocdoc'],['bcbsma_blue_care_elect_ppo','I checked: BCBS Massachusetts · Blue Care Elect (PPO)']],p.zocdoc_product||'')}<p class="hint">A typed name never selects an insurance product. This optional filter is not proof that a clinician is in-network.</p><label class="checkline"><input name="${prefix}eligible" type="checkbox" ${p.eligible?'checked':''}><span>I confirmed my eligibility with the plan or marketplace.</span></label></div>
  <div class="sub-card"><p class="sub-title">What this visit costs you</p>
    ${select(S.input.service==='same_day'?'How the plan pays for an urgent care visit':'How the plan pays for this visit',prefix+'rule', [['copay','A fixed copay (deductible does not apply)'],['deductible','Deductible first, then coinsurance']],rule)}
    <div class="form-grid"><div data-rule-fields="copay" ${rule==='copay'?'':'hidden'}>${field('Visit copay ($)',prefix+'copay',p.copay,'number','min="0" step="0.01"')}</div>
    <div data-rule-fields="deductible" class="rule-pair" ${rule==='deductible'?'':'hidden'}>${field('Remaining deductible ($)',prefix+'deductible_remaining',p.deductible_remaining,'number','min="0" step="0.01"')}${field('Coinsurance you pay (%)',prefix+'coinsurance',p.coinsurance,'number','min="0" max="100" step="0.1"')}</div>
    ${field('Remaining out-of-pocket limit ($)',prefix+'oop_remaining',p.oop_remaining,'number','min="0" step="0.01"')}</div>
    <p class="hint">Leave unknown values blank. A card alone doesn’t confirm your remaining deductible or each provider’s network.</p>
  </div>`;
}
function planResources() {
  return `<details class="private-details"><summary>Find your actual plan details</summary><div class="resource-list"><a href="https://studenthealthplan.northeastern.edu/" target="_blank" rel="noopener noreferrer">Northeastern student plan & benefit documents ↗</a><a href="https://betterhealthconnector.com/compare-plans" target="_blank" rel="noopener noreferrer">Massachusetts Health Connector plan comparison ↗</a><a href="https://providerdirectory.mahealthconnector.org/" target="_blank" rel="noopener noreferrer">Health Connector provider / plan directory ↗</a></div><p class="hint">Check the exact plan year and your enrollment before copying benefits. These are official information sources, not a personalized premium quote or an eligibility determination. Opening a source does not send your local health profile.</p></details>`;
}
function readPlan(form) {
  const f = new FormData(form), p = {};
  ['name','premium','start','end','rule','copay','deductible_remaining','coinsurance','oop_remaining','zocdoc_product'].forEach(k => p[k] = f.get('plan_'+k) ?? '');
  p.eligible = f.has('plan_eligible'); return p;
}
function collect() {
  const form = $('#wizard'); if (!form) return;
  const f = new FormData(form);
  if(S.step===2 && (f.get('city')!==S.input.city || f.get('state')!==S.input.state)) {S.input.lat=null;S.input.lon=null;}
  for (const [k,v] of f) if (!k.startsWith('plan_') && !['passphrase','live','adult','routine_confirmed','checks','none_reported'].includes(k)) S.input[k] = v;
  if (S.step === 1 && $('[name="plan_name"]',form)) S.input.plan = readPlan(form);
}
function renderHeader() {
  $('#header').innerHTML = `<div class="header-inner"><button class="brand" data-action="home" aria-label="FirstVisit home"><span class="brand-icon">${icon('heart')}</span>firstvisit<span class="brand-dot">.</span></button><nav aria-label="Main navigation">
    <div class="locale-switch" role="group" aria-label="Interface language" data-i18n-keep><button type="button" data-ui-locale="en" lang="en" aria-pressed="${I18n.locale==='en'}">EN</button><button type="button" data-ui-locale="zh" lang="zh-CN" aria-pressed="${I18n.locale==='zh'}">中文</button></div>
    <span class="privacy-pill">${icon('lock')} ${S.state.preview_mode?'Temporary preview · fictional data only':'Local vault · optional browser voice'}</span>
    ${S.state.unlocked?'<button class="nav-button" data-action="home-page">My health</button><button class="nav-button" data-action="known">What we know</button>':''}
    <button class="nav-button" data-action="saved">My care journeys</button>
    <button class="nav-button" data-action="privacy">Privacy</button>
    ${S.state.unlocked ? '<button class="nav-button" data-action="lock">Lock vault</button>' : S.state.vault_exists ? '<button class="nav-button" data-action="unlock">Unlock vault</button>' : ''}
    </nav></div>`;
  let bar=$('#page-navigation');if(!bar){bar=document.createElement('div');bar.id='page-navigation';$('#header').after(bar);}bar.innerHTML=navigationBar();
}
const SUB_STEPS=['你的情况 / You & your health','你的偏好 / What matters to you','时间和地点 / When & where','确认并搜索 / Review & find care'];
function subSteps(){const zh=I18n.locale==='zh',name=(SUB_STEPS[S.step]||'').split(' / ')[zh?0:1]||'';return `<p class="sub-steps" data-i18n-keep>${zh?'选择诊所':'Choose a clinic'} · ${S.step+1}/4 · ${esc(name)}</p>`;}
function sidebar() {
  const names=['You & your health','What matters to you','When & where','Review & find care'];
  return `<aside class="journey-sidebar"><p class="eyebrow">A CLEARER PATH TO CARE</p><h1>Care that puts<br><em>you first.</em></h1><p class="sidebar-copy">We start with you and your health. Where to go comes after.</p><ol class="steps">${names.map((n,i)=>`<li class="${S.step===i?'active':S.step>i?'done':''}">${i<S.step?`<button type="button" class="step-jump" data-step="${i}" aria-label="Edit ${n}">`:''}<span>${S.step>i?icon('check'):String(i+1).padStart(2,'0')}</span><div>${n}<small>${['How you are doing, first','Language and coverage','Location is one detail','You control what is shared'][i]}</small></div>${i<S.step?'</button>':''}</li>`).join('')}</ol><div class="sidebar-note">${icon('shield')}<p>Typed and imported health data stay local. Searches disclose location and care type after review. Optional browser-service dictation has a separate privacy boundary.</p></div><button class="text-button" data-action="neu-example">Student insurance scenario · NEU / 02445</button><button class="text-button" data-action="demo">Explore a fictional example ${icon('arrow')}</button></aside>`;
}
const serviceName=v=>({follow_up:'Primary-care follow-up',same_day:'Same-day care (urgent care or campus clinic)'})[v]||'Primary-care appointment';
const lvl=c=>['crisis','poison'].includes(c.level)?'emergency':c.level;
const SYMPTOM_GROUPS=[['Chest and breathing',['chest_pain','breathing','cough']],['Head',['stroke','worst_headache','head_injury','fainted']],['Fever, throat and ears',['high_fever','fever','sore_throat']],['Belly',['belly_severe','blood_gut','belly_ache','fluids']],['Peeing',['urination']],['Arms, legs and back',['limb_broken','leg_swollen','injury','joint_pain']],['Skin, bleeding and allergies',['bleeding','allergy_severe','rash']],['Eyes',['eye']],['Mind and mood',['self_harm','mental']],['Swallowed something',['poison']],['Other',['severe_pain']]];
const SIGN_GROUPS=[['Chest and breathing',['chest_pain','breathing']],['Head',['stroke','worst_headache','head_injury','fainted']],['Belly',['belly_severe','blood_gut']],['Arms and legs',['limb_broken','leg_swollen']],['Bleeding',['bleeding']],['Allergic reaction',['allergy_severe']],['Thoughts of hurting yourself',['self_harm']],['Swallowed something',['poison']]];
const EVERYDAY_GROUPS=[['Fever, cough and throat',['high_fever','fever','cough','sore_throat']],['Belly',['belly_ache','fluids']],['Peeing',['urination']],['Arms, legs and back',['injury','joint_pain']],['Eyes',['eye']],['Skin',['rash']],['Bad pain',['severe_pain']],['Mood and stress',['mental']]];
function grouped(items,groups){const used=new Set();const out=groups.map(([t,ids])=>{const g=ids.map(id=>items.find(c=>c.id===id)).filter(Boolean);g.forEach(c=>used.add(c.id));return [t,g];}).filter(([,g])=>g.length);const rest=items.filter(c=>!used.has(c.id));if(rest.length)out.push(['Other',rest]);return out;}
function groupCards(items,groups,kind){
  return `<div class="group-cards">${grouped(items,groups).map(([t,g])=>{
    const n=g.filter(c=>S.input.checks.includes(c.id)).length, open=S.open.has(t);
    const item=c=>kind==='sign'?`<button type="button" class="sign ${S.input.checks.includes(c.id)?'selected':''}" data-sign="${esc(c.id)}"><span class="choice-radio"></span>${esc(c.label)}</button>`:`<button type="button" class="chip ${S.input.checks.includes(c.id)?'selected':''}" data-chip="${esc(c.id)}">${esc(c.label)}</button>`;
    return `<div class="group-card ${open?'open':''} ${n?'has':''}"><button type="button" class="group-head" data-group="${esc(t)}" aria-expanded="${open}"><span>${t}</span><small>${n?`${n} selected`:`${g.length} ${g.length===1?'item':'items'}`}</small><span class="chev" aria-hidden="true">${open?'−':'+'}</span></button>${open?`<div class="group-body ${kind==='sign'?'':'chips'}">${g.map(item).join('')}</div>`:''}</div>`;
  }).join('')}</div>`;
}
const NEEDS=[['checkup','Checkup, vaccine or a form','checkup','primary_care'],['refill','Prescription refill','refill','primary_care'],['follow_up','Follow-up visit','','follow_up'],['unsure','I’m not sure','','unsure']];
const FEELS=[['unwell','I feel unwell','Something is bothering me','mood-sick'],['okay','I’m okay','I’m arranging planned care','mood-smile'],['unsure','I’m not sure what I need','Help me figure it out','help']];
function safetyPanel(r){
  if(!r)return '';
  const urgent=['emergency','same_day'].includes(r.level);
  const venues={'911':'Call 911',er:'Emergency room',urgent_care:'Urgent care clinic',campus_health:'Campus health clinic',telehealth:'Telehealth (video visit)',primary_care:'Primary care appointment'};
  return `<div class="safety-panel ${r.level}" role="${urgent?'alert':'status'}"><p class="eyebrow">YOUR SAFETY CHECK · ON THIS DEVICE</p><h3>${esc(r.headline)}</h3>${(r.hotlines||[]).map(h=>`<div class="hotline"><strong>${esc(h.name)}</strong><span>${esc(h.how)}</span></div>`).join('')}<p>${esc(r.why)}</p><p class="safety-options"><span>Good places to start:</span> ${r.options.map(o=>esc(venues[o]||o)).join(' · ')}</p>${r.rules.length?`<ul>${r.rules.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}${r.level==='emergency'?`<div class="call-actions">${callButtons(r)}</div><p class="safety-stop">Please get help now. This app won’t compare prices for an emergency. If something here is wrong, change your answers above.</p>`:''}${r.level==='same_day'?`<div class="safety-next"><span>下一步请点击下方“Find care today”，继续填写语言、保险和位置。 / Choose “Find care today” below to continue with your language, coverage and location.</span></div>`:''}<small>${esc(r.disclaimer||'')}</small></div>`;
}
function callButtons(r){
  const names=(r.hotlines||[]).map(h=>h.name).join(' '), crisis=names.includes('988'), poison=names.includes('Poison'), only=(crisis||poison)&&r.rules.every(x=>/hurting|killing|poison|medicine/i.test(x));
  const b=[];
  if(crisis) b.push(['tel:988','Call 988'],['sms:988','Text 988']);
  if(poison) b.push(['tel:18002221222','Call Poison Control']);
  b.splice(only?b.length:0,0,['tel:911','Call 911']);
  return b.map(([h,t],i)=>`<a class="${i===0?'primary':'secondary'} call" href="${h}">${t}</a>`).join('');
}
function safetySummary(){
  const r=S.safety;if(!r)return '';
  return `<div class="safety-summary">${icon('check')}<div><strong>Your safety check</strong><span>${esc(r.headline)}</span></div><button type="button" class="text-button" data-action="health">Change</button></div>`;
}
function healthHead(title,lede){return `<div class="section-icon">${icon('heart')}</div><p class="eyebrow">01 / YOU & YOUR HEALTH</p><h2>${title}</h2><p class="lede">${lede}</p>`;}
function healthStep(p){
  const actions=next=>`<div class="form-actions"><button type="button" class="text-button" data-action="page-back">← 返回 / Back</button>${next}</div>`;
  const cont=S.safety?.level==='emergency'
    ?'<button type="submit" class="secondary">重新检查修改后的回答 / Recheck edited answers</button>'
    :`<button type="submit" class="primary">${S.safety?.level==='same_day'?'查找当天就医 / Find care today':'Continue'} ${icon('arrow')}</button>`;
  const safetyResult=`<div id="safety-result">${S.safety&&['emergency','same_day'].includes(S.safety.level)?safetyPanel(S.safety):''}</div>`;
  if(S.sub==='need') return healthHead('What do you need?','No symptom questions needed.')+
    `<div class="chips">${NEEDS.map(([id,t])=>`<button type="button" class="chip ${p.need===id?'selected':''}" data-need="${id}">${t}</button>`).join('')}</div>
    <label class="field"><span>Anything else? <small>Optional · stays local</small></span><textarea name="description" rows="2" maxlength="3000" placeholder="My doctor asked me to come back in two weeks.">${esc(p.description)}</textarea></label>`+safetyResult+actions(cont);
  const items=S.choices.filter(c=>c.level!=='routine');
  return healthHead('What’s bothering you?','Open a part of the body and pick what fits. If something sounds serious, we’ll tell you right away.')+
    '<button type="button" class="text-button planned-care-link" data-action="planned-care">我是来安排体检、续药或计划内就诊的 / Here for a checkup, refill or planned visit?</button>'+
    groupCards(items,SYMPTOM_GROUPS,'chip')+
    `<label class="field"><span>Anything else? <small>Optional · stays local</small></span><textarea name="description" rows="2" maxlength="3000" placeholder="It started two days ago and gets worse at night.">${esc(p.description)}</textarea></label>
    ${safetyResult}`+actions(cont);
}
function card(title,hint,body,cls=''){return `<section class="form-card ${cls}"><div class="form-card-head"><h3>${title}</h3>${hint?`<p>${hint}</p>`:''}</div>${body}</section>`;}
function stepContent() {
  const p=S.input;
  if (S.step===0) return healthStep(p);
  if (S.step===1) {
    const insured=p.insurance==='yes', exploring=p.insurance==='no'&&p.wants_insurance;
    return `<div class="section-icon">${icon('shield')}</div><p class="eyebrow">02 / WHAT MATTERS TO YOU</p><h2>How should care work for you?</h2><p class="lede">Your language and coverage shape every option we show.</p>${safetySummary()}`+
    card('About you','Stays on this device.',`<div class="form-grid">${S.input.scenario!=='neu_student'&&S.health?.age!=null?`<div class="field"><span>Your age</span><div class="from-profile">${S.health.age} <small>from your health profile</small></div><input type="hidden" name="age" value="${S.health.age}"></div>`:field('Your age','age',p.age,'number','required min="0" max="120" step="1" inputmode="numeric"')}${select('Preferred language','language',[['English','English'],['Chinese','Chinese / 中文'],['Spanish','Spanish / Español']],p.language)}</div>`)+
    (S.activeJourney&&p.insurance&&!S.editInsurance?card('Insurance','',`<p><strong>${esc(COVERAGE_TEXT[coverageFromInput(p)])}</strong> · 来自第 2 步 / from step 2 <button type="button" class="text-button" data-action="wizard-edit-insurance">修改 / Change</button></p>`):card('Insurance','Do you have health insurance?',`<div class="choice-grid"><button type="button" class="choice ${insured?'selected':''}" data-insurance="yes"><span class="choice-radio"></span><strong>Yes, I have insurance</strong><span>Use my benefits and compare my personal cost.</span></button><button type="button" class="choice ${p.insurance==='no'?'selected':''}" data-insurance="no"><span class="choice-radio"></span><strong>No insurance right now</strong><span>Explore self-pay care and optional coverage.</span></button></div>
      ${p.insurance==='no'?`<div class="sub-card"><p class="sub-title">Would you like to explore insurance?</p><div class="segmented"><button type="button" class="${!p.wants_insurance?'selected':''}" data-wants="no">Continue without it</button><button type="button" class="${p.wants_insurance?'selected':''}" data-wants="yes">Compare getting a plan</button></div><p class="hint">Check your school account first. You may already be enrolled in student coverage.</p></div>`:''}`))+
    (insured||exploring?card(insured?'Your current plan':'A plan you’re considering',insured?'Enter what you know. You can still find care before every benefit is confirmed.':'Use an actual plan quote, or leave this blank and explore options after your search.',planFields(p.plan)+planResources()):'');
  }
  if (S.step===2) return `<div class="section-icon">${icon('pin')}</div><p class="eyebrow">03 / WHEN & WHERE</p><h2>When and where works for you?</h2><p class="lede">Searches use location and care type. Your health details stay on this device.</p>`+
    card('When','',field('Planned visit date','visit_date',p.visit_date,'date',`required min="${today()}"`))+
    card('What matters most','How we order your options.',`<div class="form-grid">${select('Put this first','priority',[['balanced','My fit: language, budget, then cost'],['cost','Lowest supported personal cost'],['rating','Highest sourced patient rating'],['distance','Closest known location']],p.priority)}${field('Visit budget ($, optional)','budget',p.budget,'number','min="0" step="0.01" placeholder="Your comfort zone"')}</div>`)+
    card('Where','Searches use location and care type. Review the exact queries before sending.',`<div class="location-choice">${icon('pin')}<div><strong>Boston, Massachusetts</strong><span>Our first supported local directory</span></div><button type="button" class="text-button" data-action="boston">Use Boston</button></div><div class="form-grid three">${field('City','city',p.city,'text','required maxlength="70" autocomplete="address-level2"')}${field('State','state',p.state,'text','required pattern="[A-Za-z]{2}" maxlength="2" autocomplete="address-level1"')}${field('ZIP (optional)','zip',p.zip,'text','pattern="[0-9]{5}" maxlength="5" autocomplete="postal-code"')}</div><button type="button" class="secondary" data-action="geolocate">${icon('pin')} Add my device location</button><p class="hint">${p.lat!=null?'Coordinates added for distance. They stay on this device.':'Optional. Exact coordinates stay on this device.'}</p>`);
  const queries = S.preview?.queries || [];
  return `<div class="section-icon">${icon('lock')}</div><p class="eyebrow">04 / REVIEW & FIND CARE</p><h2>Your information. Your control.</h2><p class="lede">Here’s what we’ll use to find your next step.</p>`+
    card('Your summary','',`<div class="review-list"><div><span>Your safety check</span><strong>${esc(S.safety?.headline||'Not checked')}</strong></div><div><span>Care</span><strong>${serviceName(p.service)}</strong></div><div><span>Payment</span><strong>${p.insurance==='yes'?'Insurance + self-pay comparison':p.wants_insurance?'Self-pay + optional insurance scenario':'Self-pay; optional comparison later'}</strong></div><div><span>Search area</span><strong>${esc(p.city)}, ${esc(p.state)} ${esc(p.zip)}</strong></div></div>`)+
    card('Help us prepare your visit','Optional. Used only on this device for your call script and doctor card.',`<label class="field"><span>Conditions, allergies, or clinician instructions</span><textarea name="history" maxlength="3000" rows="3">${esc(p.history)}</textarea></label>${field('Current medications','medications',p.medications,'text','maxlength="1000"')}`)+
    card('What stays and what’s shared','',`<div class="share-split"><div><strong>${icon('lock')} Stays on this device</strong><p>Not included in public search: health details, history, medications, exact coordinates, benefits and rankings. Optional browser dictation has a separate disclosure.</p></div><div><strong>${icon('pin')} Can be shared</strong><p>${S.preview?(queries.length?'The search below, only after you approve it.':'Nothing. No public search is configured.'):'City, state, ZIP and care type for a public search. You’ll review the exact query first.'}</p></div></div>
      ${S.preview&&queries.length?`<div class="sub-card"><p class="sub-title">Public search preview</p>${queries.map(q=>`<div class="query"><span>${esc(q.provider)}</span><code>${esc(q.query)}</code></div>`).join('')}<p class="hint">Recipients: ${S.preview.destinations.map(esc).join(', ')}. Search providers can infer a general interest in this care category.</p><label class="checkline"><input type="checkbox" name="live" checked><span>Send these queries to find more providers. Uncheck to use the local directory only.</span></label></div>`:S.preview?`<p class="hint">${p.demo?'No external search. All sample providers, prices, reviews and plan relationships are fictional.':'The Boston / Brookline directory has official source links; prices and coverage need confirmation.'}</p>`:''}`)+
    (!S.state.unlocked?card(S.state.vault_exists?'Unlock your private vault':'Create your private vault','Encrypts your saved care journeys on this computer. There is no password recovery.',field('Vault passphrase','passphrase','','password',`required minlength="8" maxlength="1000" autocomplete="${S.state.vault_exists?'current-password':'new-password'}"`)):'');
}
const pfield=(label,name,value,type='text',extra='')=>field(label,name,value,type,extra);
function fromProfile(){
  const h=S.health?.profile||{}, i=fresh();
  Object.assign(i,{visit_date:S.state.today||today(),language:h.language||'English',insurance:h.insurance||'',wants_insurance:!!h.wants_insurance,plan:h.plan||null,
    priority:h.insurance==='no'?'cost':'balanced',age:S.health?.age??'',history:[...(h.conditions||[]),...((h.allergies||[]).length?['Allergies: '+h.allergies.join(', ')]:[])].join('; '),medications:(h.medications||[]).join(', ')});
  return i;
}
function startVisit(feel){
  S.activeJourney=null;S.journey=null;
  S.input=fromProfile(); Object.assign(S.input,{feel,none_reported:feel==='okay'});
  S.sub=feel==='okay'?'need':'symptoms'; S.step=0; S.safety=null; S.open=new Set(); S.preview=null; S.current=null; S.expect=null; S.view='wizard'; render(); window.scrollTo(0,0);
}
function todoRow(t){
  return `<div class="todo ${t.done_on?'done':''} ${t.urgent?'urgent':''}"><button type="button" class="todo-check" data-todo="${esc(t.id)}" aria-pressed="${!!t.done_on}" aria-label="Mark ${esc(t.title)} done">${t.done_on?icon('check'):''}</button><div><strong>${esc(t.title)}</strong><p>${esc(t.done_on?`Done on ${t.done_on}`:t.why)}${t.source?` · <a href="${esc(t.source.url)}" target="_blank" rel="noopener noreferrer">${esc(t.source.title)}</a>`:''}</p></div></div>`;
}

const JOURNEY_KINDS={general:'一起理清下一步 / Help me get started',first_visit:'主动照顾健康 / Stay healthy',concern:'获得就医帮助 / Get care',follow_up:'跟进已有照护 / Manage my care',insurance:'理清保险与费用 / Insurance & costs',report:'我想讨论检查结果 / Discuss test results'};
const HOME_STARTS={
  general:{hint:'Start with what brought you here and what you would like help doing. A few words are enough. / 先说说你为什么来，以及希望我们帮你做什么。几句话就够。',placeholder:'I would like help with… What I am unsure about is… / 我想请你帮我……现在不太清楚的是……'},
  first_visit:{description:'New to US healthcare, find a regular doctor, plan a checkup or preventive care. / 第一次了解美国医疗、建立固定医生联系、准备常规检查和预防性服务。',hint:'Have you seen a doctor here before? Are you looking for a regular doctor, a checkup, or vaccines and screenings? / 你以前在这里看过医生吗？想找固定医生、做常规检查，还是了解疫苗和筛查？',placeholder:'I am new to healthcare in the US. I would like a regular doctor and a checkup, but I am not sure where to start. / 我刚接触美国医疗，想找一位固定医生做个常规检查，但不知道从哪里开始。'},
  concern:{description:'A new health concern, finding where to go, contacting a clinic, how booking works. / 新的健康困扰、寻找就医选项、准备联系诊所、了解预约流程。',hint:'What is bothering you, when did it start, and what help are you looking for? / 什么让你不舒服、什么时候开始，以及你想获得什么帮助？',placeholder:'I have been bothered by __ since __. I would like help figuring out where to go. / 我从……开始有……困扰，想知道该去哪里看。'},
  follow_up:{description:'A follow-up or test your doctor suggested, refills, your reports and visits, unfinished tasks. / 医生建议的复诊或检查、续药准备、整理报告和就诊记录、继续未完成任务。',hint:'What did the clinician recommend or what do you need to keep going, when is it due, and which part do you need help with? You can add the file later. / 医生建议了什么、你需要继续跟进什么、什么时候完成，你卡在哪一步？报告可以稍后添加。',placeholder:'My doctor asked me to __ by __. I need help arranging it. / 医生让我在……之前……，我需要帮助安排这件事。'},
  insurance:{description:'Using your insurance, care without insurance, comparing ways to pay, asking for prices. / 有保险怎么用、没有保险怎么办、比较支付路径、准备询价。',hint:'Do you have insurance now? What do you most want to know: what a visit costs, what your plan covers, or how to pay? / 你现在有保险吗？最想知道什么：看一次病多少钱、保险报什么，还是怎么付费？',placeholder:'I have student insurance, but I am not sure what a doctor visit would cost me. / 我有学生保险，但不清楚看一次医生自己要付多少钱。'}
};
// Step 1 on every journey: coverage decides which costs and questions apply, so it comes before Prepare / Find.
function coverageStep(j){
  const p=S.health?.profile||{}, situation=j.coverage_situation||'unknown', plan=j.input?j.input.plan?.name:p.plan?.name, sbc=!!p.plan_benefits&&j.input?.scenario!=='neu_student';
  const status={
    insured:[`你有保险${plan?'：'+plan:''} / You have insurance${plan?': '+plan:''}`, sbc?'已从你的 SBC 读取福利，费用按已确认的福利计算。 / Benefits come from your reviewed SBC; costs use only confirmed benefits.':'还没有你的计划福利（SBC），看病费用暂时是未知，不按 0 计算。 / Your plan benefits (SBC) are not added yet, so visit costs stay unknown, not $0.'],
    uninsured:['目前没有保险 / No insurance right now','接下来按自费价格比较，并准备询问减免。 / Next we compare self-pay prices and ask about financial assistance.'],
    choosing:['正在选择保险计划 / Choosing a plan','比较一年总花费：保费加上实际看病的自付部分。 / Compare the yearly total: premium plus what you pay when you use care.'],
    unknown:['还不知道你有没有保险 / We do not know your coverage yet','先回答这一步，后面的费用和问题才能对得上。 / Answer this first so costs and questions below match your situation.']}[situation]||[];
  return `<section class="form-card coverage-step ${situation==='unknown'?'needs-answer':''}"><p class="eyebrow">保险与费用 / COVERAGE & COSTS</p><h2>${esc(status[0])}</h2><p>${esc(status[1])}</p><button class="${situation==='unknown'?'primary':'secondary'}" data-action="edit-coverage">${situation==='unknown'?'回答：我有保险吗？ / Do I have insurance?':'核对或修改 / Check or change'}</button> <button class="text-button" data-action="explain-coverage">解释给我听 / Explain this</button><div id="coverage-explain" class="soft-note" aria-live="polite" hidden></div></section>`;
}
// Directions: only for a specific street address; vague or fictional locations get no link.
const mapsUrl=p=>(!p||p.demo||!p.address||/confirm/i.test(p.address)||!/\d/.test(p.address))?'':'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(p.address);
// Booking: only an official scheduling page recorded from the source; opening it is not a booking.
const bookingLink=p=>p&&p.booking_url&&/^https:\/\//.test(p.booking_url)?`<a class="booking-link" href="${esc(p.booking_url)}" target="_blank" rel="noopener noreferrer" title="Official scheduling page. Opening it does not book an appointment.">预约 / Book online ↗</a>`:'';
const directionsLink=p=>{const u=mapsUrl(p);return u?`<a class="directions-link" href="${esc(u)}" target="_blank" rel="noopener noreferrer" title="Opens Google Maps with this address only">${icon('pin')} 导航 / Directions ↗</a>`:'<span class="hint">地点需向诊所确认 / Confirm the location with the office</span>';};
const doctorResults=(rows,q)=>!q.trim()?'<p class="hint">输入医生姓名、诊所名称或街道。只在本机的有来源名录里查找，不发送到网络。 / Type a clinician, clinic or street. Matches only our sourced local directory; nothing is sent.</p>':rows.length?rows.map(r=>`<article class="directory-row"><p class="provider-label">${r.type==='clinician'?'医生 / Clinician':'诊所 / Practice'} · <span data-i18n-keep>${esc(r.practice)}</span></p><h3 data-i18n-keep>${esc(r.name)}</h3><p data-i18n-keep>${esc(r.address)}${r.phone?' · '+esc(r.phone):''}</p><p class="hint" data-i18n-keep>${esc(r.source_note)} (${esc(r.checked_on)})</p><div class="card-actions">${directionsLink(r)}${bookingLink(r)}<a class="text-button" href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">查看来源 / View source ↗</a></div></article>`).join(''):`<p>本地名录里没有找到。 / Not in our local directory.</p><p class="hint">可以在保险公司官方查找页面搜索，找到后在比较结果里点「Add a provider you found」带回来。 / Look it up in your insurer’s official directory, then bring it back with “Add a provider you found” in your results.</p><a class="text-button" href="https://member.bluecrossma.com/fad" target="_blank" rel="noopener noreferrer">BCBSMA Find a Doctor ↗</a>`;
const doctorSearchForm=()=>`<form id="doctor-search" class="doctor-search" role="search"><label class="field"><span>医生或诊所 / Doctor or clinic</span><input id="doctor-query" name="q" type="search" maxlength="120" autocomplete="off" placeholder="e.g. Hwang, Brigham, Beacon Street" value="${esc(S.doctorQuery||'')}"></label></form><div id="doctor-results" aria-live="polite">${doctorResults([],S.doctorQuery||'')}</div>`;
function bindDoctorSearch(){
  const box=$('#doctor-query');if(!box)return;let timer=null,seq=0;
  const run=async()=>{const q=box.value;S.doctorQuery=q;const mine=++seq;let rows=[];if(q.trim()){try{rows=(await api('/api/directory?q='+encodeURIComponent(q))).results;}catch(e){rows=[];}}if(mine!==seq||!$('#doctor-results'))return;$('#doctor-results').innerHTML=doctorResults(rows,q);I18n.apply($('#doctor-results'));};
  box.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(run,150);});
  $('#doctor-search').addEventListener('submit',e=>{e.preventDefault();run();});
  if(box.value.trim())run();
}
function openDoctorSearch(){openDialog('按医生或诊所找 / Find by doctor or clinic',doctorSearchForm(),true);bindDoctorSearch();$('#doctor-query')?.focus();}
let homeCompletion=null;
function homePrompt(kind){return HOME_STARTS[kind]||HOME_STARTS.general;}
function updateHomePrompt(kind){
  const prompt=homePrompt(kind),box=$('#home-goal'),hint=$('#home-prompt');
  if(box){box.setAttribute('placeholder',prompt.placeholder);I18n.apply(box);}
  if(hint){hint.textContent=prompt.hint;I18n.apply(hint);}
  homeCompletion?.schedule();
  document.querySelectorAll('[data-journey-kind]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.journeyKind===kind)));
}

const dictation=new Dictation({scope:window,onText:text=>{const box=$('#home-goal');if(!box||S.view!=='home')return;box.value=[box.value,text].filter(Boolean).join(' ');S.homeGoal=box.value;box.dispatchEvent(new Event('input',{bubbles:true}));},onState:listening=>{const b=$('#dictation-button');if(b){b.textContent=listening?'停止听写 / Stop':'语音输入 / Dictate';b.setAttribute('aria-pressed',String(listening));}if($('#dictation-status'))$('#dictation-status').textContent=listening?'正在听写，结束后请核对文字。 / Listening. Review the text before submitting.':'';},onError:error=>{if($('#dictation-status'))$('#dictation-status').textContent='语音未完成，已有文字保留，可以打字继续。 / Dictation stopped: '+error+'. Your text is kept; you can keep typing.';}});
function homeComposer(){
  const kind=S.homeKind||'general',prompt=homePrompt(kind);
  return `<section class="home-composer"><p class="eyebrow">START WHERE YOU ARE</p><h1 class="home-title">What would you like help with today?</h1><p class="lede">Speak or type to get started. Add a report if you have one. No complete profile needed.</p><div class="search-mode" role="group" aria-label="How do you want to start?"><button type="button" data-action="mode-need" aria-pressed="${S.homeMode!=='doctor'}">按需求找 / By what you need</button><button type="button" data-action="mode-doctor" aria-pressed="${S.homeMode==='doctor'}">按医生或诊所找 / By doctor or clinic</button></div>${S.homeMode==='doctor'?doctorSearchForm():''}<form id="home-intent" ${S.homeMode==='doctor'?'hidden':''}><p class="starting-points-label">选一个接近的情况，也可以直接往下写 / Pick one if it helps, or just tell us below</p><div class="journey-starts" role="group" aria-label="What brings you here?">${Object.entries(HOME_STARTS).filter(([id])=>id!=='general').map(([id,item])=>`<button type="button" class="journey-start" data-journey-kind="${id}" aria-pressed="${kind===id}"><strong>${esc(JOURNEY_KINDS[id])}</strong><span>${esc(item.description)}</span></button>`).join('')}</div><input type="hidden" name="kind" value="${esc(kind)}"><label class="field"><span>说说你的情况和想获得的帮助 / Tell us what is on your mind</span><p id="home-prompt" class="input-prompt">${esc(prompt.hint)}</p><div class="goal-editor"><div id="goal-ghost" class="goal-ghost" aria-hidden="true" hidden><span id="goal-prefix"></span><span id="goal-suggestion"></span></div><textarea id="home-goal" name="goal" rows="4" required maxlength="2000" aria-describedby="home-prompt home-completion-help" placeholder="${esc(prompt.placeholder)}">${esc(S.homeGoal||'')}</textarea><button type="button" id="accept-completion" class="ghost-accept" hidden aria-label="Accept suggested wording">Tab <span>接受 / Accept</span></button></div><p id="kind-guess" class="kind-guess" aria-live="polite" hidden></p><span id="home-completion-help" class="completion-help">浅色文字是可选补全，Tab 接受，Esc 忽略。 / Gray text is optional. Tab to accept, Esc to dismiss.</span></label><div class="composer-actions">${dictation.supported?`<button type="button" class="secondary" id="dictation-button" data-action="dictate" aria-pressed="false">语音输入 / Dictate</button>${select('识别语言 / Dictation language','dictation_lang',[['en-US','English'],['zh-CN','中文'],['es-ES','Español']],'en-US')}${select('语音处理方式 / Recognition mode','dictation_mode',[['local','仅设备识别 / On-device only'],['browser','浏览器服务 / Browser service']],'local')}`:''}<button type="submit" class="primary">一起理清下一步 / Make a plan</button></div><p id="dictation-status" role="status"></p></form><p class="hint">Your draft stays in this tab until you submit it. Voice is optional.</p><details class="dictation-disclosure"><summary>About voice & privacy</summary><p class="hint">This starts a care task, not a medical assessment. If you have symptoms, continue to the health-needs check. Typing does not use a speech service. On-device dictation needs browser support. Browser-service dictation may send audio and its content to a provider; FirstVisit does not control that provider’s retention or use. Dictation never submits automatically.</p></details><div class="scenario-shortcuts"><button type="button" class="text-button" data-action="saved">继续已保存的任务 / Resume a saved task</button></div></section>`;
}
function bindHome(){
  homeCompletion?.destroy();homeCompletion=null;
  bindDoctorSearch();
  if(S.homeMode==='doctor')return;
  homeCompletion=new GhostCompletion({input:$('#home-goal'),prefix:$('#goal-prefix'),suggestion:$('#goal-suggestion'),overlay:$('#goal-ghost'),button:$('#accept-completion'),getContext:()=>({kind:$('#home-intent')?.elements.kind.value||'general',locale:I18n.locale})});
  const guess=()=>{const el=$('#kind-guess'),form=$('#home-intent');if(!el||!form)return;const picked=form.elements.kind.value,k=inferKind($('#home-goal').value);if(picked!=='general'||!k){el.hidden=true;return;}el.hidden=false;el.innerHTML=`<span>看起来是 / Looks like:</span> <strong>${esc(JOURNEY_KINDS[k])}</strong> <button type="button" class="text-button" data-journey-kind="${k}">用这个 / Use this</button>`;I18n.apply(el);};
  $('#home-goal').addEventListener('input',e=>{S.homeGoal=e.target.value;guess();});guess();
  $('#home-intent').addEventListener('submit',e=>{e.preventDefault();S.homeGoal=$('#home-goal').value;S.homeKind=e.target.elements.kind.value;beginJourney(S.homeKind,S.homeGoal);});
}
function ensureLocalVault(next){
  if(S.state.unlocked)return next();
  if(S.state.vault_exists)return unlockDialog(next);
  openDialog('先建立本机私密空间 / Save privately',`<p>只设置加密口令，不要求提供姓名或完整健康档案。 / A passphrase encrypts saved tasks on this computer. No full profile is required.</p><form id="journey-vault">${field('本机加密口令 / Passphrase','passphrase','','password','required minlength="8" maxlength="1000" autocomplete="new-password"')}<button class="primary">创建并继续 / Create and continue</button></form>`);
  $('#journey-vault').addEventListener('submit',e=>{e.preventDefault();const passphrase=e.target.elements.passphrase.value;work(async()=>{S.state=await api('/api/vault/create',{passphrase});S.health=await api('/api/profile');closeDialog();await next();});});
}
function beginJourney(kind,goal){
  if(kind==='general')kind=inferKind(goal||'')||'general';
  const defaults={general:['我想整理这次需要的帮助。','I would like help sorting out what I need.'],insurance:['我想弄清保险能报什么，以及看病大概要自己付多少钱。','I want to understand what my insurance covers and roughly what a visit would cost me.'],first_visit:['我想找一位固定医生，并了解第一次联系诊所需要准备什么。','I would like a regular doctor and to know what to prepare when I first contact a practice.'],concern:['我想整理当前的困扰，准备下一步就医。','I want to organize my current concern and prepare for next steps in care.'],report:['我想整理已有报告，为下一次问诊做准备。','I want to organize my reports to prepare for my next visit.'],follow_up:['我想跟进检查结果或医生建议的后续事项。','I want to follow up on results or a next step my clinician recommended.']};
  const create=async()=>{S.journey=await api('/api/journeys',{kind,goal:goal?.trim()||(defaults[kind]||defaults.general)[I18n.locale==='zh'?0:1]});S.homeGoal='';S.state=await api('/api/state');S.view='journey';S.current=null;S.expect=null;closeDialog();render();window.scrollTo(0,0);};
  if(S.state.unlocked)return work(create);return ensureLocalVault(create);
}
function openJourney(id){return work(async()=>{const journey=await api('/api/journey?id='+encodeURIComponent(id));closeDialog();S.expect=null;if(journey.input){S.current=await api('/api/case?id='+encodeURIComponent(id));S.journey=journey;S.step=4;S.view='wizard';}else{S.journey=journey;S.current=null;S.view='journey';}render();window.scrollTo(0,0);});}
// Task shell: one progress line per care task plus "What we know" (the rules fact sheet, made visible).
const coverageFromInput=i=>i.insurance==='yes'?'insured':i.insurance==='no'?(i.wants_insurance?'choosing':'uninsured'):'unknown';
function taskOf(){
  if(S.view==='wizard'&&S.step<4&&!S.expect&&S.activeJourney&&S.journey){const j=S.journey;return {id:j.id,coverage:j.coverage_situation&&j.coverage_situation!=='unknown'?j.coverage_situation:coverageFromInput(S.input),hasShortlist:false,status:j.status,kind:j.kind,goal:j.goal};}
  if(S.view==='wizard'&&S.step===4&&S.current){const c=S.current;return {id:c.id,coverage:c.coverage_situation||'unknown',hasShortlist:true,chosen:!!c.contact?.provider_id,status:c.status,contactedAny:(c.results||[]).some(r=>(r.provider.answers||[]).length),comparedPlans:c.coverage_situation==='choosing'&&!!c.input?.plan?.name,kind:c.kind,goal:c.goal};}
  if(S.view==='journey'&&S.journey){const j=S.journey;return {id:j.id,coverage:j.coverage_situation||'unknown',hasShortlist:!!j.input,status:j.status,kind:j.kind,goal:j.goal};}
  return null;
}
const COVERAGE_TEXT={insured:'有保险 / Insured',uninsured:'目前没有保险 / No insurance right now',choosing:'正在选保险计划 / Choosing a plan',unknown:'还不知道 / Not answered yet'};
function taskShell(){
  // The progress line is an aid: if stages.js did not load, the task still works without it.
  if(typeof taskStages!=='function')return '';
  const t=taskOf();if(!t)return '';
  const c=S.view==='wizard'?S.current:null,stages=taskStages(t),plan=c?c.input?.plan?.name:(S.journey?.input?S.journey.input.plan?.name:S.health?.profile?.plan?.name);
  const known=c?c.results.filter(r=>r.supported&&r.cost.amount!=null&&!r.unavailable):[];
  const replies=c?c.results.reduce((n,r)=>n+(r.provider.answers||[]).length,0):0;
  const cost=c?(known.length?`有依据的最低费用 / Lowest supported cost: $${Math.min(...known.map(r=>r.cost.amount))}`:'未知，不按 0 计算 / Unknown, not $0'):(t.coverage==='insured'&&S.health?.profile?.plan_benefits?'按已核对的福利计算 / From reviewed benefits':'未知，不按 0 计算 / Unknown, not $0');
  const rows=[['类别 / Task',JOURNEY_KINDS[t.kind]||JOURNEY_KINDS.general],['保险 / Coverage',COVERAGE_TEXT[t.coverage]+(plan&&t.coverage==='insured'?` · ${plan}`:'')],['看病费用 / Visit cost',cost]];
  if(c)rows.push(['候选 / Options',I18n.locale==='zh'?`${c.results.length} 家 · ${replies} 条诊所答复`:`${c.results.length} options · ${replies} office replies`]);
  rows.push(['下一步 / Next',nextStep(stages,t.coverage)]);
  return `<nav class="task-stages" aria-label="Care task progress"><ol>${stages.map((s,i)=>`<li class="stage ${s.state}${s.locked?' locked':''}"><button type="button" data-stage="${s.id}" ${s.state==='current'?'aria-current="step"':''}><span class="stage-num">${s.state==='done'?'✓':i+1}</span><span>${esc(s.label)}</span></button></li>`).join('')}</ol></nav><details class="task-known" open><summary>目前已知 / What we know</summary><dl>${rows.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl></details>`;
}
function goStage(id){
  if(typeof taskStages!=='function')return;
  const t=taskOf();if(!t)return;
  const stage=taskStages(t).find(s=>s.id===id);
  if(stage?.locked)return toast('先回答保险问题 / Answer the coverage question first');
  // "Your need" is the task page itself; openJourney would bounce a task with a shortlist back to its results.
  if(id==='need')return S.view==='journey'?window.scrollTo(0,0):work(async()=>{S.journey=await api('/api/journey?id='+encodeURIComponent(t.id));S.current=null;S.expect=null;S.view='journey';render();window.scrollTo(0,0);});
  if(id==='coverage')return editProfile('coverage');
  // Choosing a plan compares plans; it never sends the person through clinic search (PLAN §3, G10).
  if(id==='plans')return work(openPlans);
  if(id==='clinic'||id==='contact'){if(t.hasShortlist){if(S.view!=='wizard')return openJourney(t.id);const el=$(id==='contact'&&$('.contact-checklist')?'.contact-checklist':'.results-layout');return window.scrollTo(0,el?el.getBoundingClientRect().top+window.scrollY:0);}const find=$('[data-action="journey-find"]');return find?find.click():toast('请先处理上面的提示 / Address the notice above first');}
  if(id==='after')return $('[data-action="record-visit"]')?.click()??toast('先联系诊所并预约 / Contact a clinic and book first');
  if(id==='enroll')return toast('通过学校或官方渠道投保；本应用不办理投保 / Enroll through your school or official channels; the app does not enroll you');
  if(id==='care')return toast('投保生效后，回到这里找医生 / Once covered, come back here to find care');
}
function renderJourney(){
  const j=S.journey;
  $('#app').innerHTML=`<div class="home">${taskShell()}<p class="eyebrow">${esc(JOURNEY_KINDS[j.kind]||'YOUR CARE TASK')}</p><h1 class="home-title">围绕你这次的目标 / Your next step</h1>${j.safety_notice?safetyPanel(j.safety_notice):''}<section class="form-card"><form id="journey-goal"><label class="field"><span>这次想完成什么？可随时修改 / Your goal</span><textarea name="goal" required maxlength="2000" rows="3">${esc(j.goal||'')}</textarea></label><button class="secondary small">保存目标 / Save goal</button></form><p>${esc(j.next_action)}</p></section>${coverageStep(j)}<div class="journey-action-grid"><section class="form-card"><h2>先准备，再决定 / Prepare first</h2><p>无需马上搜索。先整理你想问的问题和已有资料，不自动生成诊断或检查要求。</p><button class="primary" data-action="journey-prep">查看个人准备材料 / My preparation</button></section><section class="form-card"><h2>需要联系医生？ / Find care</h2><p>进入已有的需求核对、语言、保险、时间和位置流程。公开搜索仍需单独预览确认。</p>${j.safety_notice?.level==='emergency'?'<p>请先处理上面的紧急警示；此处不进入价格或诊所比较。 / Address the warning above before comparison.</p>':j.input?`<button class="secondary" data-case="${esc(j.id)}">查看已有候选 / View my shortlist</button>`:j.coverage_situation==='choosing'?'<p class="hint">你在选择保险计划：先比较计划，不需要先找诊所。 / You are choosing a plan: compare plans first; no clinic search is needed.</p><button class="primary" data-action="plans">比较保险计划 / Compare plans</button> <button class="text-button" data-action="journey-find">之后再找医生 / Find care later</button>':'<button class="secondary" data-action="journey-find">按需求找 / Find by what you need</button> <button class="text-button" data-action="doctor-search">按医生或诊所找 / By doctor or clinic</button>'}</section></div>${['follow_up','report'].includes(j.kind)||(j.reports||[]).length?`<section class="form-card"><h2>这次相关的资料 / Optional reports</h2><p>没有报告也可以继续。支持文本型检验 PDF；导入后逐项核对，原 PDF 不留存，确认的记录加密保存。</p><label class="secondary file-label">添加检验 PDF / Add lab PDF<input id="lab-file" type="file" accept="application/pdf" hidden></label>${(j.reports||[]).map(r=>`<details class="private-details"><summary><span data-i18n-keep>${esc(r.label)}</span> · <span data-i18n-keep>${r.rows.length}</span> <span>项 / results</span></summary><p class="hint"><span>用户核对 / Reviewed</span>: <span data-i18n-keep>${esc(r.source.reviewed_on)}</span> · <span>Source flags are not a diagnosis.</span></p><table class="report-table"><thead><tr><th>项目 / Test</th><th>结果 / Result</th><th>原文参考 / Reference</th><th>标记 / Flag</th></tr></thead><tbody>${r.rows.map(row=>`<tr><td>${esc(row.name)}</td><td>${esc(row.result)}</td><td>${esc(row.reference)}</td><td>${esc(row.flag||'—')}</td></tr>`).join('')}</tbody></table><button class="text-button" data-forget-report="${esc(r.id)}">删除这份资料 / Forget report</button></details>`).join('')||'<p class="hint">尚未添加资料，不影响开始。 / No report needed to get started.</p>'}</section>`:''}<button type="button" class="text-button" data-action="edit-profile">补充可复用的健康信息 / Add to my health profile</button></div>`;
  $('#journey-goal').addEventListener('submit',e=>{e.preventDefault();const goal=e.target.elements.goal.value;work(async()=>{S.journey=await api('/api/journey',{id:j.id,goal});render();toast('目标已保存 / Goal saved');});});
  $('#lab-file')?.addEventListener('change',e=>{const file=e.target.files[0];if(!file)return;if(file.size>6e6)return toast('PDF 最大 6 MB / Max 6 MB.');const reader=new FileReader();reader.onload=()=>work(async()=>{S.reportDraft=await api('/api/reports/preview',{journey_id:j.id,pdf_base64:String(reader.result).split(',')[1],file_name:file.name});S.view='report-review';render();});reader.readAsDataURL(file);});
}
function renderReportReview(){
 const draft=S.reportDraft;
 $('#app').innerHTML=`<div class="home"><p class="eyebrow">ON THIS DEVICE · REVIEW BEFORE SAVING</p><h1 class="home-title">先核对原文 / Check what we read</h1><p class="lede">仅提取报告事实。可以修正或忽略；确认前不会存入档案，也不会用报告推断诊断或安排复查。</p><form id="report-review">${field('资料名称 / Label','label',draft.label,'text','required maxlength="160"')}${draft.rows.map((r,i)=>`<section class="sub-card"><label class="checkline"><input type="checkbox" name="keep_${i}" checked><span>保留第 ${i+1} 项 / Keep result</span></label><div class="form-grid">${field('项目 / Test','name_'+i,r.name,'text','required maxlength="160"')}${field('结果和单位 / Result and unit','result_'+i,r.result,'text','required maxlength="160"')}${field('原文参考范围 / Reported reference','reference_'+i,r.reference,'text','maxlength="160"')}${select('原文标记 / Reported flag','flag_'+i,[['','无标记 / None'],['Low','Low'],['High','High']],r.flag)}</div><details><summary>原文依据 / Source text</summary><pre class="report-evidence">${esc(r.evidence)}</pre></details></section>`).join('')}<div class="form-actions"><button type="button" class="text-button" data-action="page-back">← 返回 / Back</button><button class="primary">我已核对，保存 / Confirm and save</button></div></form></div>`;
 $('#report-review').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.target);const rows=draft.rows.map((r,i)=>({omit:!f.has('keep_'+i),name:f.get('name_'+i),result:f.get('result_'+i),reference:f.get('reference_'+i),flag:f.get('flag_'+i)}));work(async()=>{S.journey=await api('/api/reports/confirm',{token:draft.token,confirmed:true,label:f.get('label'),rows});S.reportDraft=null;trail.clear();S.view='journey';render();});});
}
const prepSections=()=>(S.journey.preparation_view||{})[I18n.locale==='zh'?'zh':'en'];
const prepText=()=>{const secs=prepSections();return secs?secs.map(x=>x.title+':\n'+x.items.map(i=>'- '+i).join('\n')).join('\n\n'):S.journey.personal_preparation;};
function showPersonalPreparation(){const secs=prepSections();openDialog('我的问诊准备 / My preparation',`<p>这份材料供你核对和自行分享。还没有发送给医生或搜索服务。 / Review this and share it yourself. Nothing has been sent to a clinician or search service.</p>${secs?`<div class="personal-preparation" data-i18n-keep>${secs.map(x=>`<section class="prep-section"><h3>${esc(x.title)}</h3><ul>${x.items.map(i=>`<li>${esc(i)}</li>`).join('')}</ul></section>`).join('')}</div>`:`<pre class="personal-preparation">${esc(S.journey.personal_preparation)}</pre>`}<button class="secondary" data-action="copy-personal-prep">复制 / Copy</button>`,true);}
function startBrowserDictation(){
  if(dictation.rec){dictation.stop();return;}
  const mode=$('[name="dictation_mode"]')?.value||'local',lang=$('[name="dictation_lang"]')?.value||'en-US';
  const start=allowRemote=>dictation.start({lang,mode,allowRemote}).catch(error=>{toast(error.message);});
  if(mode==='local')return start(false);
  if(S.state.offline)return toast('应用离线模式下不启用浏览器服务语音。 / Browser-service dictation is disabled in app offline mode.');
  openDialog('语音内容会怎样处理？ / Before browser-service dictation',`<p>这会交给浏览器所选择的识别服务处理。录音包含你说的全部内容，可能被发送到厂商服务器。</p><p>FirstVisit 无法保证厂商不保存录音或转写、不用于改进服务、无人审核，也无法替你删除厂商副本。网站不能统一确认具体服务方和保留期限。</p><p>这条流量绕过 FirstVisit 网关，不会出现在我们的请求账本中。FirstVisit 不接收或保存音频；转写仅追加到输入框，不自动提交。</p><p>可以返回打字，或尝试仅设备识别。不要把“服务处理”理解为内容绝对私密。</p><div class="dialog-actions"><button class="secondary" data-action="close">返回打字 / Keep typing</button><button class="primary" id="allow-browser-dictation">我理解并启用本次识别 / Enable for this session</button></div>`,true);
  $('#allow-browser-dictation').addEventListener('click',()=>{S.browserVoiceUses=(S.browserVoiceUses||0)+1;closeDialog();start(true);});
}

function renderHome(){
  if(!S.state.unlocked){$('#app').innerHTML=`<div class="home">${homeComposer()}<p class="hint">开始保存任务时再设置本机加密口令。 / Set a local passphrase when you save your first task.</p></div>`;bindHome();return;}
  const h=S.health, p=h.profile, open=h.todos.filter(t=>!t.done_on), personal=open.filter(t=>['refill','follow_up'].includes(t.kind)), prevent=open.filter(t=>!['refill','follow_up'].includes(t.kind)), done=h.todos.filter(t=>t.done_on);
  const list=(arr)=>arr.length?arr.map(t=>`<span class="tag">${esc(t)}</span>`).join(''):'<span class="muted">None added</span>';
  $('#app').innerHTML=`<div class="home">
  ${homeComposer()}
  <section class="form-card"><div class="form-card-head"><h3>Continue your care</h3><p>Saved tasks and the next action.</p></div>${(S.state.cases||[]).filter(c=>c.status!=='attended').length?(S.state.cases||[]).filter(c=>c.status!=='attended').map(c=>`<div class="visit-row"><div><strong>${caseLabel(c)}${c.city?` · <span data-i18n-keep>${esc(c.city)}</span>`:''}${c.demo?' · <span>Fictional demo</span>':''}</strong><p>${esc(c.next_action||'Review your next step')}</p><button class="text-button" data-case="${esc(c.id)}">Continue journey →</button></div></div>`).join(''):'<p class="hint">No unfinished care journeys.</p>'}</section>
  <details class="example-drawer"><summary>先看看示例 / Explore an example</summary><p>Fictional student inputs with real clinic sources. This does not change your profile.</p><button type="button" class="secondary small" data-action="neu-example">Explore NEU / 02445</button></details>
  ${!S.state.profile_ready?'<details class="optional-profile"><summary>可选：补充可复用的健康信息 / Optional health profile</summary>':''}<div class="home-grid">
    <section class="form-card"><div class="form-card-head row"><h3>Your health</h3><button type="button" class="text-button" data-action="edit-profile">Edit</button></div>
      <div class="facts"><div><span>Age</span><strong>${h.age??'—'}</strong></div><div><span>Language</span><strong>${esc(p.language||'English')}</strong></div><div><span>Coverage</span><strong>${p.insurance==='yes'?esc(p.plan?.name||'Insured'):p.insurance==='no'?(p.wants_insurance?'Choosing a plan':'No insurance'):'—'}</strong></div></div>
      <div class="fact-list"><span>Conditions</span><div>${list(p.conditions||[])}</div></div>
      <div class="fact-list"><span>Medications</span><div>${list(p.medications||[])}</div></div>
      <div class="fact-list"><span>Allergies</span><div>${list(p.allergies||[])}</div></div>
      <div class="fact-list"><span>Follow-ups</span><div>${list((p.follow_ups||[]).map(f=>f.what+(f.due?` · ${f.due}`:'')))}</div></div></section>
    <section class="form-card"><div class="form-card-head"><h3>Your to-dos</h3><p>From your profile and official guidance. Ask a clinician what fits you.</p></div>
      ${personal.length?`<p class="sub-title">For you</p>${personal.map(todoRow).join('')}`:''}
      ${prevent.length?`<p class="sub-title">Checkups and vaccines for your age</p>${prevent.map(todoRow).join('')}`:'<p class="hint">Add your birth year to see checkups and vaccines for your age.</p>'}
      ${done.length?`<details class="private-details"><summary>Done (${done.length})</summary>${done.map(todoRow).join('')}</details>`:''}</section>
    <section class="form-card"><div class="form-card-head row"><h3>Your visits</h3><button type="button" class="text-button" data-action="record-visit">+ Record a visit</button></div>${(p.visits||[]).length?(p.visits||[]).slice(0,5).map(v=>`<div class="visit-row"><span class="visit-date">${esc(v.date)}</span><div><strong data-i18n-keep>${esc(v.reason)}</strong><p>${esc(v.place||'Place not recorded')}${(v.added?.medications||[]).length||(v.added?.follow_ups||[]).length?` · added ${[...(v.added.medications||[]),...(v.added.follow_ups||[])].map(esc).join(', ')}`:''}</p></div></div>`).join(''):'<p class="hint">After a visit, record what happened. New medicines and follow-ups become your next to-dos.</p>'}</section>
    <section class="form-card"><div class="form-card-head row"><h3>Better choices</h3>${p.insurance==='no'?'<button type="button" class="text-button" data-action="plans">Compare plans →</button>':''}</div>${h.choices.map(c=>`<div class="choice-tip"><strong>${esc(c.title)}</strong><p>${esc(c.why)}${c.source?` · <a href="${esc(c.source.url)}" target="_blank" rel="noopener noreferrer">${esc(c.source.title)}</a>`:''}</p></div>`).join('')}</section>
  </div>${!S.state.profile_ready?'</details>':''}</div>`;
  bindHome();
}
function listRows(kind,rows){
  const [a,b,la,lb,ta]=kind==='med'?['name','refill_by','Medication','Runs out (optional)','text']:['what','due','What','Due (optional)','text'];
  return `<div class="rows">${rows.map((r,i)=>`<div class="row-2">${field(la,`${kind}_${a}_${i}`,r[a],ta,'maxlength="160"')}${field(lb,`${kind}_${b}_${i}`,r[b],'date')}</div>`).join('')}</div><button type="button" class="secondary small" data-add-row="${kind}">+ Add ${kind==='med'?'medication':'follow-up'}</button>`;
}
function renderProfile(){
  const d=S.draft, first=!S.state.vault_exists;
  const coverage=card('Coverage','Do you have health insurance?',`<div class="choice-grid"><button type="button" class="choice ${d.insurance==='yes'?'selected':''}" data-pins="yes"><span class="choice-radio"></span><strong>Yes</strong><span>I have a plan</span></button><button type="button" class="choice ${d.insurance==='no'?'selected':''}" data-pins="no"><span class="choice-radio"></span><strong>Not right now</strong><span>Self-pay, or choosing a plan</span></button></div>${d.insurance==='yes'?`<div class="sub-card"><p class="sub-title">Your plan</p>${field('Exact plan name','pplan_name',d.plan?.name||'','text','maxlength="120"')}</div>${sbcBox()}`:''}${d.insurance==='no'?`<label class="checkline"><input type="checkbox" name="wants_insurance" ${d.wants_insurance?'checked':''}><span>I’m thinking about getting a plan</span></label>`:''}`);
  if(S.profileFocus==='coverage'&&S.state.vault_exists){
    $('#app').innerHTML=`<div class="home narrow"><form id="profile-form"><p class="eyebrow">YOUR COVERAGE</p><h1 class="home-title">Your insurance</h1><p class="lede">Only this part is needed for your insurance questions. It stays encrypted on this device.</p>${coverage}<div class="form-actions"><button type="button" class="text-button" data-action="page-back">← Cancel</button><button type="submit" class="primary">Save ${icon('arrow')}</button></div></form></div>`;
    $('#profile-form').addEventListener('submit',e=>{e.preventDefault();saveProfile();});
    bindSbcFile();return;
  }
  $('#app').innerHTML=`<div class="home"><form id="profile-form"><p class="eyebrow">${first?'START HERE':'YOUR HEALTH PROFILE'}</p><h1 class="home-title">${first?'Let’s get to know your health.':'Your health profile'}</h1><p class="lede">It stays encrypted on this device and grows with every visit. Skip anything you don’t want to add.</p>
    ${card('About you','Your age decides which checkups and vaccines we suggest.',`<div class="form-grid three">${field('Birth year','birth_year',d.birth_year??'','number','min="1900" max="'+new Date().getFullYear()+'" step="1" inputmode="numeric" required')}${select('Sex (optional)','sex',[['','Prefer not to say'],['female','Female'],['male','Male']],d.sex||'')}${select('Preferred language','language',[['English','English'],['Chinese','Chinese / 中文'],['Spanish','Spanish / Español']],d.language||'English')}</div><p class="hint">Sex is only used for screenings like cervical or breast cancer checks.</p>`)}
    ${card('Ongoing health','Optional. Separate items with commas.',`<label class="field"><span>Conditions</span><textarea name="conditions" rows="2" maxlength="2000" placeholder="Asthma, migraines">${esc((d.conditions||[]).join(', '))}</textarea></label><label class="field"><span>Allergies</span><textarea name="allergies" rows="2" maxlength="2000" placeholder="Penicillin, peanuts">${esc((d.allergies||[]).join(', '))}</textarea></label>`)}
    ${card('Medications','We’ll remind you before one runs out.',listRows('med',d.meds))}
    ${card('Follow-ups','Visits or tests a clinician asked you to come back for.',listRows('fu',d.fus))}
    ${coverage}
    ${!S.state.vault_exists?card('Save it privately','Choose a passphrase. It encrypts your profile on this computer. There is no recovery.',field('Passphrase','passphrase','','password','required minlength="8" maxlength="1000" autocomplete="new-password"')):''}
    <div class="form-actions">${first?'<span class="small-note">You can change this anytime.</span>':'<button type="button" class="text-button" data-action="page-back">← Cancel</button>'}<button type="submit" class="primary">${first?'Save and continue':'Save'} ${icon('arrow')}</button></div></form></div>`;
  $('#profile-form').addEventListener('submit',e=>{e.preventDefault();saveProfile();});
  bindSbcFile();
}
function bindSbcFile(){
  $('#sbc-file')?.addEventListener('change',e=>{const file=e.target.files[0];if(!file)return;if(file.size>6e6)return toast('That PDF is too large (6 MB max).');
    const rd=new FileReader();rd.onload=()=>sendSbc({pdf_base64:String(rd.result).split(',')[1],file_name:file.name});rd.readAsDataURL(file);});
}
function readDraft(){
  const f=$('#profile-form'); if(!f) return; const g=n=>f.elements[n]?.value??'', has=n=>!!f.elements[n], list=n=>g(n).split(',').map(x=>x.trim()).filter(Boolean);
  // A focused editor (coverage only) must not blank fields that are not on the page.
  for(const k of ['birth_year','sex','language'])if(has(k))S.draft[k]=g(k);
  for(const k of ['conditions','allergies'])if(has(k))S.draft[k]=list(k);
  if(has('med_name_0'))S.draft.meds=S.draft.meds.map((_,i)=>({name:g(`med_name_${i}`),refill_by:g(`med_refill_by_${i}`)}));
  if(has('fu_what_0'))S.draft.fus=S.draft.fus.map((_,i)=>({what:g(`fu_what_${i}`),due:g(`fu_due_${i}`)}));
  if(has('wants_insurance'))S.draft.wants_insurance=f.elements.wants_insurance.checked;
  if(f.elements.pplan_name) S.draft.plan={...(S.draft.plan||{}),name:g('pplan_name')};
}
function editProfile(focus=null){
  S.profileFocus=focus;
  const p=S.health?.profile||{}, r=p.refills||{};
  S.draft={birth_year:p.birth_year,sex:p.sex,language:p.language,conditions:p.conditions||[],allergies:p.allergies||[],insurance:p.insurance||'',wants_insurance:!!p.wants_insurance,plan:p.plan,
    meds:(p.medications||[]).map(n=>({name:n,refill_by:r[n]||''})).concat([{name:'',refill_by:''}]),fus:(p.follow_ups||[]).map(f=>({...f})).concat([{what:'',due:''}])};
  S.view='profile'; render(); window.scrollTo(0,0);
}
async function saveProfile(){
  if(!$('#profile-form').reportValidity()) return; readDraft(); const d=S.draft;
  await work(async()=>{
    if(!S.state.vault_exists){ const pass=$('[name="passphrase"]').value; S.state=await api('/api/vault/create',{passphrase:pass}); }
    S.justCreated=!S.state.profile_ready;
    const plan=d.insurance==='yes'&&d.plan?.name?{rule:'copay',...d.plan}:(d.plan?.name?d.plan:null);
    S.health=await api('/api/profile',{birth_year:d.birth_year,sex:d.sex,language:d.language,conditions:d.conditions,allergies:d.allergies,medications:d.meds.filter(m=>m.name.trim()),follow_ups:d.fus.filter(f=>f.what.trim()),insurance:d.insurance,wants_insurance:d.insurance==='no'&&d.wants_insurance,plan});
    S.state=await api('/api/state');
    if(S.profileFocus==='coverage'&&S.journey){S.profileFocus=null;S.journey=await api('/api/journey?id='+encodeURIComponent(S.journey.id));trail.clear();S.view='journey';render();window.scrollTo(0,0);toast('Saved. Your questions now match your coverage.');return;}
    S.profileFocus=null; S.view='home'; render(); window.scrollTo(0,0); toast('Saved on this device.');
  });
}
function visitReason(c){
  if(!c) return '';
  const labels=(c.input.safety?.checks||[]).map(id=>S.choices.find(x=>x.id===id)?.label).filter(Boolean);
  return labels.length?labels.join('; '):serviceName(c.input.service);
}
function recordVisit(){
  const c=S.current, chosen=c?.contact?.provider_id?c.providers.find(x=>x.id===c.contact.provider_id):null;
  S.visit={case_id:c?.id||'',date:S.state.today||today(),reason:visitReason(c),place:chosen?.name||'',places:c?c.providers.map(x=>x.name):[],notes:'',meds:[{name:'',refill_by:''}],fus:[{what:'',due:''}],conditions:'',completed:[]};
  S.view='visit'; render(); window.scrollTo(0,0);
}
function readVisit(){
  const f=$('#visit-form'); if(!f) return; const g=n=>f.elements[n]?.value??'';
  Object.assign(S.visit,{date:g('v_date'),reason:g('v_reason'),place:g('v_place'),notes:g('v_notes'),conditions:g('v_conditions'),
    meds:S.visit.meds.map((_,i)=>({name:g(`med_name_${i}`),refill_by:g(`med_refill_by_${i}`)})),fus:S.visit.fus.map((_,i)=>({what:g(`fu_what_${i}`),due:g(`fu_due_${i}`)})),
    completed:[...f.querySelectorAll('[name=v_done]:checked')].map(x=>x.value)});
}
function renderVisit(){
  const v=S.visit, open=(S.health?.profile?.follow_ups||[]);
  $('#app').innerHTML=`<div class="home narrow"><form id="visit-form"><p class="eyebrow">AFTER YOUR VISIT</p><h1 class="home-title">What happened at your visit?</h1><p class="lede">A minute now saves you from remembering later. It’s added to your encrypted health profile.</p>
    ${card('The visit','',`<div class="form-grid">${field('When','v_date',v.date,'date',`required max="${today()}"`)}${field('Where','v_place',v.place,'text','maxlength="160" list="v-places" placeholder="Clinic or doctor"')}</div><datalist id="v-places">${v.places.map(n=>`<option value="${esc(n)}">`).join('')}</datalist>${field('What it was for','v_reason',v.reason,'text','required maxlength="200"')}<label class="field"><span>What the clinician said <small>Optional · stays local</small></span><textarea name="v_notes" rows="3" maxlength="2000" placeholder="Come back in 3 months. Get blood work before then.">${esc(v.notes)}</textarea></label>`)}
    ${card('New medicines','We’ll remind you before they run out.',listRows('med',v.meds))}
    ${card('Follow-ups','Did they ask you to come back, or get a test?',listRows('fu',v.fus)+(open.length?`<div class="sub-card"><p class="sub-title">Was this visit one of your follow-ups?</p>${open.map(f=>`<label class="checkline"><input type="checkbox" name="v_done" value="${esc(f.what)}" ${v.completed.includes(f.what)?'checked':''}><span>${esc(f.what)}</span></label>`).join('')}</div>`:''))}
    ${card('Anything new to remember?','Optional. A new ongoing condition, separated by commas.',`<label class="field"><span>New conditions</span><input name="v_conditions" value="${esc(v.conditions)}" maxlength="400" placeholder="Seasonal allergies"></label>`)}
    <div class="form-actions"><button type="button" class="text-button" data-action="${S.current?'back-to-results':'home-page'}">← Cancel</button><button type="submit" class="primary">Save to my profile ${icon('arrow')}</button></div></form></div>`;
  $('#visit-form').addEventListener('submit',e=>{e.preventDefault();saveVisit();});
}
async function saveVisit(){
  if(!$('#visit-form').reportValidity()) return; readVisit(); const v=S.visit;
  await work(async()=>{
    S.health=await api('/api/visit',{case_id:v.case_id,date:v.date,reason:v.reason,place:v.place,notes:v.notes,
      medications:v.meds.filter(m=>m.name.trim()),follow_ups:v.fus.filter(f=>f.what.trim()),conditions:v.conditions,completed_follow_ups:v.completed});
    S.visit=null; S.current=null; S.state=await api('/api/state'); trail.clear(); S.view='home'; S.justCreated=false; render(); window.scrollTo(0,0);
    const a=S.health.visit.added, n=a.medications.length+a.follow_ups.length+a.conditions.length;
    toast(n?`Saved. ${n} ${n===1?'item was':'items were'} added to your profile.`:'Visit saved to your profile.');
  });
}
function sbcBox(){
  const b=S.health?.benefits;
  if(!S.state.unlocked) return '<p class="hint">After you save, you can upload your plan’s benefits summary (SBC) to fill in your costs.</p>';
  return `<div class="sub-card upload"><p class="sub-title">Your plan’s benefits summary (SBC)</p>${b?`<p class="sbc-done">${icon('check')} Read from <strong>${esc(b.source?.file||'SBC')}</strong> on ${esc(b.source?.read_on||'')}: ${esc(b.name)}</p>`:'<p class="hint">Every US plan publishes a standard “Summary of Benefits and Coverage” PDF. Upload it and we’ll read your copays, deductible and out-of-pocket limit. It’s read on this computer and never uploaded anywhere.</p>'}
    <label class="secondary small file-btn">${icon('arrow')} ${b?'Replace with a new SBC':'Upload SBC (PDF)'}<input type="file" id="sbc-file" accept="application/pdf,.pdf" hidden></label>
    <details class="private-details"><summary>Or paste the SBC text</summary><textarea id="sbc-text" rows="5" maxlength="200000" placeholder="Paste the text of your plan’s Summary of Benefits and Coverage"></textarea><button type="button" class="secondary small" data-action="sbc-paste">Read pasted text</button></details></div>`;
}
async function sendSbc(body){
  readDraft();
  await work(async()=>{S.sbc=await api('/api/plan/sbc',body);S.view='sbc';render();window.scrollTo(0,0);},'Reading your plan on this computer…');
}
function costInputs(key,svc){
  const c=svc.cost||{kind:'unknown'};
  return `<div class="sbc-row"><div class="sbc-label"><strong>${esc(svc.label)}</strong>${svc.evidence?`<q>${esc(svc.evidence)}</q>`:'<q class="missing">Not found in the document</q>'}</div>
    <div class="sbc-edit"><select name="k_${key}" aria-label="${esc(svc.label)} cost type">${[['copay','Copay'],['coinsurance','Coinsurance'],['free','No charge'],['not_covered','Not covered'],['unknown','Don’t know']].map(([v,t])=>`<option value="${v}" ${c.kind===v?'selected':''}>${t}</option>`).join('')}</select>
    <input type="number" min="0" step="0.01" name="v_${key}" value="${c.kind==='copay'?c.amount:c.kind==='coinsurance'?c.pct:''}" placeholder="$ or %" aria-label="${esc(svc.label)} amount">
    <label class="checkline small-check"><input type="checkbox" name="d_${key}" ${c.after_deductible?'checked':''}><span>after deductible</span></label></div></div>`;
}
function renderSbc(){
  const r=S.sbc, f=r.fields, ev=k=>f[k]?.evidence?`<q>${esc(f[k].evidence)}</q>`:'<q class="missing">Not found</q>';
  $('#app').innerHTML=`<div class="home"><form id="sbc-form"><p class="eyebrow">CHECK WHAT WE READ</p><h1 class="home-title">Is this right?</h1><p class="lede">We read ${r.found} values from <strong>${esc(r.source.file)}</strong> on this computer, with fixed rules. Each one shows the line it came from. Fix anything that’s off, then save.</p>
    ${r.is_sbc?'':'<div class="notice">This doesn’t look like a standard SBC. Check every value carefully.</div>'}
    ${card('The plan','',`${field('Plan name','name',f.name?.value||'','text','required maxlength="120"')}${ev('name')}<div class="form-grid">${field('Coverage starts','start',f.start?.value||'','date')}${field('Coverage ends','end',f.end?.value||'','date')}</div><div class="form-grid three">${field('Deductible ($)','deductible',f.deductible?.value??'','number','min="0" step="0.01"')}${field('Used so far this year ($)','deductible_used','','number','min="0" step="0.01" placeholder="0 if none"')}${field('Out-of-pocket limit ($)','oop_max',f.oop_max?.value??'','number','min="0" step="0.01"')}</div>${ev('deductible')}${ev('oop_max')}${field('Monthly premium ($, optional)','premium','','number','min="0" step="0.01"')}`)}
    ${card('What you pay for each kind of care','In-network, as the SBC says.',Object.entries(r.services).map(([k,v])=>costInputs(k,v)).join(''))}
    <p class="computed">${icon('lock')} ${esc(r.source.how)} The file itself isn’t saved, only these values and a fingerprint of the file.</p>
    <div class="form-actions"><button type="button" class="text-button" data-action="page-back">← 返回 / Back</button><button type="submit" class="primary">Save to my profile ${icon('arrow')}</button></div></form></div>`;
  $('#sbc-form').addEventListener('submit',e=>{e.preventDefault();saveSbc();});
}
async function saveSbc(){
  const f=$('#sbc-form'); if(!f.reportValidity()) return; const g=n=>f.elements[n]?.value??'';
  const services={}; Object.keys(S.sbc.services).forEach(k=>{const kind=g(`k_${k}`),v=g(`v_${k}`),d=f.elements[`d_${k}`]?.checked;services[k]=kind==='copay'?{kind,amount:v,after_deductible:d}:kind==='coinsurance'?{kind,pct:v,after_deductible:d}:{kind};});
  await work(async()=>{S.health=await api('/api/plan/benefits',{name:g('name'),start:g('start'),end:g('end'),deductible:g('deductible'),deductible_used:g('deductible_used'),oop_max:g('oop_max'),premium:g('premium'),services,source:S.sbc.source});
    S.sbc=null;S.state=await api('/api/state');S.view='home';render();window.scrollTo(0,0);toast('Your plan’s costs are saved on this device.');});
}
function renderGate(){
  $('#app').innerHTML=`<div class="home narrow"><p class="eyebrow">WELCOME BACK</p><h1 class="home-title">Unlock your health profile.</h1><p class="lede">A health profile is saved on this computer. It’s encrypted, so it needs your passphrase. For your privacy it locks itself after a while.</p><form id="gate-form"><section class="form-card">${field('Your passphrase','passphrase','','password','required minlength="8" maxlength="1000" autocomplete="current-password"')}${S.state.preview_mode?'<p class="hint">Test preview passphrase: <code>firstvisit-preview-only</code></p>':''}</section><div class="form-actions"><span class="small-note">Nothing is sent anywhere.</span><button type="submit" class="primary">Unlock ${icon('arrow')}</button></div></form>
  <section class="form-card new-here"><div class="form-card-head"><h3>New here, or forgot your passphrase?</h3><p>Start a new profile. This erases the saved profile on this computer. There’s no way to recover it.</p></div><button type="button" class="secondary" data-action="start-over">Start a new profile</button></section></div>`;
  $('#gate-form').addEventListener('submit',e=>{e.preventDefault();work(async()=>{S.state=await api('/api/vault/unlock',{passphrase:$('[name="passphrase"]').value});await afterUnlock();});});
}
async function afterUnlock(){ S.justCreated=false; S.health=await api('/api/profile');S.state=await api('/api/state');S.view='home';render(); }
function renderKnown(){
  const p=S.health.profile, row=(field,value,label)=>`<div class="known-row"><span>${esc(label)}</span><button type="button" class="text-button" data-forget="${field}" data-value="${esc(value)}">Forget</button></div>`;
  const rows=[...(p.birth_year?[row('birth_year','',`Birth year ${p.birth_year}`)]:[]),...(p.sex?[row('sex','',`Sex: ${p.sex}`)]:[]),...(p.conditions||[]).map(v=>row('conditions',v,`Condition: ${v}`)),...(p.medications||[]).map(v=>row('medications',v,`Medication: ${v}`)),...(p.allergies||[]).map(v=>row('allergies',v,`Allergy: ${v}`)),...(p.follow_ups||[]).map(f=>row('follow_ups',f.what,`Follow-up: ${f.what}`)),...(p.plan?[row('plan','',`Plan: ${p.plan.name}`)]:[]),...(p.visits||[]).map(v=>row('visit',v.id,`Visit ${v.date}: ${v.reason}`)),row('visits','',`Saved searches and all visits: ${S.state.cases.length} searches, ${(p.visits||[]).length} visits`)];
  $('#app').innerHTML=`<div class="home narrow"><p class="eyebrow">WHAT WE KNOW</p><h1 class="home-title">Everything FirstVisit knows about you.</h1><p class="lede">All of it is encrypted on this device. None of it is sent with searches.</p><details class="form-card"><summary>Sources and review dates</summary>${Object.entries(p.fact_sources||{}).map(([k,v])=>`<p><strong>${esc(k)}</strong><br>${esc(v.source)} · ${esc(v.reviewed_on||'Date not recorded')}. User-reported; review whether still current.</p>`).join('')||'<p>Older profile: source dates were not recorded. Review and save your profile to add a review date.</p>'}</details>${card('Your saved information','Forget any item. This can’t be undone.',`<div class="known">${rows.join('')}</div>`)}<div class="form-actions"><button type="button" class="text-button" data-action="page-back">← 返回 / Back</button><button type="button" class="secondary" data-forget="everything">Forget everything</button></div></div>`;
}
function render() {
  homeCompletion?.destroy();homeCompletion=null;
  dictation.abort();
  trackPage();
  renderHeader();
  if (S.view==='loading') { $('#app').innerHTML='<div class="home"><p class="lede">Loading…</p></div>'; return; }
  if (S.view==='gate') return renderGate();
  if (S.view==='profile') return renderProfile();
  if (S.view==='home') return renderHome();
  if (S.view==='journey') return renderJourney();
  if (S.view==='report-review') return renderReportReview();
  if (S.view==='known') return renderKnown();
  if (S.view==='visit') return renderVisit();
  if (S.view==='plans') return renderPlans();
  if (S.view==='sbc') return renderSbc();
  if (S.expect) return renderExpect();
  if (S.step===4 && S.current) return renderResults();
  const inTask=!!(S.activeJourney&&S.journey);
  $('#app').innerHTML = `${inTask?`<div class="home task-wizard">${taskShell()}${subSteps()}`:`<div class="wizard-layout">${sidebar()}`}<section class="form-panel">${S.input.scenario==='neu_student'?'<div class="notice">DEFAULT STUDENT INSURANCE SCENARIO · Northeastern / Brookline 02445. Review this illustrative person and confirm your exact current-year plan; benefits and enrollment are not pre-confirmed.</div>':''}${S.input.demo?'<div class="demo-banner">FICTIONAL DEMO · No actual providers, prices, ratings or insurance offers</div>':''}<form id="wizard">${stepContent()}${S.step===0?'':`<div class="form-actions">${S.step>0?'<button type="button" class="text-button" data-action="page-back">← 返回上一步 / Previous step</button>':'<span class="small-note">A few steps to a clearer choice.</span>'}<button type="submit" class="primary">${S.step===3?(S.preview?'Find my care':'Review search'):'Continue'} ${icon('arrow')}</button></div>`}<div id="working" role="status" class="working"></div></form></section></div>`;
  $('#wizard').addEventListener('submit', event => {event.preventDefault(); advance();});
}
async function advance() {
  if (!$('#wizard').reportValidity()) return;
  collect();
  rememberPage();
  if(S.step===0){
    if(S.sub==='symptoms' && !S.input.checks.length && !S.input.description.trim()) return toast('Pick what’s bothering you, or describe it in a few words.');
    if(S.sub==='need'){
      if(!S.input.need) return toast('Choose what you need.');
      if(S.input.need==='unsure'){ S.sub='symptoms'; S.input.feel='unsure'; render(); return toast('Tell us what’s going on first.'); }
    }
    let r; try{ r=await api('/api/safety',{checks:S.input.checks,description:S.input.description}); }catch(e){ return toast(e.message); }
    const reviewedSameDay=S.safety?.level==='same_day';
    S.safety=r;
    if(r.level==='emergency'){render();$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});return;}
    if(r.level==='same_day'){
      S.input.service='same_day';
      // First reveal a newly detected warning. Its single primary action then continues.
      if(!reviewedSameDay){render();$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});return;}
    }else if(S.input.service==='same_day'){
      S.input.service=S.input.need==='follow_up'?'follow_up':'primary_care';
    }
  }
  if(S.step===1 && Number(S.input.age)<18) return toast('This version supports adults (18+). For a child or teen, contact a pediatric clinician.');
  if(S.step===0 && S.input.scenario!=='neu_student' && S.input.insurance==='yes' && S.health?.plan_by_service?.[S.input.service]) S.input.plan=S.health.plan_by_service[S.input.service];
  if(S.step===1 && !S.input.insurance) return toast('Choose whether you have insurance.');
  if(S.step<3) {S.step++; S.preview=null; render(); window.scrollTo(0,0); return;}
  await work(async()=>{
    if (!S.state.unlocked) {
      const passphrase=$('[name="passphrase"]').value;
      S.state=await api(S.state.vault_exists?'/api/vault/unlock':'/api/vault/create',{passphrase});
      $('[name="passphrase"]').value='';
    }
    if(!S.preview) {S.preview=await api('/api/preview',{...S.input,journey_id:S.activeJourney||''}); render(); return;}
    const body={token:S.preview.token,approved:true,live:!!$('[name="live"]')?.checked};
    S.expect={data:S.preview.expect,status:'searching',found:null}; S.preview=null; renderExpect(); window.scrollTo(0,0);
    try{ const result=await api('/api/search',body); S.found=result; S.expect.status='ready'; S.expect.found=result.results.length; S.state=await api('/api/state');
      if(!S.expect.data.illustration){S.view='wizard';S.current=S.found;S.found=null;S.expect=null;S.step=4;render();window.scrollTo(0,0);toast(`找到 ${result.results.length} 家 / ${result.results.length} options found`);return;} }
    catch(e){ S.expect.status='error'; S.expect.error=e.message; }
    renderExpect();
  },'Finding care and checking the available evidence…');
}
function costLabel(cost) {return ({unknown:'Needs confirmation',not_active:'Outside coverage dates',demo:'Synthetic example',conditional:'Conditional estimate',user_quote:'User-entered quote'})[cost.status] || 'Estimate';}
function compareBlock(row, compact=true) {
  const c=row.comparison;
  return `<div class="comparison ${compact?'compact':''}"><div class="compare-line"><span>Same visit, self-pay</span><strong>${dollars(c.cash.amount)}</strong></div><div class="compare-line"><span>Your share with this plan</span><strong>${dollars(c.insured.amount)}</strong></div><div class="compare-line"><span>Premiums × ${c.months} month${c.months===1?'':'s'}</span><strong>${dollars(c.premium_total)}</strong></div><div class="compare-line total"><span>Visit + premiums</span><strong>${dollars(c.total_with_plan)}</strong></div>${c.net_difference!=null?`<div class="difference ${c.net_difference>0?'positive':''}">${c.net_difference>0?`${dollars(c.net_difference)} less`:c.net_difference<0?`${dollars(-c.net_difference)} more`:'Same estimated total'} <span>than self-pay for this scenario</span></div>`:`<p class="hint">${esc(c.insured.amount==null?c.insured.reason:c.note)}</p>`}<p class="hint">One visit only. ${c.eligible?'Eligibility entered as confirmed.':'Eligibility not confirmed.'} ${esc(c.scope)}</p></div>`;
}
// Prior-year NUSHP copay as a labeled reference; the supported cost above is unchanged.
const refCopay=p=>{const r=S.current?.plan_reference?.reference_copays;if(!r||p.demo||S.current?.input?.insurance!=='yes')return '';const v=r[p.id]??r.default_in_network;return I18n.locale==='zh'?`<small class="ref-copay" data-i18n-keep>往年参考：如在网络内，门诊 copay $${esc(v)} · ${esc(r.label)}。需确认 2026–27 年度。</small>`:`<small class="ref-copay" data-i18n-keep>Prior-year reference: $${esc(v)} office-visit copay if in network · ${esc(r.label)}. Confirm for 2026–27.</small>`;};
function providerCard(row,index) {
  const p=row.provider, rating=p.rating;
  const link=p.url?`<a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer" class="text-button">View source ↗</a>`:'<span class="hint">Fictional provider; no booking link</span>';
  return `<article class="provider-card ${index===0&&row.supported&&row.cost.amount!=null&&!row.unavailable?'first':''}"><div class="card-top"><div class="provider-avatar">${icon('building')}</div><div class="provider-title"><div class="provider-label">${esc(p.kind)}${p.demo?' · DEMO':''}</div><h3>${esc(p.name)}</h3><p>${esc(p.address)}${p.phone?' · '+esc(p.phone):''}</p>${directionsLink(p)} ${bookingLink(p)}</div><span class="rank">${row.supported&&row.cost.amount!=null&&!row.unavailable?String(index+1).padStart(2,'0'):'?'}</span></div><div class="card-stats"><div><span>YOUR VISIT COST</span><strong class="price">${dollars(row.cost.amount)}</strong><small>${costLabel(row.cost)} · ${row.pathway}</small>${refCopay(p)}</div><div><span>PATIENT EXPERIENCE</span><strong>${rating?`<span class="star">★</span> ${rating.value.toFixed(1)} <small>/ 5</small>`:'Not available'}</strong><small>${rating?`${rating.count} ${p.demo?'synthetic':'user-entered'} reviews`:'No sourced rating yet'}</small></div><div><span>DISTANCE</span><strong>${row.miles==null?'Not verified':`${row.miles} mi`}</strong><small>${row.miles==null?'Check the source location':'Straight-line; not travel time'}</small></div></div><ul class="match-reasons">${row.reasons.map(r=>`<li>${icon('check')}${esc(r)}</li>`).join('')}</ul>${row.confirmation?.length?`<details class="evidence" open><summary>Next: confirm with this office</summary><ul>${row.confirmation.map(t=>`<li>${esc(t.question)}${t.reason?`<p class="hint">${esc(t.reason)}</p>`:''}</li>`).join('')}</ul><p class="hint">Save price, service and network answers using Add quote / confirmation. Use Record office reply for availability, language and referral answers. Record appointment outcomes separately.</p></details>`:''}<details class="evidence"><summary>Cost, insurance & evidence</summary><p>${esc(p.source_note)}</p><p class="hint">Source checked: ${esc(p.checked_on)}. Patient reviews describe experience, not clinical quality.</p>${rating?`<p class="hint">Rating source: ${esc(rating.source)} · ${esc(rating.checked_on)}</p>`:''}<p><strong>Insurance:</strong> ${esc(row.insured.reason)}</p>${row.cost.breakdown.map(b=>`<div class="compare-line"><span>${esc(b.label)}</span><strong>${dollars(b.amount)}</strong></div>`).join('')}<p class="hint">Price source: ${esc(row.cost.source || 'No scoped price yet')}${row.cost.checked_on?' · '+esc(row.cost.checked_on):''}</p>${S.current.input.plan?compareBlock(row):'<p>Add a plan to compare the same visit with insurance.</p>'}${link}</details>${p.answers?.length?`<details class="evidence"><summary>Recorded replies (${p.answers.length})</summary>${p.answers.slice().reverse().map(a=>`<p><strong>${esc(a.key)} · ${esc(a.result)}</strong> — ${esc(a.answer)}<br><small>${esc(a.checked_on)} · ${esc(a.source)} · user-entered</small></p>`).join('')}<p class="hint">Replies older than 30 days or for another plan/service/language need reconfirmation.</p></details>`:''}<div class="card-actions">${S.current.contact?.provider_id===p.id?'<span class="chosen-tag">✓ 已选择 / Chosen</span>':['booked','attended'].includes(S.current.status)?'':`<button class="primary small" data-choose="${esc(p.id)}">选这家 / Choose this clinic</button>`}<button class="text-button" data-answer="${p.id}">Record office reply</button><button class="primary small" data-prepare="${p.id}">Prepare this visit ${icon('arrow')}</button><button class="text-button" data-quote="${p.id}">Add quote / confirmation</button></div></article>`;
}
function renderExpect(){
  trackPage();
  renderHeader();
  const x=S.expect, d=x.data, ill=d.illustration;
  const status=x.status==='searching'?`<div class="expect-status">${icon('pin')}<div><strong>Finding places near you…</strong><span>While that runs, here’s what to expect.</span></div></div>`
    :x.status==='ready'?`<div class="expect-status ready">${icon('check')}<div><strong>${x.found?`${x.found} ${x.found===1?'place':'places'} found`:'Search finished'}</strong><span>${x.found?'Ready when you are.':'No places came back. The guidance below still applies.'}</span></div><button type="button" class="primary" data-action="see-places">${x.found?'See places':'Continue'} ${icon('arrow')}</button></div>`
    :`<div class="expect-status error"><div><strong>The search didn’t finish</strong><span>${esc(x.error||'')}</span></div><button type="button" class="secondary" data-action="home">Start again</button></div>`;
  $('#app').innerHTML=`<div class="results-page expect-page">${S.input.scenario==='neu_student'?'<div class="notice">DEFAULT STUDENT INSURANCE SCENARIO · Northeastern / Brookline 02445. Review this illustrative person and confirm your exact current-year plan; benefits and enrollment are not pre-confirmed.</div>':''}${S.input.demo?'<div class="demo-banner">FICTIONAL DEMO · These are not actual care recommendations or insurance offers.</div>':''}
  <p class="eyebrow">WHAT TO EXPECT</p><h1 class="expect-title">${esc(d.headline)}</h1>${status}
  <div class="expect-grid">
    <section class="form-card"><div class="form-card-head"><h3>Where you could go</h3><p>In the order we’d suggest.</p></div>
      ${d.options.map((o,i)=>`<div class="venue"><span class="venue-n">${i+1}</span><div><strong>${esc(o.name)}</strong><p>${esc(o.fits)}</p>${o.cost?`<p class="venue-cost">${esc(o.cost)} <a href="${esc(o.source.url)}" target="_blank" rel="noopener noreferrer">Source</a></p>`:''}</div></div>`).join('')}
    </section>
    ${ill?`<section class="form-card"><div class="form-card-head"><h3>What you might pay</h3><p>${esc(ill.label)}</p></div>
      ${ill.rows.map(r=>`<div class="pay-row"><div><strong>${esc(r.venue)}</strong><span>Example fee ${dollars(r.example_fee)}</span></div><div class="pay-you"><small>You pay</small><strong>${r.you_pay==null?'Depends':dollars(r.you_pay)}</strong></div><p>${esc(r.how)}</p></div>`).join('')}
      <p class="hint"><a href="${esc(ill.source.url)}" target="_blank" rel="noopener noreferrer">${esc(ill.source.title)}</a> · checked ${esc(ill.source.checked_on)}</p></section>`:''}
    <section class="form-card"><div class="form-card-head"><h3>Before you go</h3></div><ul class="tips">${d.tips.map(t=>`<li>${icon('check')}<span>${esc(t)}</span></li>`).join('')}</ul></section>
  </div>
  <p class="computed">${icon('lock')} ${esc(d.computed)} ${d.sources.map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>`).join(' · ')}</p></div>`;
}
const srcLink=x=>x?` <a class="src" href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)}</a>`:'';
function scenarioPanel(sc){
  if(!sc) return '';
  const tip=t=>`<div class="choice-tip"><strong>${esc(t.title)}</strong><p>${esc(t.why)}${srcLink(t.source)}</p></div>`;
  const copyList=(id,items)=>`<ol class="script" id="${id}">${items.map(x=>`<li>${esc(x)}</li>`).join('')}</ol><button type="button" class="text-button" data-copy="${id}">Copy</button>`;
  if(sc.kind==='insured') return `<section class="scenario insured"><p class="eyebrow">YOU HAVE INSURANCE</p><h2>${esc(sc.title)}</h2><p class="lede">${esc(sc.lede)}</p>
    <div class="scenario-grid"><div class="form-card"><div class="form-card-head"><h3>What we know</h3></div>${sc.known.map(k=>`<div class="fact-list"><span>${esc(k.label)}</span><div>${esc(k.value)}</div></div>`).join('')}</div>
    <div class="form-card"><div class="form-card-head"><h3>Confirm before you go</h3><p>Call the number on your insurance card, or ask the clinic.</p></div>${copyList('ask-list',sc.ask)}</div>
    <div class="form-card"><div class="form-card-head"><h3>Use your plan well</h3></div>${sc.tips.map(tip).join('')}</div></div></section>`;
  return `<section class="scenario uninsured"><p class="eyebrow">${sc.kind==='choosing'?'NO INSURANCE · CHOOSING A PLAN':'NO INSURANCE'}</p><h2>${esc(sc.title)}</h2><p class="lede">${esc(sc.lede)}</p>
    <div class="first-check">${icon('shield')}<div><strong>${esc(sc.first.title)}</strong><p>${esc(sc.first.why)}${srcLink(sc.first.source)}</p></div></div>
    ${sc.compare?`<div class="compare-cta"><div><strong>Compare plans on the care you need</strong><p>See a yearly total for each plan, using your own numbers.</p></div><button type="button" class="primary" data-action="plans">Compare plans ${icon('arrow')}</button></div>`:''}
    <div class="scenario-grid"><div class="form-card"><div class="form-card-head"><h3>Help you can ask for</h3></div>${sc.resources.map(tip).join('')}</div>
    <div class="form-card"><div class="form-card-head"><h3>What to say</h3><p>When you call or check in.</p></div>${copyList('script-list',sc.scripts)}</div></div></section>`;
}
function renderPlans(){
  const P=S.plans, keys=Object.keys(P.catalog);
  const needRow=k=>`<div class="need-row ${P.needs[k]?'on':''}"><button type="button" class="need-toggle" data-plan-need="${k}" aria-pressed="${!!P.needs[k]}"><span class="todo-check">${P.needs[k]?icon('check'):''}</span>${esc(P.catalog[k])}</button>${P.needs[k]?`<input class="count" type="number" min="1" max="365" step="1" name="need_${k}" value="${P.needs[k]}" aria-label="${esc(P.catalog[k])} per year"><small>per year</small>`:''}</div>`;
  const chosen=keys.filter(k=>P.needs[k]);
  const planCard=(pl,i)=>`<section class="form-card plan-card"><div class="form-card-head row"><h3>Plan ${i+1}</h3>${P.plans.length>1?`<button type="button" class="text-button" data-remove-plan="${i}">Remove</button>`:''}</div>
    <div class="form-grid three">${field('Plan name',`p${i}_name`,pl.name,'text','maxlength="120" placeholder="From the plan list"')}${field('Monthly premium ($)',`p${i}_premium`,pl.premium??'','number','min="0" step="0.01"')}${field('Out-of-pocket max ($)',`p${i}_oop`,pl.oop_max??'','number','min="0" step="0.01"')}</div>
    ${chosen.length?`<div class="sub-card"><p class="sub-title">What you’d pay each time</p>${chosen.map(k=>{const c=pl.costs[k]||{status:'unknown',cost:''};return `<div class="cost-row"><span>${esc(P.catalog[k])}</span><select name="p${i}_${k}_status" aria-label="${esc(P.catalog[k])} coverage"><option value="covered" ${c.status==='covered'?'selected':''}>Covered</option><option value="not_covered" ${c.status==='not_covered'?'selected':''}>Not covered</option><option value="unknown" ${c.status==='unknown'?'selected':''}>Don’t know yet</option></select><input type="number" min="0" step="0.01" name="p${i}_${k}_cost" value="${esc(c.cost??'')}" placeholder="$ each" aria-label="${esc(P.catalog[k])} cost each"></div>`;}).join('')}</div>`:''}</section>`;
  const R=P.result;
  $('#app').innerHTML=`<div class="home"><form id="plans-form"><p class="eyebrow">CHOOSING A PLAN</p><h1 class="home-title">Compare plans on what you need.</h1><p class="lede">Pick the care you expect this year. We pre-filled a guess from your health profile. Copy each plan’s numbers from its official summary.</p>
    ${card('The care you expect this year','',`<div class="need-list">${keys.map(needRow).join('')}</div>`)}
    ${P.plans.map(planCard).join('')}
    ${P.plans.length<3?'<button type="button" class="secondary small" data-action="add-plan">+ Add another plan</button>':''}
    ${R?`<section class="form-card result-card"><div class="form-card-head"><h3>Your yearly estimate</h3><p>${esc(R.note)}</p></div><div class="plan-results">${R.plans.map(pl=>`<div class="plan-result ${R.best===pl.name?'best':''}"><div class="pr-head"><strong>${esc(pl.name)}</strong>${R.best===pl.name?'<span class="tag">Lowest known total</span>':''}</div><div class="pr-total">${pl.year_total==null?'Add the premium':dollars(pl.year_total)}<small>${pl.year_total==null?'':' per year'}</small></div><p>${pl.premium_year==null?'Premium unknown':`${dollars(pl.premium_year)} premiums`} + ${dollars(pl.care_total)} care${pl.capped?' (capped at your out-of-pocket max)':''}</p>${pl.not_covered.length?`<p class="warn">Not covered: ${pl.not_covered.map(esc).join(', ')}</p>`:''}${pl.unknown.length?`<p class="warn soft">Still unknown: ${pl.unknown.map(esc).join(', ')}</p>`:''}</div>`).join('')}</div><p class="hint">${R.sources.map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.title)}</a>`).join(' · ')}</p></section>`:''}
    <div class="form-actions"><button type="button" class="text-button" data-action="page-back">← 返回 / Back</button><button type="submit" class="primary">Calculate ${icon('arrow')}</button></div></form></div>`;
  $('#plans-form').addEventListener('submit',e=>{e.preventDefault();calcPlans();});
}
function readPlans(){
  const f=$('#plans-form'); if(!f) return; const g=n=>f.elements[n]?.value??'';
  Object.keys(S.plans.needs).forEach(k=>{if(f.elements[`need_${k}`])S.plans.needs[k]=Number(g(`need_${k}`))||1;});
  S.plans.plans=S.plans.plans.map((pl,i)=>{const costs={...pl.costs};Object.keys(S.plans.needs).forEach(k=>{if(f.elements[`p${i}_${k}_status`])costs[k]={status:g(`p${i}_${k}_status`),cost:g(`p${i}_${k}_cost`)};});return {name:g(`p${i}_name`),premium:g(`p${i}_premium`),oop_max:g(`p${i}_oop`),costs};});
}
async function openPlans(){
  const d=await api('/api/plans'), saved=d.saved;
  S.plans={catalog:d.needs,needs:saved?.needs||d.suggested,plans:saved?.plans?.length?saved.plans:[{name:'',premium:'',oop_max:'',costs:{}},{name:'',premium:'',oop_max:'',costs:{}}],result:d.result};
  S.view='plans'; render(); window.scrollTo(0,0);
}
async function calcPlans(){
  readPlans();
  await work(async()=>{const r=await api('/api/plans/compare',{needs:S.plans.needs,plans:S.plans.plans});S.plans.result=r.result;renderPlans();$('.result-card')?.scrollIntoView({behavior:'smooth',block:'start'});});
}
function sourceCard(x){
  return `<section class="source-card"><div class="source-main"><p class="eyebrow">${x.in_network_filter?'PLAN FILTER · CONFIRM WITH INSURER':'FIND REAL PROVIDERS'}</p><h3>See matching providers on ${esc(x.source)}</h3><p>${esc(x.note)}</p>
    <a class="primary" href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">Open ${esc(x.source)} results ${icon('arrow')}</a></div>
    <div class="source-shares"><strong>${icon('lock')} What ${esc(x.source)} will see</strong><ul>${x.shares.map(t=>`<li>${esc(t)}</li>`).join('')}</ul><p>${esc(x.how)} Search IDs checked ${esc(x.checked_on)}.</p></div></section>`;
}
function studentPlanReference(r){
  if(!r)return '';
  return `<section class="form-card"><div class="form-card-head"><h3>${esc(r.title)}</h3><p>Official public references · checked ${esc(r.checked_on)}</p></div>
    <p><strong>Published annual period:</strong> ${esc(r.period.start)} to ${esc(r.period.end)}. <strong>Student annual fee:</strong> ${dollars(r.annual_student_fee)}. This is an annual charge, not a monthly premium or your personal bill.</p>
    <p><strong>Carrier:</strong> ${esc(r.carrier)}</p><p>${esc(r.benefit_status)}</p>
    <details><summary>Published benefit leads to confirm</summary><p>${esc(r.published_highlights)}</p></details>
    <h3>Check this exact provider’s network</h3><p>${esc(r.network_status)}</p><p>${esc(r.network_guidance)}</p>
    <ol>${r.steps.map(t=>`<li>${esc(t)}</li>`).join('')}</ol>
    <p>${r.links.map(l=>`<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.title)} ↗</a>`).join(' · ')}</p>
    <p>${esc(r.contact)}</p><p class="hint">${esc(r.member_status)} ${esc(r.external_handoff)}</p></section>`;
}
const PRIORITY_LABELS={balanced:'适合我 / My fit',cost:'优先费用 / Cost first',rating:'优先评价 / Patient ratings',distance:'优先距离 / Distance first'};
function personalizedContext(c) {
  const p=c.input;
  const why={balanced:'先看接诊状态、服务依据和预算，再比较语言匹配与费用。 / Availability, service evidence and budget first; then language fit and cost.',cost:'按有依据的个人费用比较；未知费用不能当成便宜。 / Compare supported personal costs; unknown is not cheap.',rating:'使用有来源的患者评价；它不等于医疗质量。 / Sourced patient experience, not clinical quality.',distance:'只比较已知坐标的直线距离；不是通勤时间。 / Known straight-line distance, not travel time.'};
  const items=[['本次需求 / Care',p.need==='refill'?'Prescription refill':p.need==='checkup'?'Checkup / preventive visit':serviceName(p.service)],['语言支持 / Language',p.language],['预算 / Visit budget',p.budget==null?'未设置 / Not set':dollars(p.budget)],['支付方式 / Payment',p.insurance==='yes'?(p.plan?.name||'Insured · exact plan to confirm'):'自费 / Self-pay'],['时间与地点 / When & where',`${p.visit_date} · ${p.zip||p.city}, ${p.state}`]];
  return `<section class="personalized-context" aria-labelledby="your-priorities"><div class="context-heading"><div><p class="eyebrow">根据你这次的需求 / YOUR CARE PREFERENCES</p><h2 id="your-priorities">你的偏好 / Your priorities</h2></div><button type="button" class="secondary small" data-action="edit-preferences">修改偏好 / Edit preferences</button></div><dl class="preference-facts">${items.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl><p class="ranking-explanation"><strong>${esc(PRIORITY_LABELS[p.priority])}：</strong>${esc(why[p.priority])}</p><p class="hint">只比较当前找到的选项；待确认信息不会被当作已满足。 / Only the options found, with missing evidence kept explicit.</p></section>`;
}
// Stage 4: one chosen clinic, one checklist. Ticks come from saved data, never from clicks alone.
function contactChecklist(c,row){
  const p=row.provider,id=p.id,booked=['booked','attended'].includes(c.status);
  const zh=I18n.locale==='zh',L=(a,b)=>zh?a:b;
  const items=[
    {done:c.preparation?.provider_id===id,label:L('准备电话脚本','Prepare your call script'),act:`<button type="button" class="secondary small" data-prepare="${esc(id)}">${booked?L('就诊准备','Visit preparation'):L('打开脚本','Open script')}</button>`},
    {done:(p.answers||[]).length>0,label:L('打电话，记录诊所的答复','Call and record what the office said'),act:booked?'':`<button type="button" class="secondary small" data-answer="${esc(id)}">${L('记录答复','Record reply')}</button>`},
    {done:!!p.confirmation_source,label:L('记录报价或保险确认','Record a price or coverage answer'),act:booked?'':`<button type="button" class="secondary small" data-quote="${esc(id)}">${L('记录报价','Add quote')}</button>`},
    {done:null,label:L('查看路线','Get directions'),act:directionsLink(p)},
    {done:booked,label:L('预约，然后在这里标记','Book, then mark it here'),act:`${bookingLink(p)}${booked?'':`<button type="button" class="primary small" data-action="mark-booked">${L('我已预约','I booked it')}</button>`}`}
  ];
  const left=items.filter(i=>i.done===false).length;
  return `<section class="next-step-panel contact-checklist" aria-labelledby="checklist-title"><p class="eyebrow">${L('联系与确认','CONTACT & CONFIRM')}</p><h2 id="checklist-title" data-i18n-keep>${esc(p.name)}</h2><p class="hint" data-i18n-keep>${esc(p.address||'')}${left?` · ${L(`还有 ${left} 项`,`${left} left`)}`:''}</p><ul class="checklist">${items.map(i=>`<li class="${i.done?'done':''}"><span class="check" aria-hidden="true">${i.done?'✓':i.done===null?'·':''}</span><span class="label" data-i18n-keep>${esc(i.label)}</span><span class="act">${i.act}</span></li>`).join('')}</ul>${booked?`<button type="button" class="primary" data-action="record-visit">${L('就诊后：记录这次就诊','After the visit: record it')}</button>`:''}<p class="hint">${booked?L('预约状态来自你保存的记录。要更改，请用「更新预约状态」。','Booked status comes from what you saved. To change it, use “Update appointment status”.'):`${L('选择一家只代表你打算先联系它，不代表已联系或已预约。','Choosing a clinic only means you plan to contact it first; it is not a booking.')} <button type="button" class="text-button" data-action="unchoose">${L('换一家','Choose another')}</button>`}</p></section>`;
}
function nextStepPanel(c) {
  const chosenRow=c.contact?.provider_id&&c.status!=='attended'&&c.results.find(r=>r.provider.id===c.contact.provider_id);
  if(chosenRow)return contactChecklist(c,chosenRow);
  const complete=c.status==='attended', booked=c.status==='booked';
  const row=c.results.find(r=>booked?r.provider.id===c.contact?.provider_id:!r.unavailable);
  const action=complete?'<button type="button" class="primary" data-action="home-page">查看后续待办 / View follow-ups</button>':row?`<button type="button" class="primary" data-prepare="${esc(row.provider.id)}">${booked?'查看就诊准备 / Visit preparation':'准备联系这家 / Prepare to contact'}</button>${!booked?`<button type="button" class="secondary" data-answer="${esc(row.provider.id)}">记录诊所答复 / Record office reply</button>`:''}`:'<button type="button" class="primary" data-action="add-candidate">添加其他诊所 / Add another clinic</button>';
  return `<section class="next-step-panel" aria-labelledby="next-step-title"><div><p class="eyebrow">继续推进这件事 / YOUR NEXT STEP</p><h2 id="next-step-title">${complete?'继续后续照护 / Follow through after your visit':booked?'准备就诊 / Prepare for your appointment':row?`先联系这家 / Start here: ${esc(row.provider.name)}`:'找另一个选项 / Find another option'}</h2><p>${esc(row||complete?c.next_action:'当前没有可继续联系的候选。保留现有记录，并添加另一家诊所。 / No clinic is ready to contact right now. Your records are kept; add another clinic.')}</p>${!booked&&!complete&&row?'<p class="hint">这是下一步联系对象，不代表费用、保险或预约已经确认。 / A next contact, not a verified appointment or coverage recommendation.</p>':''}</div><div class="next-step-actions">${action}<button type="button" class="text-button" data-action="agent">让本地助手帮我梳理 / Ask the local assistant</button></div></section>`;
}
function preferencesDialog() {
  const c=S.current,p=c.input;
  openDialog('调整这次就医的偏好 / Your care preferences',`<p>更新后立即重新排列当前候选，已有答复和报价保留。 / Reorders this shortlist while keeping its evidence.</p><form id="preferences-form">${select('优先考虑 / Put first','priority',Object.entries(PRIORITY_LABELS),p.priority)}<div class="form-grid">${select('需要的语言支持 / Care language','language',[['English','English'],['Chinese','中文 / Chinese'],['Spanish','Español / Spanish']],p.language)}${field('本次预算 / Visit budget ($, optional)','budget',p.budget,'number','min="0" step="0.01"')}</div><p class="hint">修改语言后，其他语言的答复不会自动算作确认。 / Replies about another language do not confirm this preference.</p><button type="submit" class="primary">保存并更新选项 / Update my options</button></form>`,true);
  $('#preferences-form').addEventListener('submit',event=>{event.preventDefault();const values=Object.fromEntries(new FormData(event.target));work(async()=>{S.current=await api('/api/case/preferences',{id:c.id,...values});closeDialog();render();toast('偏好已更新，候选已重新排序。 / Preferences saved; shortlist updated.');});});
}

function renderResults() {
  const c=S.current,p=c.input,known=c.results.filter(r=>r.supported&&r.cost.amount!=null&&!r.unavailable),min=known.length?Math.min(...known.map(r=>r.cost.amount)):null;
  $('#app').innerHTML=`<div class="results-page">${taskShell()}${p.scenario==='neu_student'?'<div class="notice">STUDENT INSURANCE SCENARIO · NEU / Brookline 02445. Illustrative person, real provider sources. NUSHP product, plan year, enrollment, prices and exact network need confirmation. <a href="https://studenthealthplan.northeastern.edu/" target="_blank" rel="noopener noreferrer">Check NUSHP documents ↗</a></div>':''}${p.demo?'<div class="demo-banner">FICTIONAL DEMO · These are not actual care recommendations or insurance offers.</div>':''}<div class="results-heading"><div><p class="eyebrow">YOUR NEXT STEP, A LITTLE CLEARER</p><h1><em>Your care plan.</em></h1><p><button class="text-button" data-action="explain-ranking">解释这个排序 / Explain this ranking</button></p><div id="ranking-explain" class="soft-note" aria-live="polite" hidden></div><p>${esc(p.city)}, ${esc(p.state)} <span class="dot">·</span> ${serviceName(p.service)} <span class="dot">·</span> ${esc(p.visit_date)}</p></div><div class="dialog-actions"><button class="primary" data-action="agent">本地助手 / Local assistant</button><button class="secondary" data-action="new">新建任务 / New task ${icon('arrow')}</button></div></div><div class="result-metrics"><div><span>OPTIONS FOUND</span><strong>${c.results.length}<small> in your shortlist</small></strong></div><div><span>LOWEST SUPPORTED COST</span><strong>${dollars(min)}<small>${known.length?' for this visit':' · confirm quotes first'}</small></strong></div><div><span>YOUR HEALTH PROFILE</span><strong>${icon('lock')} Stays local</strong></div></div>${c.goal?`<section class="task-context"><strong>这次的目标 / Your goal</strong><p>${esc(c.goal)}</p><button class="text-button" data-action="task-details">任务与资料 / Task & reports (${(c.report_ids||[]).length})</button></section>`:''}${personalizedContext(c)}${nextStepPanel(c)}<details class="supporting-guidance"><summary>需要时再看：保险说明与其他查找入口 / Insurance guidance & other ways to find care</summary>${studentPlanReference(c.plan_reference)}${scenarioPanel(c.scenario)}${(c.sources||[]).map(sourceCard).join('')}</details>${c.errors.length?`<div class="notice">Live discovery had a problem: ${c.errors.map(esc).join('; ')}. Available local results remain below.</div>`:''}<div class="results-layout"><section><div class="results-toolbar"><div><h2>按你的条件比较 / Your shortlist</h2>${!p.demo?'<button class="secondary small" data-action="add-candidate">Add a provider you found</button>':''}<p>Ordered by your preferences, among the options found.</p></div>${select('Sort by','result_priority',[['balanced','My fit'],['cost','Lowest cost'],['rating','Patient rating'],['distance','Distance']],p.priority)}</div>${c.results.length?['<h3>Supported cost comparisons</h3>',...(known.length?known.map((r,i)=>providerCard(r,i)):['<p class="hint">No supported visit prices yet. Confirm the evidence below before comparing costs.</p>']),'<h3>Options needing confirmation</h3>',...c.results.filter(r=>!known.includes(r)).map((r,i)=>providerCard(r,i))].join(''):'<div class="empty"><h3>No local providers found here yet.</h3><p>Live discovery is not connected. You can use the official health-center finder below; this shortlist will not substitute providers from another city.</p><a href="https://findahealthcenter.hrsa.gov/" target="_blank" rel="noopener noreferrer">Find a community health center ↗</a></div>'}</section><aside class="results-aside"><div class="aside-panel"><span class="aside-icon">${icon('shield')}</span><h3>${p.insurance==='yes'?'Make your benefits work for you.':'Would insurance change the picture?'}</h3><p>Compare the same visit, then include what the plan itself costs.</p>${p.plan?`<div class="plan-chip"><span>PLAN SCENARIO</span><strong>${esc(p.plan.name)}</strong><small>${p.plan.start?'Starts '+esc(p.plan.start):'Start date unconfirmed'} · ${p.plan.eligible?'Eligibility entered as confirmed':'Eligibility unconfirmed'}</small></div>`:'<p class="hint">No plan entered. Add a quote to calculate a scenario; unknown prices stay unknown.</p>'}<button class="primary full" data-action="plan">${p.plan?'Edit plan comparison':'Compare an insurance plan'} ${icon('arrow')}</button><p class="hint">Potential savings depend on eligibility, coverage dates, exact network and benefit rules. A lower visit copay does not always mean a lower total.</p><a href="${p.state==='MA'?'https://betterhealthconnector.com/get-started/individuals-families':'https://www.healthcare.gov/see-plans/'}" target="_blank" rel="noopener noreferrer" class="text-button">Explore official coverage options ↗</a></div><div class="aside-panel quiet"><h3>What we know. What we don’t.</h3><p>${p.demo?'This sample illustrates the complete comparison with fictional data.':c.live_searched?'Live discovery adds leads to a small sourced directory. Search matches still need provider confirmation.':'This is a small sourced directory, not an exhaustive search.'}</p><p>Appointments, exact networks and complete charges need confirmation. Unknown price never means free.</p><a href="https://www.healthcare.gov/choose-a-plan/your-total-costs/" target="_blank" rel="noopener noreferrer">How health costs work ↗</a></div><div class="aside-panel quiet"><h3>Your ongoing care journey</h3><p>Status: <strong>${esc(c.status)}</strong></p><p class="hint">A booking link does not confirm an appointment. Record the outcome after contacting the provider.</p><button class="text-button" data-action="contact">Update appointment status →</button><button class="secondary small record-visit" data-action="record-visit">I went · record the visit ${icon('arrow')}</button></div></aside></div></div>`;
  $('[name="result_priority"]').addEventListener('change',event=>work(async()=>{S.current=await api('/api/case/preferences',{id:c.id,priority:event.target.value});render();}));
}

const AGENT_KEYS={language:'中文等语言 / Language or interpreter support',availability:'接收新病人或有合适预约 / Suitable new-patient appointment',referral:'需要转诊或授权 / Referral required',referral_action:'已取得转诊或授权 / Referral obtained'};
function agentDialog(status, result=null, input={}) {
  const c=S.current;
  let output='';
  if(result){
    output=`<p role="status">${esc(result.text)}</p>`;
    if(result.state==='read')output+=`<p><strong>下一步 / Next:</strong> ${esc(result.next_action)}</p>${result.rows.map(r=>`<section class="sub-card"><h3>${esc(r.name)}</h3><p>${esc(r.address)}</p><p>${r.unavailable?'备选：目前没有合适预约 / Backup: no suitable appointment':''}</p><p><strong>${dollars(r.cost.amount)}</strong> · ${esc(r.pathway)}</p><p>${esc(r.cost.reason)}</p>${r.cost.source?`<p>${esc(r.cost.source)} · ${esc(r.cost.checked_on)}</p>`:''}${r.cost.breakdown.map(b=>`<p>${esc(b.label)}: ${dollars(b.amount)}</p>`).join('')}<ul>${(result.tool==='costs'?r.questions.map(q=>q.question):r.reasons).map(t=>`<li>${esc(t)}</li>`).join('')}</ul></section>`).join('')}`;
    if(result.state==='proposal')output+=`<form id="agent-confirm"><div class="soft-note"><strong>${esc(result.provider.name)}</strong><br>${esc(result.provider.address)}<br><span>语言 / Language</span>: <span data-i18n-keep>${esc(result.scope.language)}</span> · <span>${esc(serviceName(result.scope.service))}</span><br>请逐条核对；结果可修正。不勾选的项目不会保存。 / Review each fact; uncheck to omit.</div>${result.replies.map(r=>`<section class="sub-card"><label class="checkline"><input type="checkbox" name="keep_${r.key}" checked><span>${esc(r.key==='language'?result.scope.language+' 语言或翻译支持 / Language support':AGENT_KEYS[r.key])}</span></label><blockquote>${esc(r.evidence)}</blockquote>${select('核对结果 / Reviewed result','result_'+r.key,[['yes','是 / Yes'],['no','否 / No'],['unknown','未知 / Unknown']],r.result)}</section>`).join('')}${field('实际来源或联系人 / Actual source or person','source','','text','required maxlength="500"')}${field('实际确认日期 / Date actually checked','checked_on','','date',`required max="${today()}"`)}<p class="hint">这是用户记录，不是独立验证，也不代表预约成功。草稿 10 分钟后失效。 / User-reported evidence, not an independent verification or booking. Draft expires in 10 minutes.</p><button class="primary">确认并保存 / Confirm and save</button></form>`;
  }
  openDialog('本地就医任务助手 / Local care assistant',`<p>只处理当前任务与诊所答复；不评估症状。文字仅发往本机 Ollama。对话不保存；只有你确认的事实进入加密档案。 / Care tasks and office replies only. Text goes to local Ollama; only confirmed facts are saved.</p><p class="hint">${status.available?`本地模型 / Local model: ${esc(status.model)}`:`本地模型未就绪 / Local model not ready: ${esc(status.model)}. ${esc(status.reason)}. Read tools still work.`}</p><div class="dialog-actions"><button class="secondary" id="agent-overview">查看任务 / View task</button><button class="secondary" id="agent-costs">查看费用 / View costs</button><button class="text-button" data-action="agent">重新检查模型 / Recheck model</button></div><form id="agent-turn">${select('先选择答复对应的诊所 / Clinic for this reply','provider_id',[['','请选择 / Select a clinic'],...c.providers.map(p=>[p.id,p.name+' · '+p.address])],input.provider_id||'')}<label class="field"><span>诊所怎么说？也可以问下一步或费用。 / Office reply or task question</span><textarea name="message" rows="3" maxlength="3000" required placeholder="这家诊所有中文翻译，但目前不收新病人。">${esc(input.message||'')}</textarea></label><button class="primary" ${status.available?'':'disabled'}>整理并预览 / Interpret and preview</button><p id="agent-working" role="status"></p></form><div class="agent-output" aria-live="polite">${output}</div>`,true);
  const read=tool=>work(async()=>{const r=await api('/api/agent/turn',{id:c.id,tool});agentDialog(status,r,{provider_id:$('#agent-turn').elements.provider_id.value,message:$('#agent-turn').elements.message.value});});
  $('#agent-overview').addEventListener('click',()=>read('overview'));
  $('#agent-costs').addEventListener('click',()=>read('costs'));
  $('#agent-turn').addEventListener('submit',e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));work(async()=>{$('#agent-working').textContent='正在本机处理… / Working locally…';try{const r=await api('/api/agent/turn',{id:c.id,...data});agentDialog(status,r,data);}finally{if($('#agent-working'))$('#agent-working').textContent='';}});});
  if($('#agent-confirm'))$('#agent-confirm').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.target),results={};for(const r of result.replies)if(f.has('keep_'+r.key))results[r.key]=f.get('result_'+r.key);work(async()=>{const saved=await api('/api/agent/confirm',{id:c.id,token:result.token,confirmed:true,results,source:f.get('source'),checked_on:f.get('checked_on')});S.current=saved.case;closeDialog();render();toast(`已保存 ${saved.saved} 条答复并更新排序。 / Replies saved; shortlist updated.`);});});
}

function openDialog(title,html,wide=false) {
  const d=$('#dialog'); d.innerHTML=`<div class="dialog-head"><h2 id="dialog-title">${title}</h2><button type="button" class="text-button dialog-back" data-action="close" aria-label="Back to current page">← 返回 / Back</button></div>${html}`; d.className=wide?'wide':''; if(!d.open)d.showModal();
}
function closeDialog() {$('#dialog').close();$('#dialog').innerHTML='';}
function planDialog() {
  const p=S.current.input;
  openDialog('Compare a plan, including its cost',`<p class="lede">A scenario for the same visit at each provider. This is not an enrollment or eligibility decision.</p><form id="plan-form">${planResources()}${planFields(p.plan)}${field('Number of premium payments to include','months',p.months,'number','required min="1" max="12" step="1"')}<p class="hint">For example, 12 includes a year of premiums but still only this one visit. This is not a complete annual healthcare forecast.</p><button class="primary" type="submit">Update comparison ${icon('arrow')}</button></form>`,true);
  $('#plan-form').addEventListener('submit',e=>{e.preventDefault();const plan=readPlan(e.target),months=e.target.elements.months.value;work(async()=>{S.current=await api('/api/case/preferences',{id:S.current.id,plan,months});closeDialog();render();toast('Comparison updated locally. Confirm each provider’s exact-plan participation.');});});
}
function candidateDialog(){
  openDialog('Add a provider you found',`<p>Bring back a candidate from Zocdoc, the insurer directory or an official clinic page. Nothing is fetched or sent by this form.</p><form id="candidate-form">${field('Provider / practice name','name','','text','required maxlength="150"')}${field('Exact appointment address','address','','text','required maxlength="300"')}${field('Public source URL','url','','url','required placeholder="https://…"')}${field('Phone (optional)','phone','','tel','maxlength="50"')}${field('Source description','source','','text','required maxlength="500" placeholder="Official directory or clinic page; what did you verify?"')}${field('Date checked','checked_on',today(),'date',`required max="${today()}"`)}<p class="hint">A directory listing is a lead, not a confirmed network, price or appointment. Add those confirmations separately.</p><button type="submit" class="primary">Save candidate</button></form>`,true);
  $('#candidate-form').addEventListener('submit',e=>{e.preventDefault();const b=Object.fromEntries(new FormData(e.target));work(async()=>{S.current=await api('/api/case/candidate',{...b,id:S.current.id});S.state=await api('/api/state');closeDialog();render();toast('Candidate saved locally. Confirm its service, network and price.');});});
}
function answerDialog(id){
  const p=S.current.providers.find(p=>p.id===id);
  openDialog('Record an office reply',`<p>${esc(p.name)} · ${esc(p.address)}</p><form id="answer-form">${select('Question','key',[['availability',S.current.input?.service==='follow_up'?'Appointment availability':'New-patient / appointment availability'],['language','Language / interpreter support'],['referral','Referral / prior authorization'],['referral_action','Required referral / authorization obtained']],'availability')}${select('Answer','result',[['unknown','Still unknown / needs follow-up'],['yes','Yes'],['no','No']],'unknown')}<label class="field"><span>What they said / next action</span><textarea name="answer" maxlength="1500" required rows="3"></textarea></label>${field('Source / person contacted','source','','text','required maxlength="500"')}${field('Date checked','checked_on',today(),'date',`required max="${today()}"`)}<p class="hint">For referral: Yes means required, No means not required. For referral obtained: Yes means you have the required confirmation. For availability: No means no suitable appointment. These are your records, not independently verified. Price, service and insurance network use Add quote / confirmation.</p><button class="primary">Save reply</button></form>`,true);
  $('#answer-form').addEventListener('submit',e=>{e.preventDefault();const b=Object.fromEntries(new FormData(e.target));work(async()=>{S.current=await api('/api/case/answer',{...b,id:S.current.id,provider_id:id});S.state=await api('/api/state');closeDialog();render();});});
}
function quoteDialog(id) {
  const row=S.current.results.find(r=>r.provider.id===id),p=row.provider,plan=S.current.input.plan;
  openDialog('Add a quote or confirmation',`<p>${esc(p.name)} · ${serviceName(S.current.input.service)}</p><form id="quote-form"><div class="form-grid">${field('Complete self-pay quote ($)','cash',p.cash.amount,'number','min="0" step="0.01"')}${field('Date you checked','checked_on',today(),'date',`required max="${today()}"`)}${field('Exact plan / network name','plan_name',plan?.name)}${field('Allowed amount for this service ($)','allowed_amount','','number','min="0" step="0.01"')}</div>${field('Source (person, quote reference, or URL)','source','','text','required placeholder="For example: billing office call, Nov 7" maxlength="500"')}<label class="checkline"><input type="checkbox" name="service_confirmed"><span>I confirmed this location offers this service for adult patients.</span></label><label class="checkline"><input type="checkbox" name="scope_confirmed"><span>I confirmed the quote covers the defined visit, including applicable facility/professional fees.</span></label><label class="checkline"><input type="checkbox" name="network_confirmed"><span>I confirmed this exact plan, provider, location and service are in-network.</span></label><details class="private-details"><summary>Add sourced patient reviews (optional)</summary><div class="form-grid">${field('Patient rating (0–5)','rating','','number','min="0" max="5" step="0.1"')}${field('Number of reviews','rating_count','','number','min="1" step="1"')}</div>${field('Rating source URL','rating_source','','url')}</details><p class="hint">Saved as user-entered evidence, not independently verified. Additional services are excluded from the visit comparison.</p><button type="submit" class="primary">Save & rerank ${icon('arrow')}</button></form>`,true);
  $('#quote-form').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.target),b=Object.fromEntries(f);['service_confirmed','scope_confirmed','network_confirmed'].forEach(k=>b[k]=f.has(k));work(async()=>{S.current=await api('/api/case/quote',{...b,id:S.current.id,provider_id:id});closeDialog();render();toast('Evidence saved. Your shortlist has been recalculated.');});});
}
function preparationDialog(id) {
  const p=S.current.results.find(r=>r.provider.id===id).provider;
  S.preparingProvider=id;
  openDialog('Make the next step easier',`<p class="lede">${esc(p.name)}</p><div class="soft-note">Review your script before sharing. Nothing is sent to the provider.</div><div id="prep-output" class="prep-output">Preparing your questions…</div><div class="dialog-actions"><button class="secondary" data-action="model-prep">Use my local model</button><button class="secondary" data-action="copy-prep">Copy script</button>${p.url?`<a class="primary" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">Open provider website ↗</a>`:''}</div><p class="hint">The provider website is a separate service with its own privacy practices. A visit is booked only after you receive confirmation.</p>`);
  work(async()=>{const result=await api('/api/case/preparation',{id:S.current.id,provider_id:S.preparingProvider,use_model:false});showPrep(result);});
}
function showPrep(result) {if($('#prep-output'))$('#prep-output').innerHTML=`<span class="source-label">${esc(result.source)} · review this draft</span>${result.fallback_reason?`<p class="hint">Your local model wasn't used (${esc(result.fallback_reason)}). To use it, start Ollama on this computer and run <code>ollama pull ${esc(S.state?.services?.ollama_model||'qwen3.5:2b')}</code>.</p>`:''}<pre id="script-text">${esc(result.text)}</pre>${result.personal_note?`<details class="private-details"><summary>给医生的个人材料 / Private clinician note</summary><p>不包含在预约脚本中；由你决定向谁分享。 / Separate from the booking script.</p><pre>${esc(result.personal_note_view?.[I18n.locale==='zh'?'zh':'en']||result.personal_note)}</pre></details>`:''}`;}
function contactDialog(preset={}) {
  const c=S.current,status=preset.status||c.status;
  openDialog('Keep track of your next step',`<form id="contact-form">${select('Status','status',[['comparing','Still comparing'],['contacted','Contacted a provider'],['booked','Appointment confirmed'],['attended','Visit completed']],status)}${select('Provider','provider_id',[['','Not selected'],...c.providers.map(p=>[p.id,p.name])],c.contact?.provider_id||'')}${field('Booking reference or how it was confirmed','reference',c.contact?.reference)}<label class="field"><span>Notes / next steps</span><textarea name="notes" rows="4" maxlength="3000">${esc(c.contact?.notes||'')}</textarea></label><button class="primary">Save to my care journey</button></form>`);
  $('#contact-form').addEventListener('submit',e=>{e.preventDefault();const b=Object.fromEntries(new FormData(e.target));work(async()=>{S.current=await api('/api/case/contact',{...b,id:c.id});closeDialog();render();});});
}
function unlockDialog(after) {
  openDialog(S.state.vault_exists?'Unlock your private vault':'Your care, saved privately',S.state.vault_exists?`<form id="unlock-form">${field('Passphrase','passphrase','','password','required minlength="8" autocomplete="current-password"')}<button class="primary">Unlock</button></form>`:'<p>Start your care search to create an encrypted local vault at the review step.</p><button class="primary" data-action="close">Continue</button>');
  if($('#unlock-form'))$('#unlock-form').addEventListener('submit',e=>{e.preventDefault();const passphrase=e.target.elements.passphrase.value;work(async()=>{S.state=await api('/api/vault/unlock',{passphrase});closeDialog();renderHeader();if(after)await after();});});
}
const CASE_STATUS={planning:'Planning',comparing:'Comparing options',contacted:'Contacted',booked:'Booked',attended:'Visit recorded'};
// Saved task label: the user's chosen starting point (current names), plus the searched service when the task has a shortlist.
function caseLabel(c){const kind=c.kind&&JOURNEY_KINDS[c.kind];return kind&&kind!==c.service?`<span>${esc(kind)}</span> · <span>${esc(c.service)}</span>`:`<span>${esc(c.service)}</span>`;}
async function savedDialog() {
  if(!S.state.unlocked)return unlockDialog(savedDialog);
  S.state=await api('/api/state');
  openDialog('My care journeys',S.state.cases.length?`<div class="saved-list">${S.state.cases.map(c=>`<button data-case="${esc(c.id)}"><span>${caseLabel(c)}${c.demo?' · <span>Fictional demo</span>':''}<small>${c.city?`<span data-i18n-keep>${esc(c.city)}</span> · `:''}${new Date(c.created*1000).toLocaleDateString()}</small></span><span>${esc(CASE_STATUS[c.status]||c.status)} →</span></button>`).join('')}</div>`:'<p>Your saved searches and appointment steps will appear here.</p>');
}
async function privacyDialog() {
  if(!S.state.unlocked)return unlockDialog(privacyDialog);
  const data=await api('/api/privacy');
  openDialog('Your privacy, in view',`<p>Confirmed records are encrypted in your local vault. Optional browser-service dictation may send audio and its content outside this app; retention, training and deletion are controlled by the provider, not FirstVisit. These browser requests are outside this gateway ledger. Dictation never submits automatically. ${S.browserVoiceUses||0} browser-service attempts explicitly enabled in this tab (count only, not a network observation).</p><div class="privacy-numbers"><div><strong>${data.attempted}</strong><span>External attempts</span></div><div><strong>${data.blocked}</strong><span>Requests blocked</span></div><div><strong>${data.local_calls}</strong><span>Local model calls</span></div></div><button class="secondary" data-action="offline">${S.state.offline?'Turn live discovery back on':'Turn on offline mode'}</button><button class="secondary" data-action="privacy-probe">Run synthetic privacy self-check</button><p class="hint">Uses a made-up protected phrase through the gateway preflight. No network call, no real patient data.</p><p class="hint">Failed requests may still reach a destination and count as external attempts. ${esc(data.scope)}</p><details><summary>Recent gateway activity</summary><pre class="ledger">${esc(JSON.stringify(data.ledger,null,2))}</pre></details>`,true);
}
document.addEventListener('click',event=>{
  const target=event.target.closest('button, [data-action]');if(!target||S.busy)return;
  if(target.dataset.uiLocale){I18n.setLocale(target.dataset.uiLocale);return;}
  if(dictation.rec&&target.dataset.action!=='dictate')dictation.abort();
  rememberPage();
  if(target.dataset.step!==undefined){const step=Number(target.dataset.step);if(S.view==='wizard'&&step>=0&&step<S.step&&S.step<4){collect();S.step=step;S.preview=null;render();window.scrollTo(0,0);}return;}
  if(target.dataset.group){collect();const t=target.dataset.group;S.open.has(t)?S.open.delete(t):S.open.add(t);render();return;}
  if(target.dataset.journeyKind){const form=$('#home-intent');if(form){form.elements.kind.value=target.dataset.journeyKind;S.homeKind=target.dataset.journeyKind;if($('#kind-guess'))$('#kind-guess').hidden=true;updateHomePrompt(S.homeKind);rememberPage();$('#home-goal').focus();}return;}
  if(target.dataset.forgetReport)return work(async()=>{await api('/api/reports/forget',{report_id:target.dataset.forgetReport});trail.clear();S.reportDraft=null;S.current=null;S.journey=await api('/api/journey?id='+encodeURIComponent(S.journey.id));render();});
  if(target.dataset.feel)return startVisit(target.dataset.feel);
  if(target.dataset.planNeed){readPlans();const k=target.dataset.planNeed;if(S.plans.needs[k])delete S.plans.needs[k];else S.plans.needs[k]=1;renderPlans();return;}
  if(target.dataset.removePlan){readPlans();S.plans.plans.splice(Number(target.dataset.removePlan),1);renderPlans();return;}
  if(target.dataset.copy){const t=$('#'+target.dataset.copy)?.innerText;return work(async()=>{await navigator.clipboard.writeText(t);toast('Copied.');});}
  if(target.dataset.pins){readDraft();S.draft.insurance=target.dataset.pins;renderProfile();return;}
  if(target.dataset.addRow){const visit=S.view==='visit';visit?readVisit():readDraft();const tgt=visit?S.visit:S.draft;(target.dataset.addRow==='med'?tgt.meds:tgt.fus).push(target.dataset.addRow==='med'?{name:'',refill_by:''}:{what:'',due:''});visit?renderVisit():renderProfile();return;}
  if(target.dataset.todo){const t=S.health.todos.find(x=>x.id===target.dataset.todo);return work(async()=>{S.health=await api('/api/profile/todo',{id:t.id,done:!t.done_on});render();});}
  if(target.dataset.forget){const f=target.dataset.forget;if(f==='everything'&&!confirm('Forget your whole profile and all saved care journeys? This can’t be undone.'))return;return work(async()=>{S.health=await api('/api/profile/forget',{field:f,value:target.dataset.value||''});trail.clear();S.state=await api('/api/state');if(f==='everything'){S.journey=null;S.reportDraft=null;S.homeGoal='';S.activeJourney=null;S.current=null;S.found=null;editProfile();return;}render();});}
  if(target.dataset.sign){S.input.no_signs=false;const id=target.dataset.sign;S.input.checks=S.input.checks.includes(id)?S.input.checks.filter(x=>x!==id):[...S.input.checks.filter(x=>S.choices.some(c=>c.id===x&&lvl(c)==='emergency')),id];
    return work(async()=>{S.safety=await api('/api/safety',{checks:S.input.checks});render();$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});});}
  if(target.dataset.none){S.input.no_signs=!S.input.no_signs;if(S.input.no_signs){S.input.checks=S.input.checks.filter(x=>!S.choices.some(c=>c.id===x&&lvl(c)==='emergency'));S.safety=null;}render();return;}
  if(target.dataset.chip){collect();if(S.input.service==='same_day')S.input.service='primary_care';const id=target.dataset.chip;S.input.checks=S.input.checks.includes(id)?S.input.checks.filter(x=>x!==id):[...S.input.checks,id];
    return work(async()=>{const r=await api('/api/safety',{checks:S.input.checks,description:S.input.description});S.safety=r.level==='emergency'?r:null;render();if(S.safety)$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});});}
  if(target.dataset.need){collect();const n=NEEDS.find(x=>x[0]===target.dataset.need);S.input.need=n[0];S.input.service=n[3];S.input.checks=n[2]?[n[2]]:[];render();return;}
  if(target.dataset.sub){collect();S.sub=target.dataset.sub;S.open=new Set();S.safety=null;if(S.sub==='start')S.input.checks=[];render();return;}
  if(target.dataset.insurance){collect();S.input.insurance=target.dataset.insurance;S.preview=null;render();return;}
  if(target.dataset.wants){collect();S.input.wants_insurance=target.dataset.wants==='yes';render();return;}
  if(target.dataset.answer)return answerDialog(target.dataset.answer);
  if(target.dataset.quote)return quoteDialog(target.dataset.quote);
  if(target.dataset.prepare)return preparationDialog(target.dataset.prepare);
  if(target.dataset.case)return openJourney(target.dataset.case);
  const action=target.dataset.action;
  if(action==='page-back'){
    if(trail.canGoBack){history.back();return;}
    if(S.view==='wizard'&&S.step>0&&S.step<4){collect();S.step--;S.preview=null;render();return;}
    S.view='home';S.expect=null;S.current=null;S.activeJourney=null;return work(async()=>{[S.health,S.state]=await Promise.all([api('/api/profile'),api('/api/state')]);render();window.scrollTo(0,0);});
  }
  if(action==='dictate')return startBrowserDictation();
  if(action==='journey-prep')return showPersonalPreparation();
  if(action==='task-details')return work(async()=>{S.journey=await api('/api/journey?id='+encodeURIComponent(S.current.id));S.current=null;S.view='journey';S.expect=null;render();window.scrollTo(0,0);});
  if(action==='copy-personal-prep')return work(async()=>{await navigator.clipboard.writeText(prepText());toast('已复制；由你决定分享对象。 / Copied for you to share.');});
  if(action==='journey-find'){S.editInsurance=false;if(S.journey.safety_notice?.level==='emergency')return toast('请先处理紧急警示 / Please address the emergency warning.');S.activeJourney=S.journey.id;S.input=fromProfile();S.input.description='';S.input.feel=['concern','general'].includes(S.journey.kind)?'unsure':'okay';S.input.need='';S.input.checks=[];if(['follow_up','report'].includes(S.journey.kind)){S.input.need='follow_up';S.input.service='follow_up';}if(S.journey.kind==='first_visit'){S.input.need='checkup';S.input.service='primary_care';S.input.checks=['checkup'];}if(!S.input.insurance&&['insured','uninsured','choosing'].includes(S.journey.coverage_situation)){S.input.insurance=S.journey.coverage_situation==='insured'?'yes':'no';S.input.wants_insurance=S.journey.coverage_situation==='choosing';}S.input.none_reported=!['concern','general'].includes(S.journey.kind);S.safety=null;S.current=null;S.expect=null;S.preview=null;S.step=0;S.sub=['concern','general'].includes(S.journey.kind)||S.journey.safety_notice?'symptoms':'need';if(S.journey.safety_notice){S.input.description=S.journey.goal;S.safety=S.journey.safety_notice;}S.view='wizard';render();window.scrollTo(0,0);return;}
  if(action==='edit-preferences')return preferencesDialog();

  if(action==='close')return closeDialog();
  if(action==='back'){collect();S.step--;S.preview=null;render();return;}
  if((action==='home'||action==='new')&&S.state.unlocked){S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.current=null;S.preview=null;S.view='home';return work(async()=>{[S.health,S.state]=await Promise.all([api('/api/profile'),api('/api/state')]);render();window.scrollTo(0,0);});}
  if(action==='home'||action==='new'){S.input=fresh();S.input.visit_date=S.state.today||today();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.step=0;S.current=null;S.preview=null;render();return;}
  if(action==='home-page'){if(!S.state.unlocked){S.view=S.state.vault_exists?'gate':'home';render();return;}S.view='home';S.expect=null;S.current=null;return work(async()=>{[S.health,S.state]=await Promise.all([api('/api/profile'),api('/api/state')]);render();window.scrollTo(0,0);});}
  if(action==='edit-profile')return editProfile();
  if(action==='edit-coverage')return editProfile('coverage');
  if(action==='wizard-edit-insurance'){collect();S.editInsurance=true;render();return;}
  if(target.dataset.stage)return goStage(target.dataset.stage);
  if(target.dataset.choose)return work(async()=>{S.current=await api('/api/case/contact',{id:S.current.id,status:S.current.status==='contacted'?'contacted':'comparing',provider_id:target.dataset.choose,notes:S.current.contact?.notes||''});render();$('.contact-checklist')?.scrollIntoView({behavior:'smooth',block:'start'});});
  if(action==='explain-ranking')return work(async()=>{const r=await api('/api/explain/comparison',{case_id:S.current.id,lang:I18n.locale==='zh'?'zh':'en'});const el=$('#ranking-explain');if(!el)return;el.hidden=false;el.innerHTML=`<p data-i18n-keep>${esc(r.text)}</p><p class="hint" data-i18n-keep>${esc(r.source)}</p>`;},'Explaining on this device…');
  if(action==='explain-coverage')return work(async()=>{const r=await api('/api/explain/coverage',{journey_id:S.journey.id,lang:I18n.locale==='zh'?'zh':'en'});const el=$('#coverage-explain');if(!el)return;el.hidden=false;el.innerHTML=`<p data-i18n-keep>${esc(r.text)}</p><p class="hint" data-i18n-keep>${esc(r.source)}</p>`;},'Explaining on this device…');
  if(action==='mode-need'||action==='mode-doctor'){S.homeMode=action==='mode-doctor'?'doctor':'need';render();if(S.homeMode==='doctor')$('#doctor-query')?.focus();return;}
  if(action==='doctor-search')return openDoctorSearch();
  if(action==='plans')return work(openPlans);
  if(action==='sbc-paste'){const t=$('#sbc-text')?.value||'';if(t.trim().length<200)return toast('Paste the whole SBC text.');return sendSbc({text:t,file_name:'pasted text'});}
  if(action==='add-plan'){readPlans();S.plans.plans.push({name:'',premium:'',oop_max:'',costs:{}});renderPlans();return;}
  if(action==='record-visit'){if(S.view==='home')S.current=null;return work(async()=>{if(!S.health)S.health=await api('/api/profile');recordVisit();});}
  if(action==='back-to-results'){S.visit=null;S.view='wizard';render();return;}
  if(action==='start-over'){if(!confirm('Erase the saved health profile on this computer and start a new one? This can’t be undone.'))return;return work(async()=>{S.state=await api('/api/vault/reset',{confirm:'erase'});trail.clear();S.health=null;S.state.profile_ready=false;editProfile();});}
  if(action==='known'){S.view='known';return work(async()=>{[S.health,S.state]=await Promise.all([api('/api/profile'),api('/api/state')]);render();window.scrollTo(0,0);});}
  if(action==='planned-care'){collect();S.sub='need';S.input.feel='okay';S.input.need='';S.preview=null;render();return;}
  if(action==='care-today')return advance();
  if(action==='see-places'){S.view='wizard';S.current=S.found;S.found=null;S.expect=null;S.step=4;render();window.scrollTo(0,0);return;}
  if(action==='health'){collect();S.step=0;S.sub='symptoms';S.safety=null;S.preview=null;render();window.scrollTo(0,0);return;}
  if(action==='boston'){collect();Object.assign(S.input,{city:'Boston',state:'MA',zip:'',lat:null,lon:null});render();return;}
  if(action==='neu-example'){
    S.activeJourney=null;S.journey=null;
    S.safety=null;S.input={...fresh(),scenario:'neu_student',city:'Brookline',state:'MA',zip:'02445',insurance:'yes',age:24,language:'Chinese',feel:'okay',need:'follow_up',service:'follow_up',
      plan:{name:'Northeastern University Student Health Plan (NUSHP) 2026–27 — exact product to confirm',rule:'copay',eligible:false}};
    S.step=0;S.sub='need';S.view='wizard';S.preview=null;S.current=null;S.expect=null;S.found=null;render();
    toast('Illustrative NEU student, ZIP only. Review all inputs. Current-year benefits, enrollment and clinic network are unconfirmed. Your saved profile is unchanged.');return;
  }
  if(action==='demo'){
    S.activeJourney=null;S.journey=null;
    const year=today().slice(0,4);S.safety=null;S.input={...fresh(),demo:true,insurance:'no',wants_insurance:true,lat:42.3505,lon:-71.1054,language:'Chinese',budget:200,age:28,none_reported:true,feel:'okay',need:'follow_up',service:'follow_up',
      description:'My clinician recommended a routine primary-care follow-up.',plan:{name:'Demo Student PPO',rule:'copay',premium:95,copay:25,deductible_remaining:50,coinsurance:20,oop_remaining:3000,start:year+'-01-01',end:year+'-12-31',eligible:false}};S.step=0;S.sub='need';S.view='wizard';S.preview=null;S.current=null;render();return;
  }
  if(action==='geolocate'){
    collect();if(!navigator.geolocation)return toast('Device location is unavailable. Enter your city instead.');
    navigator.geolocation.getCurrentPosition(position=>{S.input.lat=position.coords.latitude;S.input.lon=position.coords.longitude;render();toast('Coordinates stay on this device. Confirm your city before continuing.');},()=>toast('Location was unavailable or declined. You can continue with city and state.'),{timeout:10000,maximumAge:60000});return;
  }
  if(action==='agent')return work(async()=>{const status=await api('/api/agent/status');agentDialog(status);});
  if(action==='add-candidate')return candidateDialog();
  if(action==='plan')return planDialog();
  if(action==='contact')return contactDialog();
  if(action==='mark-booked')return contactDialog({status:'booked'});
  if(action==='unchoose')return work(async()=>{S.current=await api('/api/case/contact',{id:S.current.id,status:'comparing',provider_id:'',notes:S.current.contact?.notes||''});render();});
  if(action==='unlock'){S.view='gate';render();return;}
  if(action==='saved')return work(savedDialog);
  if(action==='privacy')return work(privacyDialog);
  if(action==='privacy-probe')return work(async()=>{const r=await api('/api/privacy/probe',{});await privacyDialog();toast((r.blocked?'Blocked as expected: ':'Self-check failed: ')+r.reason);});
  if(action==='offline')return work(async()=>{S.state=await api('/api/offline',{offline:!S.state.offline});await privacyDialog();});
  if(action==='lock')return work(async()=>{S.state=await api('/api/vault/lock',{});S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.current=null;S.step=0;S.preview=null;S.health=null;S.journey=null;S.reportDraft=null;S.homeGoal='';S.activeJourney=null;S.view='gate';dictation.abort();closeDialog();render();toast('Vault locked. Private information cleared from this page.');});
  if(action==='model-prep')return work(async()=>{if($('#prep-output'))$('#prep-output').textContent='Preparing a draft with your local model…';showPrep(await api('/api/case/preparation',{id:S.current.id,provider_id:S.preparingProvider,use_model:true}));});
  if(action==='copy-prep')return work(async()=>{const script=$('#script-text')?.textContent;if(!script)throw Error('Prepare a script first.');await navigator.clipboard.writeText(script);toast('Copied. You control where you share it.');});
});
document.addEventListener('change',event=>{if(event.target.name?.startsWith('dictation_'))dictation.abort();if(!event.target.name?.endsWith('_rule'))return;const box=event.target.closest('form')||document;box.querySelectorAll('[data-rule-fields]').forEach(el=>{el.hidden=el.dataset.ruleFields!==event.target.value;});});
$('#dialog').addEventListener('cancel',()=>{$('#dialog').innerHTML='';});
async function init(){try{S.state=await api('/api/state');S.input.visit_date=S.state.today;S.choices=(await api('/api/safety/choices')).choices;
  if(S.state.unlocked){await afterUnlock();return;}
  if(S.state.vault_exists){S.view='gate';}else{S.state.profile_ready=false;S.view='home';}
}catch(e){toast(e.message);S.view='gate';}render();}
I18n.init();
init();
setInterval(async()=>{if(S.busy||!S.state.unlocked)return;try{const state=await api('/api/state');if(!state.unlocked){S.state=state;S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.current=null;S.step=0;S.preview=null;S.health=null;S.journey=null;S.reportDraft=null;S.homeGoal='';S.activeJourney=null;S.view='gate';dictation.abort();closeDialog();render();toast('Your vault locked after inactivity. Unlock to resume your saved journey.');}}catch{}},30000);
