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

async function api(path, body) {
  const response = await fetch(path, {method:body === undefined ? 'GET':'POST', headers:{'X-FirstVisit':'local','Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 423 && S.state.unlocked) {
      S.state.unlocked = false; S.current = null; S.input = fresh(); S.safety = null; S.expect = null; S.found = null; S.sub = 'symptoms'; S.view = 'gate'; S.health = null; S.step = 0; S.preview = null; closeDialog(); render();
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
  finally { S.busy = false; document.body.classList.remove('busy'); if ($('#working')) $('#working').textContent = ''; }
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
  </div><label class="checkline"><input name="${prefix}eligible" type="checkbox" ${p.eligible?'checked':''}><span>I confirmed my eligibility with the plan or marketplace.</span></label></div>
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
  ['name','premium','start','end','rule','copay','deductible_remaining','coinsurance','oop_remaining'].forEach(k => p[k] = f.get('plan_'+k) ?? '');
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
    <span class="privacy-pill">${icon('lock')} ${S.state.preview_mode?'Temporary preview · fictional data only':'Local & private'}</span>
    ${S.state.unlocked?'<button class="nav-button" data-action="home-page">My health</button><button class="nav-button" data-action="known">What we know</button>':''}
    <button class="nav-button" data-action="saved">My care journeys</button>
    <button class="nav-button" data-action="privacy">Privacy</button>
    ${S.state.unlocked ? '<button class="nav-button" data-action="lock">Lock vault</button>' : S.state.vault_exists ? '<button class="nav-button" data-action="unlock">Unlock vault</button>' : ''}
    </nav></div>`;
}
function sidebar() {
  const names=['You & your health','What matters to you','When & where','Review & find care'];
  return `<aside class="journey-sidebar"><p class="eyebrow">A CLEARER PATH TO CARE</p><h1>Care that puts<br><em>you first.</em></h1><p class="sidebar-copy">We start with you and your health. Where to go comes after.</p><ol class="steps">${names.map((n,i)=>`<li class="${S.step===i?'active':S.step>i?'done':''}"><span>${S.step>i?icon('check'):String(i+1).padStart(2,'0')}</span><div>${n}<small>${['How you are doing, first','Language and coverage','Location is one detail','You control what is shared'][i]}</small></div></li>`).join('')}</ol><div class="sidebar-note">${icon('shield')}<p>Your health details stay on this device. Location is the only detail a public search uses, and you review it first.</p></div><button class="text-button" data-action="demo">Explore a fictional example ${icon('arrow')}</button></aside>`;
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
  return `<div class="safety-panel ${r.level}" role="${urgent?'alert':'status'}"><p class="eyebrow">YOUR SAFETY CHECK · ON THIS DEVICE</p><h3>${esc(r.headline)}</h3>${(r.hotlines||[]).map(h=>`<div class="hotline"><strong>${esc(h.name)}</strong><span>${esc(h.how)}</span></div>`).join('')}<p>${esc(r.why)}</p><p class="safety-options"><span>Good places to start:</span> ${r.options.map(o=>esc(venues[o]||o)).join(' · ')}</p>${r.rules.length?`<ul>${r.rules.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}${r.level==='emergency'?`<div class="call-actions">${callButtons(r)}</div><p class="safety-stop">Please get help now. This app won’t compare prices for an emergency. If something here is wrong, change your answers above.</p>`:''}${r.level==='same_day'?`<div class="safety-next"><button type="button" class="primary" data-action="care-today">Find care today ${icon('arrow')}</button><span>We’ll look for urgent care and campus clinics near you, and show what to expect.</span></div>`:''}<small>${esc(r.disclaimer||'')}</small></div>`;
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
  const actions=next=>`<div class="form-actions"><button type="button" class="text-button" data-action="home-page">← Back</button>${next}</div>`;
  const cont=`<button type="submit" class="primary">Continue ${icon('arrow')}</button>`;
  if(S.sub==='need') return healthHead('What do you need?','No symptom questions needed.')+
    `<div class="chips">${NEEDS.map(([id,t])=>`<button type="button" class="chip ${p.need===id?'selected':''}" data-need="${id}">${t}</button>`).join('')}</div>
    <label class="field"><span>Anything else? <small>Optional · stays local</small></span><textarea name="description" rows="2" maxlength="3000" placeholder="My doctor asked me to come back in two weeks.">${esc(p.description)}</textarea></label>`+actions(cont);
  const items=S.choices.filter(c=>c.level!=='routine');
  return healthHead('What’s bothering you?','Open a part of the body and pick what fits. If something sounds serious, we’ll tell you right away.')+
    groupCards(items,SYMPTOM_GROUPS,'chip')+
    `<label class="field"><span>Anything else? <small>Optional · stays local</small></span><textarea name="description" rows="2" maxlength="3000" placeholder="It started two days ago and gets worse at night.">${esc(p.description)}</textarea></label>
    <div id="safety-result">${S.safety&&['emergency','same_day'].includes(S.safety.level)?safetyPanel(S.safety):''}</div>`+
    actions(S.safety?.level==='emergency'?'':cont);
}
function card(title,hint,body,cls=''){return `<section class="form-card ${cls}"><div class="form-card-head"><h3>${title}</h3>${hint?`<p>${hint}</p>`:''}</div>${body}</section>`;}
function stepContent() {
  const p=S.input;
  if (S.step===0) return healthStep(p);
  if (S.step===1) {
    const insured=p.insurance==='yes', exploring=p.insurance==='no'&&p.wants_insurance;
    return `<div class="section-icon">${icon('shield')}</div><p class="eyebrow">02 / WHAT MATTERS TO YOU</p><h2>How should care work for you?</h2><p class="lede">Your language and coverage shape every option we show.</p>${safetySummary()}`+
    card('About you','Stays on this device.',`<div class="form-grid">${S.health?.age!=null?`<div class="field"><span>Your age</span><div class="from-profile">${S.health.age} <small>from your health profile</small></div><input type="hidden" name="age" value="${S.health.age}"></div>`:field('Your age','age',p.age,'number','required min="0" max="120" step="1" inputmode="numeric"')}${select('Preferred language','language',[['English','English'],['Chinese','Chinese / 中文'],['Spanish','Spanish / Español']],p.language)}</div>`)+
    card('Insurance','Do you have health insurance?',`<div class="choice-grid"><button type="button" class="choice ${insured?'selected':''}" data-insurance="yes"><span class="choice-radio"></span><strong>Yes, I have insurance</strong><span>Use my benefits and compare my personal cost.</span></button><button type="button" class="choice ${p.insurance==='no'?'selected':''}" data-insurance="no"><span class="choice-radio"></span><strong>No insurance right now</strong><span>Explore self-pay care and optional coverage.</span></button></div>
      ${p.insurance==='no'?`<div class="sub-card"><p class="sub-title">Would you like to explore insurance?</p><div class="segmented"><button type="button" class="${!p.wants_insurance?'selected':''}" data-wants="no">Continue without it</button><button type="button" class="${p.wants_insurance?'selected':''}" data-wants="yes">Compare getting a plan</button></div><p class="hint">Check your school account first. You may already be enrolled in student coverage.</p></div>`:''}`)+
    (insured||exploring?card(insured?'Your current plan':'A plan you’re considering',insured?'Enter what you know. You can still find care before every benefit is confirmed.':'Use an actual plan quote, or leave this blank and explore options after your search.',planFields(p.plan)+planResources()):'');
  }
  if (S.step===2) return `<div class="section-icon">${icon('pin')}</div><p class="eyebrow">03 / WHEN & WHERE</p><h2>When and where works for you?</h2><p class="lede">Location is one part of the picture. It’s also the only detail a public search uses.</p>`+
    card('When','',field('Planned visit date','visit_date',p.visit_date,'date',`required min="${today()}"`))+
    card('What matters most','How we order your options.',`<div class="form-grid">${select('Put this first','priority',[['balanced','My fit: language, budget, then cost'],['cost','Lowest supported personal cost'],['rating','Highest sourced patient rating'],['distance','Closest known location']],p.priority)}${field('Visit budget ($, optional)','budget',p.budget,'number','min="0" step="0.01" placeholder="Your comfort zone"')}</div>`)+
    card('Where','The only detail a public search uses. You review it before anything is sent.',`<div class="location-choice">${icon('pin')}<div><strong>Boston, Massachusetts</strong><span>Our first supported local directory</span></div><button type="button" class="text-button" data-action="boston">Use Boston</button></div><div class="form-grid three">${field('City','city',p.city,'text','required maxlength="70" autocomplete="address-level2"')}${field('State','state',p.state,'text','required pattern="[A-Za-z]{2}" maxlength="2" autocomplete="address-level1"')}${field('ZIP (optional)','zip',p.zip,'text','pattern="[0-9]{5}" maxlength="5" autocomplete="postal-code"')}</div><button type="button" class="secondary" data-action="geolocate">${icon('pin')} Add my device location</button><p class="hint">${p.lat!=null?'Coordinates added for distance. They stay on this device.':'Optional. Exact coordinates stay on this device.'}</p>`);
  const queries = S.preview?.queries || [];
  return `<div class="section-icon">${icon('lock')}</div><p class="eyebrow">04 / REVIEW & FIND CARE</p><h2>Your information. Your control.</h2><p class="lede">Here’s what we’ll use to find your next step.</p>`+
    card('Your summary','',`<div class="review-list"><div><span>Your safety check</span><strong>${esc(S.safety?.headline||'Not checked')}</strong></div><div><span>Care</span><strong>${serviceName(p.service)}</strong></div><div><span>Payment</span><strong>${p.insurance==='yes'?'Insurance + self-pay comparison':p.wants_insurance?'Self-pay + optional insurance scenario':'Self-pay; optional comparison later'}</strong></div><div><span>Search area</span><strong>${esc(p.city)}, ${esc(p.state)} ${esc(p.zip)}</strong></div></div>`)+
    card('Help us prepare your visit','Optional. Used only on this device for your call script and doctor card.',`<label class="field"><span>Conditions, allergies, or clinician instructions</span><textarea name="history" maxlength="3000" rows="3">${esc(p.history)}</textarea></label>${field('Current medications','medications',p.medications,'text','maxlength="1000"')}`)+
    card('What stays and what’s shared','',`<div class="share-split"><div><strong>${icon('lock')} Stays on this device</strong><p>Health details, history, medications, exact coordinates, benefits and rankings.</p></div><div><strong>${icon('pin')} Can be shared</strong><p>${S.preview?(queries.length?'The search below, only after you approve it.':'Nothing. No public search is configured.'):'City, state and ZIP for a public search. You’ll see it first.'}</p></div></div>
      ${S.preview&&queries.length?`<div class="sub-card"><p class="sub-title">Public search preview</p>${queries.map(q=>`<div class="query"><span>${esc(q.provider)}</span><code>${esc(q.query)}</code></div>`).join('')}<p class="hint">Recipients: ${S.preview.destinations.map(esc).join(', ')}. Search providers can infer a general interest in this care category.</p><label class="checkline"><input type="checkbox" name="live" checked><span>Send these queries to find more providers. Uncheck to use the local directory only.</span></label></div>`:S.preview?`<p class="hint">${p.demo?'No external search. All sample providers, prices, reviews and plan relationships are fictional.':'The Boston directory has official source links; prices and coverage need confirmation.'}</p>`:''}`)+
    (!S.state.unlocked?card(S.state.vault_exists?'Unlock your private vault':'Create your private vault','Encrypts your saved care journeys on this computer. There is no password recovery.',field('Vault passphrase','passphrase','','password',`required minlength="8" maxlength="1000" autocomplete="${S.state.vault_exists?'current-password':'new-password'}"`)):'');
}
const pfield=(label,name,value,type='text',extra='')=>field(label,name,value,type,extra);
function fromProfile(){
  const h=S.health?.profile||{}, i=fresh();
  Object.assign(i,{visit_date:S.state.today||today(),language:h.language||'English',insurance:h.insurance||'',wants_insurance:!!h.wants_insurance,plan:h.plan||null,
    age:S.health?.age??'',history:[...(h.conditions||[]),...((h.allergies||[]).length?['Allergies: '+h.allergies.join(', ')]:[])].join('; '),medications:(h.medications||[]).join(', ')});
  return i;
}
function startVisit(feel){
  S.input=fromProfile(); Object.assign(S.input,{feel,none_reported:feel==='okay'});
  S.sub=feel==='okay'?'need':'symptoms'; S.step=0; S.safety=null; S.open=new Set(); S.preview=null; S.current=null; S.expect=null; S.view='wizard'; render(); window.scrollTo(0,0);
}
function todoRow(t){
  return `<div class="todo ${t.done_on?'done':''} ${t.urgent?'urgent':''}"><button type="button" class="todo-check" data-todo="${esc(t.id)}" aria-pressed="${!!t.done_on}" aria-label="Mark ${esc(t.title)} done">${t.done_on?icon('check'):''}</button><div><strong>${esc(t.title)}</strong><p>${esc(t.done_on?`Done on ${t.done_on}`:t.why)}${t.source?` · <a href="${esc(t.source.url)}" target="_blank" rel="noopener noreferrer">${esc(t.source.title)}</a>`:''}</p></div></div>`;
}
function renderHome(){
  const h=S.health, p=h.profile, open=h.todos.filter(t=>!t.done_on), personal=open.filter(t=>['refill','follow_up'].includes(t.kind)), prevent=open.filter(t=>!['refill','follow_up'].includes(t.kind)), done=h.todos.filter(t=>t.done_on);
  const list=(arr)=>arr.length?arr.map(t=>`<span class="tag">${esc(t)}</span>`).join(''):'<span class="muted">None added</span>';
  $('#app').innerHTML=`<div class="home">
  <p class="eyebrow">YOUR HEALTH, IN ONE PLACE</p><h1 class="home-title">${S.justCreated?'Your health, in one place.':'Welcome back.'}</h1><p class="lede">Everything here stays encrypted on this device. It grows with every visit.</p>
  <section class="form-card need-card"><div class="form-card-head"><h3>What do you need today?</h3></div><div class="feel-row">${FEELS.map(([id,t,d])=>`<button type="button" class="choice feel" data-feel="${id}"><strong>${t}</strong><span>${d}</span></button>`).join('')}</div></section>
  <div class="home-grid">
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
    <section class="form-card"><div class="form-card-head"><h3>Better choices</h3></div>${h.choices.map(c=>`<div class="choice-tip"><strong>${esc(c.title)}</strong><p>${esc(c.why)}${c.source?` · <a href="${esc(c.source.url)}" target="_blank" rel="noopener noreferrer">${esc(c.source.title)}</a>`:''}</p></div>`).join('')}</section>
  </div></div>`;
}
function listRows(kind,rows){
  const [a,b,la,lb,ta]=kind==='med'?['name','refill_by','Medication','Runs out (optional)','text']:['what','due','What','Due (optional)','text'];
  return `<div class="rows">${rows.map((r,i)=>`<div class="row-2">${field(la,`${kind}_${a}_${i}`,r[a],ta,'maxlength="160"')}${field(lb,`${kind}_${b}_${i}`,r[b],'date')}</div>`).join('')}</div><button type="button" class="secondary small" data-add-row="${kind}">+ Add ${kind==='med'?'medication':'follow-up'}</button>`;
}
function renderProfile(){
  const d=S.draft, first=!S.state.vault_exists||!S.state.profile_ready;
  $('#app').innerHTML=`<div class="home"><form id="profile-form"><p class="eyebrow">${first?'START HERE':'YOUR HEALTH PROFILE'}</p><h1 class="home-title">${first?'Let’s get to know your health.':'Your health profile'}</h1><p class="lede">It stays encrypted on this device and grows with every visit. Skip anything you don’t want to add.</p>
    ${card('About you','Your age decides which checkups and vaccines we suggest.',`<div class="form-grid three">${field('Birth year','birth_year',d.birth_year??'','number','min="1900" max="'+new Date().getFullYear()+'" step="1" inputmode="numeric" required')}${select('Sex (optional)','sex',[['','Prefer not to say'],['female','Female'],['male','Male']],d.sex||'')}${select('Preferred language','language',[['English','English'],['Chinese','Chinese / 中文'],['Spanish','Spanish / Español']],d.language||'English')}</div><p class="hint">Sex is only used for screenings like cervical or breast cancer checks.</p>`)}
    ${card('Ongoing health','Optional. Separate items with commas.',`<label class="field"><span>Conditions</span><textarea name="conditions" rows="2" maxlength="2000" placeholder="Asthma, migraines">${esc((d.conditions||[]).join(', '))}</textarea></label><label class="field"><span>Allergies</span><textarea name="allergies" rows="2" maxlength="2000" placeholder="Penicillin, peanuts">${esc((d.allergies||[]).join(', '))}</textarea></label>`)}
    ${card('Medications','We’ll remind you before one runs out.',listRows('med',d.meds))}
    ${card('Follow-ups','Visits or tests a clinician asked you to come back for.',listRows('fu',d.fus))}
    ${card('Coverage','Do you have health insurance?',`<div class="choice-grid"><button type="button" class="choice ${d.insurance==='yes'?'selected':''}" data-pins="yes"><span class="choice-radio"></span><strong>Yes</strong><span>I have a plan</span></button><button type="button" class="choice ${d.insurance==='no'?'selected':''}" data-pins="no"><span class="choice-radio"></span><strong>Not right now</strong><span>Self-pay, or choosing a plan</span></button></div>${d.insurance==='yes'?`<div class="sub-card"><p class="sub-title">Your plan</p>${field('Exact plan name','pplan_name',d.plan?.name||'','text','maxlength="120"')}</div>`:''}${d.insurance==='no'?`<label class="checkline"><input type="checkbox" name="wants_insurance" ${d.wants_insurance?'checked':''}><span>I’m thinking about getting a plan</span></label>`:''}`)}
    ${!S.state.vault_exists?card('Save it privately','Choose a passphrase. It encrypts your profile on this computer. There is no recovery.',field('Passphrase','passphrase','','password','required minlength="8" maxlength="1000" autocomplete="new-password"')):''}
    <div class="form-actions">${first?'<span class="small-note">You can change this anytime.</span>':'<button type="button" class="text-button" data-action="home-page">← Cancel</button>'}<button type="submit" class="primary">${first?'Save and continue':'Save'} ${icon('arrow')}</button></div></form></div>`;
  $('#profile-form').addEventListener('submit',e=>{e.preventDefault();saveProfile();});
}
function readDraft(){
  const f=$('#profile-form'); if(!f) return; const g=n=>f.elements[n]?.value??'';
  Object.assign(S.draft,{birth_year:g('birth_year'),sex:g('sex'),language:g('language'),conditions:g('conditions').split(',').map(x=>x.trim()).filter(Boolean),allergies:g('allergies').split(',').map(x=>x.trim()).filter(Boolean),
    meds:S.draft.meds.map((_,i)=>({name:g(`med_name_${i}`),refill_by:g(`med_refill_by_${i}`)})),fus:S.draft.fus.map((_,i)=>({what:g(`fu_what_${i}`),due:g(`fu_due_${i}`)})),
    wants_insurance:f.elements.wants_insurance?f.elements.wants_insurance.checked:S.draft.wants_insurance});
  if(f.elements.pplan_name) S.draft.plan={...(S.draft.plan||{}),name:g('pplan_name')};
}
function editProfile(){
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
    S.state=await api('/api/state'); S.view='home'; render(); window.scrollTo(0,0); toast('Saved on this device.');
  });
}
function renderGate(){
  $('#app').innerHTML=`<div class="home narrow"><p class="eyebrow">WELCOME BACK</p><h1 class="home-title">Unlock your health profile.</h1><p class="lede">A health profile is saved on this computer. It’s encrypted, so it needs your passphrase. For your privacy it locks itself after a while.</p><form id="gate-form"><section class="form-card">${field('Your passphrase','passphrase','','password','required minlength="8" maxlength="1000" autocomplete="current-password"')}${S.state.preview_mode?'<p class="hint">Test preview passphrase: <code>firstvisit-preview-only</code></p>':''}</section><div class="form-actions"><span class="small-note">Nothing is sent anywhere.</span><button type="submit" class="primary">Unlock ${icon('arrow')}</button></div></form>
  <section class="form-card new-here"><div class="form-card-head"><h3>New here, or forgot your passphrase?</h3><p>Start a new profile. This erases the saved profile on this computer. There’s no way to recover it.</p></div><button type="button" class="secondary" data-action="start-over">Start a new profile</button></section></div>`;
  $('#gate-form').addEventListener('submit',e=>{e.preventDefault();work(async()=>{S.state=await api('/api/vault/unlock',{passphrase:$('[name="passphrase"]').value});await afterUnlock();});});
}
async function afterUnlock(){ S.justCreated=false; S.health=await api('/api/profile'); if(S.health.complete){S.view='home';}else{editProfile();return;} render(); }
function renderKnown(){
  const p=S.health.profile, row=(field,value,label)=>`<div class="known-row"><span>${esc(label)}</span><button type="button" class="text-button" data-forget="${field}" data-value="${esc(value)}">Forget</button></div>`;
  const rows=[...(p.birth_year?[row('birth_year','',`Birth year ${p.birth_year}`)]:[]),...(p.sex?[row('sex','',`Sex: ${p.sex}`)]:[]),...(p.conditions||[]).map(v=>row('conditions',v,`Condition: ${v}`)),...(p.medications||[]).map(v=>row('medications',v,`Medication: ${v}`)),...(p.allergies||[]).map(v=>row('allergies',v,`Allergy: ${v}`)),...(p.follow_ups||[]).map(f=>row('follow_ups',f.what,`Follow-up: ${f.what}`)),...(p.plan?[row('plan','',`Plan: ${p.plan.name}`)]:[]),row('visits','',`Saved care journeys: ${S.state.cases.length}`)];
  $('#app').innerHTML=`<div class="home narrow"><p class="eyebrow">WHAT WE KNOW</p><h1 class="home-title">Everything FirstVisit knows about you.</h1><p class="lede">All of it is encrypted on this device. None of it is sent with searches.</p>${card('Your saved information','Forget any item. This can’t be undone.',`<div class="known">${rows.join('')}</div>`)}<div class="form-actions"><button type="button" class="text-button" data-action="home-page">← Back</button><button type="button" class="secondary" data-forget="everything">Forget everything</button></div></div>`;
}
function render() {
  renderHeader();
  if (S.view==='loading') { $('#app').innerHTML='<div class="home"><p class="lede">Loading…</p></div>'; return; }
  if (S.view==='gate') return renderGate();
  if (S.view==='profile') return renderProfile();
  if (S.view==='home') return renderHome();
  if (S.view==='known') return renderKnown();
  if (S.expect) return renderExpect();
  if (S.step===4 && S.current) return renderResults();
  $('#app').innerHTML = `<div class="wizard-layout">${sidebar()}<section class="form-panel">${S.input.demo?'<div class="demo-banner">FICTIONAL DEMO · No actual providers, prices, ratings or insurance offers</div>':''}<form id="wizard">${stepContent()}${S.step===0?'':`<div class="form-actions">${S.step>0?'<button type="button" class="text-button" data-action="back">← Back</button>':'<span class="small-note">A few steps to a clearer choice.</span>'}<button type="submit" class="primary">${S.step===3?(S.preview?'Find my care':'Review search'):'Continue'} ${icon('arrow')}</button></div>`}<div id="working" role="status" class="working"></div></form></section></div>`;
  $('#wizard').addEventListener('submit', event => {event.preventDefault(); advance();});
}
async function advance() {
  if (!$('#wizard').reportValidity()) return;
  collect();
  if(S.step===0){
    if(S.sub==='symptoms' && !S.input.checks.length && !S.input.description.trim()) return toast('Pick what’s bothering you, or describe it in a few words.');
    if(S.sub==='need'){
      if(!S.input.need) return toast('Choose what you need.');
      if(S.input.need==='unsure'){ S.sub='symptoms'; S.input.feel='unsure'; render(); return toast('Tell us what’s going on first.'); }
    }
    let r; try{ r=await api('/api/safety',{checks:S.input.checks,description:S.input.description}); }catch(e){ return toast(e.message); }
    S.safety=r;
    if(r.level==='emergency' || (r.level==='same_day' && S.input.service!=='same_day')){ render(); $('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'}); return; }
  }
  if(S.step===1 && Number(S.input.age)<18) return toast('This version supports adults (18+). For a child or teen, contact a pediatric clinician.');
  if(S.step===1 && !S.input.insurance) return toast('Choose whether you have insurance.');
  if(S.step<3) {S.step++; S.preview=null; render(); window.scrollTo(0,0); return;}
  await work(async()=>{
    if (!S.state.unlocked) {
      const passphrase=$('[name="passphrase"]').value;
      S.state=await api(S.state.vault_exists?'/api/vault/unlock':'/api/vault/create',{passphrase});
      $('[name="passphrase"]').value='';
    }
    if(!S.preview) {S.preview=await api('/api/preview',S.input); render(); return;}
    const body={token:S.preview.token,approved:true,live:!!$('[name="live"]')?.checked};
    S.expect={data:S.preview.expect,status:'searching',found:null}; S.preview=null; renderExpect(); window.scrollTo(0,0);
    try{ const result=await api('/api/search',body); S.found=result; S.expect.status='ready'; S.expect.found=result.results.length; S.state=await api('/api/state'); }
    catch(e){ S.expect.status='error'; S.expect.error=e.message; }
    renderExpect();
  },'Finding care and checking the available evidence…');
}
function costLabel(cost) {return ({unknown:'Needs confirmation',not_active:'Outside coverage dates',demo:'Synthetic example',conditional:'Conditional estimate',user_quote:'User-entered quote'})[cost.status] || 'Estimate';}
function compareBlock(row, compact=true) {
  const c=row.comparison;
  return `<div class="comparison ${compact?'compact':''}"><div class="compare-line"><span>Same visit, self-pay</span><strong>${dollars(c.cash.amount)}</strong></div><div class="compare-line"><span>Your share with this plan</span><strong>${dollars(c.insured.amount)}</strong></div><div class="compare-line"><span>Premiums × ${c.months} month${c.months===1?'':'s'}</span><strong>${dollars(c.premium_total)}</strong></div><div class="compare-line total"><span>Visit + premiums</span><strong>${dollars(c.total_with_plan)}</strong></div>${c.net_difference!=null?`<div class="difference ${c.net_difference>0?'positive':''}">${c.net_difference>0?`${dollars(c.net_difference)} less`:c.net_difference<0?`${dollars(-c.net_difference)} more`:'Same estimated total'} <span>than self-pay for this scenario</span></div>`:`<p class="hint">${esc(c.insured.amount==null?c.insured.reason:c.note)}</p>`}<p class="hint">One visit only. ${c.eligible?'Eligibility entered as confirmed.':'Eligibility not confirmed.'} ${esc(c.scope)}</p></div>`;
}
function providerCard(row,index) {
  const p=row.provider, rating=p.rating;
  const link=p.url?`<a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer" class="text-button">View source ↗</a>`:'<span class="hint">Fictional provider; no booking link</span>';
  return `<article class="provider-card ${index===0?'first':''}"><div class="card-top"><div class="provider-avatar">${icon('building')}</div><div class="provider-title"><div class="provider-label">${esc(p.kind)}${p.demo?' · DEMO':''}</div><h3>${esc(p.name)}</h3><p>${esc(p.address)}</p></div><span class="rank">${String(index+1).padStart(2,'0')}</span></div><div class="card-stats"><div><span>YOUR VISIT COST</span><strong class="price">${dollars(row.cost.amount)}</strong><small>${costLabel(row.cost)} · ${row.pathway}</small></div><div><span>PATIENT EXPERIENCE</span><strong>${rating?`<span class="star">★</span> ${rating.value.toFixed(1)} <small>/ 5</small>`:'Not available'}</strong><small>${rating?`${rating.count} ${p.demo?'synthetic':'user-entered'} reviews`:'No sourced rating yet'}</small></div><div><span>DISTANCE</span><strong>${row.miles==null?'Not verified':`${row.miles} mi`}</strong><small>${row.miles==null?'Check the source location':'Straight-line; not travel time'}</small></div></div><ul class="match-reasons">${row.reasons.map(r=>`<li>${icon('check')}${esc(r)}</li>`).join('')}</ul><details class="evidence"><summary>Cost, insurance & evidence</summary><p>${esc(p.source_note)}</p><p class="hint">Source checked: ${esc(p.checked_on)}. Patient reviews describe experience, not clinical quality.</p>${rating?`<p class="hint">Rating source: ${esc(rating.source)} · ${esc(rating.checked_on)}</p>`:''}<p><strong>Insurance:</strong> ${esc(row.insured.reason)}</p>${row.cost.breakdown.map(b=>`<div class="compare-line"><span>${esc(b.label)}</span><strong>${dollars(b.amount)}</strong></div>`).join('')}<p class="hint">Price source: ${esc(row.cost.source || 'No scoped price yet')}${row.cost.checked_on?' · '+esc(row.cost.checked_on):''}</p>${S.current.input.plan?compareBlock(row):'<p>Add a plan to compare the same visit with insurance.</p>'}${link}</details><div class="card-actions"><button class="primary small" data-prepare="${p.id}">Prepare this visit ${icon('arrow')}</button><button class="text-button" data-quote="${p.id}">Add quote / confirmation</button></div></article>`;
}
function renderExpect(){
  renderHeader();
  const x=S.expect, d=x.data, ill=d.illustration;
  const status=x.status==='searching'?`<div class="expect-status">${icon('pin')}<div><strong>Finding places near you…</strong><span>While that runs, here’s what to expect.</span></div></div>`
    :x.status==='ready'?`<div class="expect-status ready">${icon('check')}<div><strong>${x.found?`${x.found} ${x.found===1?'place':'places'} found`:'Search finished'}</strong><span>${x.found?'Ready when you are.':'No places came back. The guidance below still applies.'}</span></div><button type="button" class="primary" data-action="see-places">${x.found?'See places':'Continue'} ${icon('arrow')}</button></div>`
    :`<div class="expect-status error"><div><strong>The search didn’t finish</strong><span>${esc(x.error||'')}</span></div><button type="button" class="secondary" data-action="home">Start again</button></div>`;
  $('#app').innerHTML=`<div class="results-page expect-page">${S.input.demo?'<div class="demo-banner">FICTIONAL DEMO · These are not actual care recommendations or insurance offers.</div>':''}
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
function renderResults() {
  const c=S.current,p=c.input,known=c.results.filter(r=>r.supported&&r.cost.amount!=null),min=known.length?Math.min(...known.map(r=>r.cost.amount)):null;
  $('#app').innerHTML=`<div class="results-page">${p.demo?'<div class="demo-banner">FICTIONAL DEMO · These are not actual care recommendations or insurance offers.</div>':''}<div class="results-heading"><div><p class="eyebrow">YOUR NEXT STEP, A LITTLE CLEARER</p><h1>Care around <em>you.</em></h1><p>${esc(p.city)}, ${esc(p.state)} <span class="dot">·</span> ${serviceName(p.service)} <span class="dot">·</span> ${esc(p.visit_date)}</p></div><button class="secondary" data-action="new">Start a new search ${icon('arrow')}</button></div><div class="result-metrics"><div><span>OPTIONS FOUND</span><strong>${c.results.length}<small> in your shortlist</small></strong></div><div><span>LOWEST SUPPORTED COST</span><strong>${dollars(min)}<small>${known.length?' for this visit':' · confirm quotes first'}</small></strong></div><div><span>YOUR HEALTH PROFILE</span><strong>${icon('lock')} Stays local</strong></div></div>${c.errors.length?`<div class="notice">Live discovery had a problem: ${c.errors.map(esc).join('; ')}. Available local results remain below.</div>`:''}<div class="results-layout"><section><div class="results-toolbar"><div><h2>Your shortlist</h2><p>Ordered by your preferences, among the options found.</p></div>${select('Sort by','result_priority',[['balanced','My fit'],['cost','Lowest cost'],['rating','Patient rating'],['distance','Distance']],p.priority)}</div>${c.results.length?c.results.map(providerCard).join(''):'<div class="empty"><h3>No local providers found here yet.</h3><p>Live discovery is not connected. You can use the official health-center finder below; this shortlist will not substitute providers from another city.</p><a href="https://findahealthcenter.hrsa.gov/" target="_blank" rel="noopener noreferrer">Find a community health center ↗</a></div>'}</section><aside class="results-aside"><div class="aside-panel"><span class="aside-icon">${icon('shield')}</span><h3>${p.insurance==='yes'?'Make your benefits work for you.':'Would insurance change the picture?'}</h3><p>Compare the same visit, then include what the plan itself costs.</p>${p.plan?`<div class="plan-chip"><span>PLAN SCENARIO</span><strong>${esc(p.plan.name)}</strong><small>${p.plan.start?'Starts '+esc(p.plan.start):'Start date unconfirmed'} · ${p.plan.eligible?'Eligibility entered as confirmed':'Eligibility unconfirmed'}</small></div>`:'<p class="hint">No plan entered. Add a quote to calculate a scenario; unknown prices stay unknown.</p>'}<button class="primary full" data-action="plan">${p.plan?'Edit plan comparison':'Compare an insurance plan'} ${icon('arrow')}</button><p class="hint">Potential savings depend on eligibility, coverage dates, exact network and benefit rules. A lower visit copay does not always mean a lower total.</p><a href="${p.state==='MA'?'https://betterhealthconnector.com/get-started/individuals-families':'https://www.healthcare.gov/see-plans/'}" target="_blank" rel="noopener noreferrer" class="text-button">Explore official coverage options ↗</a></div><div class="aside-panel quiet"><h3>What we know. What we don’t.</h3><p>${p.demo?'This sample illustrates the complete comparison with fictional data.':c.live_searched?'Live discovery adds leads to a small sourced directory. Search matches still need provider confirmation.':'This is a small sourced directory, not an exhaustive search.'}</p><p>Appointments, exact networks and complete charges need confirmation. Unknown price never means free.</p><a href="https://www.healthcare.gov/choose-a-plan/your-total-costs/" target="_blank" rel="noopener noreferrer">How health costs work ↗</a></div><div class="aside-panel quiet"><h3>Your ongoing care journey</h3><p>Status: <strong>${esc(c.status)}</strong></p><p class="hint">A booking link does not confirm an appointment. Record the outcome after contacting the provider.</p><button class="text-button" data-action="contact">Update appointment status →</button></div></aside></div></div>`;
  $('[name="result_priority"]').addEventListener('change',event=>work(async()=>{S.current=await api('/api/case/preferences',{id:c.id,priority:event.target.value});render();}));
}
function openDialog(title,html,wide=false) {
  const d=$('#dialog'); d.innerHTML=`<div class="dialog-head"><h2 id="dialog-title">${title}</h2><button class="icon-button" data-action="close" aria-label="Close dialog">×</button></div>${html}`; d.className=wide?'wide':''; if(!d.open)d.showModal();
}
function closeDialog() {$('#dialog').close();$('#dialog').innerHTML='';}
function planDialog() {
  const p=S.current.input;
  openDialog('Compare a plan, including its cost',`<p class="lede">A scenario for the same visit at each provider. This is not an enrollment or eligibility decision.</p><form id="plan-form">${planResources()}${planFields(p.plan)}${field('Number of premium payments to include','months',p.months,'number','required min="1" max="12" step="1"')}<p class="hint">For example, 12 includes a year of premiums but still only this one visit. This is not a complete annual healthcare forecast.</p><button class="primary" type="submit">Update comparison ${icon('arrow')}</button></form>`,true);
  $('#plan-form').addEventListener('submit',e=>{e.preventDefault();const plan=readPlan(e.target),months=e.target.elements.months.value;work(async()=>{S.current=await api('/api/case/preferences',{id:S.current.id,plan,months});closeDialog();render();toast('Comparison updated locally. Confirm each provider’s exact-plan participation.');});});
}
function quoteDialog(id) {
  const row=S.current.results.find(r=>r.provider.id===id),p=row.provider,plan=S.current.input.plan;
  openDialog('Add a quote or confirmation',`<p>${esc(p.name)} · ${serviceName(S.current.input.service)}</p><form id="quote-form"><div class="form-grid">${field('Complete self-pay quote ($)','cash',p.cash.amount,'number','min="0" step="0.01"')}${field('Date you checked','checked_on',today(),'date',`required max="${today()}"`)}${field('Exact plan / network name','plan_name',plan?.name)}${field('Allowed amount for this service ($)','allowed_amount','','number','min="0" step="0.01"')}</div>${field('Source (person, quote reference, or URL)','source','','text','required placeholder="For example: billing office call, Nov 7" maxlength="500"')}<label class="checkline"><input type="checkbox" name="service_confirmed"><span>I confirmed this location offers this service for adult patients.</span></label><label class="checkline"><input type="checkbox" name="scope_confirmed"><span>I confirmed the quote covers the defined visit, including applicable facility/professional fees.</span></label><label class="checkline"><input type="checkbox" name="network_confirmed"><span>I confirmed this exact plan, provider, location and service are in-network.</span></label><details class="private-details"><summary>Add sourced patient reviews (optional)</summary><div class="form-grid">${field('Patient rating (0–5)','rating','','number','min="0" max="5" step="0.1"')}${field('Number of reviews','rating_count','','number','min="1" step="1"')}</div>${field('Rating source URL','rating_source','','url')}</details><p class="hint">Saved as user-entered evidence, not independently verified. Additional services are excluded from the visit comparison.</p><button type="submit" class="primary">Save & rerank ${icon('arrow')}</button></form>`,true);
  $('#quote-form').addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.target),b=Object.fromEntries(f);['service_confirmed','scope_confirmed','network_confirmed'].forEach(k=>b[k]=f.has(k));work(async()=>{S.current=await api('/api/case/quote',{...b,id:S.current.id,provider_id:id});closeDialog();render();toast('Evidence saved. Your shortlist has been recalculated.');});});
}
function preparationDialog(id) {
  const p=S.current.results.find(r=>r.provider.id===id).provider;
  openDialog('Make the next step easier',`<p class="lede">${esc(p.name)}</p><div class="soft-note">Review your script before sharing. Nothing is sent to the provider.</div><div id="prep-output" class="prep-output">Preparing your questions…</div><div class="dialog-actions"><button class="secondary" data-action="model-prep">Use my local model</button><button class="secondary" data-action="copy-prep">Copy script</button>${p.url?`<a class="primary" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">Open provider website ↗</a>`:''}</div><p class="hint">The provider website is a separate service with its own privacy practices. A visit is booked only after you receive confirmation.</p>`);
  work(async()=>{const result=await api('/api/case/preparation',{id:S.current.id,use_model:false});showPrep(result);});
}
function showPrep(result) {if($('#prep-output'))$('#prep-output').innerHTML=`<span class="source-label">${esc(result.source)} · review this draft</span><pre id="script-text">${esc(result.text)}</pre>`;}
function contactDialog() {
  const c=S.current;
  openDialog('Keep track of your next step',`<form id="contact-form">${select('Status','status',[['comparing','Still comparing'],['contacted','Contacted a provider'],['booked','Appointment confirmed'],['attended','Visit completed']],c.status)}${select('Provider','provider_id',[['','Not selected'],...c.providers.map(p=>[p.id,p.name])],c.contact?.provider_id||'')}${field('Booking reference or how it was confirmed','reference',c.contact?.reference)}<label class="field"><span>Notes / next steps</span><textarea name="notes" rows="4" maxlength="3000">${esc(c.contact?.notes||'')}</textarea></label><button class="primary">Save to my care journey</button></form>`);
  $('#contact-form').addEventListener('submit',e=>{e.preventDefault();const b=Object.fromEntries(new FormData(e.target));work(async()=>{S.current=await api('/api/case/contact',{...b,id:c.id});closeDialog();render();});});
}
function unlockDialog(after) {
  openDialog(S.state.vault_exists?'Unlock your private vault':'Your care, saved privately',S.state.vault_exists?`<form id="unlock-form">${field('Passphrase','passphrase','','password','required minlength="8" autocomplete="current-password"')}<button class="primary">Unlock</button></form>`:'<p>Start your care search to create an encrypted local vault at the review step.</p><button class="primary" data-action="close">Continue</button>');
  if($('#unlock-form'))$('#unlock-form').addEventListener('submit',e=>{e.preventDefault();const passphrase=e.target.elements.passphrase.value;work(async()=>{S.state=await api('/api/vault/unlock',{passphrase});closeDialog();renderHeader();if(after)await after();});});
}
async function savedDialog() {
  if(!S.state.unlocked)return unlockDialog(savedDialog);
  S.state=await api('/api/state');
  openDialog('My care journeys',S.state.cases.length?`<div class="saved-list">${S.state.cases.map(c=>`<button data-case="${c.id}"><span>${esc(c.service)} ${c.demo?'· Demo':''}<small>${esc(c.city)} · ${new Date(c.created*1000).toLocaleDateString()}</small></span><span>${esc(c.status)} →</span></button>`).join('')}</div>`:'<p>Your saved searches and appointment steps will appear here.</p>');
}
async function privacyDialog() {
  if(!S.state.unlocked)return unlockDialog(privacyDialog);
  const data=await api('/api/privacy');
  openDialog('Your privacy, in view',`<p>Personal data is encrypted in your local vault. No cloud model or analytics is connected.</p><div class="privacy-numbers"><div><strong>${data.attempted}</strong><span>External attempts</span></div><div><strong>${data.blocked}</strong><span>Requests blocked</span></div><div><strong>${data.local_calls}</strong><span>Local model calls</span></div></div><button class="secondary" data-action="offline">${S.state.offline?'Turn live discovery back on':'Turn on offline mode'}</button><p class="hint">Failed requests may still reach a destination and count as external attempts. ${esc(data.scope)}</p><details><summary>Recent gateway activity</summary><pre class="ledger">${esc(JSON.stringify(data.ledger,null,2))}</pre></details>`,true);
}
document.addEventListener('click',event=>{
  const target=event.target.closest('button, [data-action]');if(!target||S.busy)return;
  if(target.dataset.group){collect();const t=target.dataset.group;S.open.has(t)?S.open.delete(t):S.open.add(t);render();return;}
  if(target.dataset.feel)return startVisit(target.dataset.feel);
  if(target.dataset.pins){readDraft();S.draft.insurance=target.dataset.pins;renderProfile();return;}
  if(target.dataset.addRow){readDraft();(target.dataset.addRow==='med'?S.draft.meds:S.draft.fus).push(target.dataset.addRow==='med'?{name:'',refill_by:''}:{what:'',due:''});renderProfile();return;}
  if(target.dataset.todo){const t=S.health.todos.find(x=>x.id===target.dataset.todo);return work(async()=>{S.health=await api('/api/profile/todo',{id:t.id,done:!t.done_on});render();});}
  if(target.dataset.forget){const f=target.dataset.forget;if(f==='everything'&&!confirm('Forget your whole profile and all saved care journeys? This can’t be undone.'))return;return work(async()=>{S.health=await api('/api/profile/forget',{field:f,value:target.dataset.value||''});S.state=await api('/api/state');if(f==='everything'){editProfile();return;}render();});}
  if(target.dataset.sign){S.input.no_signs=false;const id=target.dataset.sign;S.input.checks=S.input.checks.includes(id)?S.input.checks.filter(x=>x!==id):[...S.input.checks.filter(x=>S.choices.some(c=>c.id===x&&lvl(c)==='emergency')),id];
    return work(async()=>{S.safety=await api('/api/safety',{checks:S.input.checks});render();$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});});}
  if(target.dataset.none){S.input.no_signs=!S.input.no_signs;if(S.input.no_signs){S.input.checks=S.input.checks.filter(x=>!S.choices.some(c=>c.id===x&&lvl(c)==='emergency'));S.safety=null;}render();return;}
  if(target.dataset.chip){collect();if(S.input.service==='same_day')S.input.service='primary_care';const id=target.dataset.chip;S.input.checks=S.input.checks.includes(id)?S.input.checks.filter(x=>x!==id):[...S.input.checks,id];
    return work(async()=>{const r=await api('/api/safety',{checks:S.input.checks,description:S.input.description});S.safety=r.level==='emergency'?r:null;render();if(S.safety)$('#safety-result')?.scrollIntoView({behavior:'smooth',block:'center'});});}
  if(target.dataset.need){collect();const n=NEEDS.find(x=>x[0]===target.dataset.need);S.input.need=n[0];S.input.service=n[3];S.input.checks=n[2]?[n[2]]:[];render();return;}
  if(target.dataset.sub){collect();S.sub=target.dataset.sub;S.open=new Set();S.safety=null;if(S.sub==='start')S.input.checks=[];render();return;}
  if(target.dataset.insurance){collect();S.input.insurance=target.dataset.insurance;S.preview=null;render();return;}
  if(target.dataset.wants){collect();S.input.wants_insurance=target.dataset.wants==='yes';render();return;}
  if(target.dataset.quote)return quoteDialog(target.dataset.quote);
  if(target.dataset.prepare)return preparationDialog(target.dataset.prepare);
  if(target.dataset.case)return work(async()=>{S.current=await api('/api/case?id='+encodeURIComponent(target.dataset.case));S.step=4;closeDialog();render();});
  const action=target.dataset.action;
  if(action==='close')return closeDialog();
  if(action==='back'){collect();S.step--;S.preview=null;render();return;}
  if((action==='home'||action==='new')&&S.state.unlocked){S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.current=null;S.preview=null;S.view='home';return work(async()=>{S.health=await api('/api/profile');render();window.scrollTo(0,0);});}
  if(action==='home'||action==='new'){S.input=fresh();S.input.visit_date=S.state.today||today();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.step=0;S.current=null;S.preview=null;render();return;}
  if(action==='home-page'){if(!S.state.unlocked){S.view='gate';render();return;}S.view='home';S.expect=null;S.current=null;return work(async()=>{S.health=await api('/api/profile');render();window.scrollTo(0,0);});}
  if(action==='edit-profile')return editProfile();
  if(action==='start-over'){if(!confirm('Erase the saved health profile on this computer and start a new one? This can’t be undone.'))return;return work(async()=>{S.state=await api('/api/vault/reset',{confirm:'erase'});S.health=null;S.state.profile_ready=false;editProfile();});}
  if(action==='known'){S.view='known';return work(async()=>{S.health=await api('/api/profile');render();window.scrollTo(0,0);});}
  if(action==='care-today'){collect();S.input.service='same_day';return advance();}
  if(action==='see-places'){S.view='wizard';S.current=S.found;S.found=null;S.expect=null;S.step=4;render();window.scrollTo(0,0);return;}
  if(action==='health'){collect();S.step=0;S.sub='symptoms';S.safety=null;S.preview=null;render();window.scrollTo(0,0);return;}
  if(action==='boston'){collect();Object.assign(S.input,{city:'Boston',state:'MA',zip:'',lat:null,lon:null});render();return;}
  if(action==='demo'){
    const year=today().slice(0,4);S.safety=null;S.input={...fresh(),demo:true,insurance:'no',wants_insurance:true,lat:42.3505,lon:-71.1054,language:'Chinese',budget:200,age:28,none_reported:true,feel:'okay',need:'follow_up',service:'follow_up',
      description:'My clinician recommended a routine primary-care follow-up.',plan:{name:'Demo Student PPO',rule:'copay',premium:95,copay:25,deductible_remaining:50,coinsurance:20,oop_remaining:3000,start:year+'-01-01',end:year+'-12-31',eligible:false}};S.step=0;S.sub='need';S.view='wizard';S.preview=null;S.current=null;render();return;
  }
  if(action==='geolocate'){
    collect();if(!navigator.geolocation)return toast('Device location is unavailable. Enter your city instead.');
    navigator.geolocation.getCurrentPosition(position=>{S.input.lat=position.coords.latitude;S.input.lon=position.coords.longitude;render();toast('Coordinates stay on this device. Confirm your city before continuing.');},()=>toast('Location was unavailable or declined. You can continue with city and state.'),{timeout:10000,maximumAge:60000});return;
  }
  if(action==='plan')return planDialog();
  if(action==='contact')return contactDialog();
  if(action==='unlock'){S.view='gate';render();return;}
  if(action==='saved')return work(savedDialog);
  if(action==='privacy')return work(privacyDialog);
  if(action==='offline')return work(async()=>{S.state=await api('/api/offline',{offline:!S.state.offline});await privacyDialog();});
  if(action==='lock')return work(async()=>{S.state=await api('/api/vault/lock',{});S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.current=null;S.step=0;S.preview=null;S.health=null;S.view='gate';closeDialog();render();toast('Vault locked. Private information cleared from this page.');});
  if(action==='model-prep')return work(async()=>{if($('#prep-output'))$('#prep-output').textContent='Preparing a draft with your local model…';showPrep(await api('/api/case/preparation',{id:S.current.id,use_model:true}));});
  if(action==='copy-prep')return work(async()=>{const script=$('#script-text')?.textContent;if(!script)throw Error('Prepare a script first.');await navigator.clipboard.writeText(script);toast('Copied. You control where you share it.');});
});
document.addEventListener('change',event=>{if(!event.target.name?.endsWith('_rule'))return;const box=event.target.closest('form')||document;box.querySelectorAll('[data-rule-fields]').forEach(el=>{el.hidden=el.dataset.ruleFields!==event.target.value;});});
$('#dialog').addEventListener('cancel',()=>{$('#dialog').innerHTML='';});
async function init(){try{S.state=await api('/api/state');S.input.visit_date=S.state.today;S.choices=(await api('/api/safety/choices')).choices;
  if(S.state.unlocked){await afterUnlock();return;}
  if(S.state.vault_exists){S.view='gate';}else{S.state.profile_ready=false;editProfile();return;}
}catch(e){toast(e.message);S.view='gate';}render();}
init();
setInterval(async()=>{if(S.busy||!S.state.unlocked)return;try{const state=await api('/api/state');if(!state.unlocked){S.state=state;S.input=fresh();S.safety=null;S.expect=null;S.found=null;S.sub='symptoms';S.current=null;S.step=0;S.preview=null;S.health=null;S.view='gate';closeDialog();render();toast('Your vault locked after inactivity. Unlock to resume your saved journey.');}}catch{}},30000);
