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
  priority:'balanced',months:1,adult:false,routine_confirmed:false,demo:false,plan:null});
const S = {step:0, input:fresh(), state:{services:{},cases:[]}, preview:null, current:null, busy:false};

async function api(path, body) {
  const response = await fetch(path, {method:body === undefined ? 'GET':'POST', headers:{'X-FirstVisit':'local','Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 423 && S.state.unlocked) {
      S.state.unlocked = false; S.current = null; S.input = fresh(); S.step = 0; S.preview = null; closeDialog(); render();
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
  const p = plan || {};
  return `<div class="form-grid">
    ${field('Exact plan / network name',prefix+'name',p.name,'text','placeholder="Copy the full name from the plan" maxlength="120"')}
    ${field('Monthly premium you would pay ($)',prefix+'premium',p.premium,'number','min="0" max="1000000" step="0.01" placeholder="Optional; needed for total comparison"')}
    ${field('Coverage starts',prefix+'start',p.start,'date')}${field('Coverage ends (if known)',prefix+'end',p.end,'date')}
    ${select('Benefit for this type of visit',prefix+'rule', [['copay','Copay; deductible does not apply'],['deductible','Deductible, then coinsurance']],p.rule || 'copay')}
    ${field('Visit copay ($)',prefix+'copay',p.copay,'number','min="0" step="0.01" placeholder="For the copay rule only"')}
    ${field('Remaining deductible ($)',prefix+'deductible_remaining',p.deductible_remaining,'number','min="0" step="0.01" placeholder="For deductible-based benefits"')}
    ${field('Coinsurance you pay (%)',prefix+'coinsurance',p.coinsurance,'number','min="0" max="100" step="0.1"')}
    ${field('Remaining out-of-pocket limit ($)',prefix+'oop_remaining',p.oop_remaining,'number','min="0" step="0.01"')}
  </div><label class="checkline"><input name="${prefix}eligible" type="checkbox" ${p.eligible?'checked':''}><span>I confirmed my eligibility with the plan or marketplace.</span></label>
  <p class="hint">Use the benefit for this specific visit. Leave unknown values blank. A card alone does not confirm your remaining deductible or each provider’s network participation.</p>`;
}
function planResources() {
  return `<details class="private-details"><summary>Find your actual plan details</summary><div class="resource-list"><a href="https://studenthealthplan.northeastern.edu/" target="_blank" rel="noopener noreferrer">Northeastern student plan & benefit documents ↗</a><a href="https://betterhealthconnector.com/compare-plans" target="_blank" rel="noopener noreferrer">Massachusetts Health Connector plan comparison ↗</a><a href="https://providerdirectory.mahealthconnector.org/" target="_blank" rel="noopener noreferrer">Health Connector provider / plan directory ↗</a></div><p class="hint">Check the exact plan year and your enrollment before copying benefits. These are official information sources, not a personalized premium quote or an eligibility determination. Opening a source does not send your local health profile.</p></details>`;
}
function readPlan(form) {
  const f = new FormData(form), p = {};
  ['name','premium','start','end','rule','copay','deductible_remaining','coinsurance','oop_remaining'].forEach(k => p[k] = f.get('plan_'+k) ?? '');
  p.eligible = f.has('plan_eligible'); return p.name.trim() ? p : null;
}
function collect() {
  const form = $('#wizard'); if (!form) return;
  const f = new FormData(form);
  if(S.step===0 && (f.get('city')!==S.input.city || f.get('state')!==S.input.state)) {S.input.lat=null;S.input.lon=null;}
  for (const [k,v] of f) if (!k.startsWith('plan_') && !['passphrase','live','adult','routine_confirmed'].includes(k)) S.input[k] = v;
  if (S.step === 1 && $('[name="plan_name"]',form)) S.input.plan = readPlan(form);
  if (S.step === 2) { S.input.adult = f.has('adult'); S.input.routine_confirmed = f.has('routine_confirmed'); }
}
function renderHeader() {
  $('#header').innerHTML = `<div class="header-inner"><button class="brand" data-action="home" aria-label="FirstVisit home"><span class="brand-icon">${icon('heart')}</span>firstvisit<span class="brand-dot">.</span></button><nav aria-label="Main navigation">
    <span class="privacy-pill">${icon('lock')} ${S.state.preview_mode?'Temporary preview · fictional data only':'Local & private'}</span>
    <button class="nav-button" data-action="saved">My care journeys</button>
    <button class="nav-button" data-action="privacy">Privacy</button>
    ${S.state.unlocked ? '<button class="nav-button" data-action="lock">Lock vault</button>' : '<button class="nav-button" data-action="unlock">Unlock vault</button>'}
    </nav></div>`;
}
function sidebar() {
  const names=['Your location','Your coverage','Your care needs','Review & find care'];
  return `<aside class="journey-sidebar"><p class="eyebrow">A CLEARER PATH TO CARE</p><h1>Care that puts<br><em>you first.</em></h1><p class="sidebar-copy">A clearer path through US healthcare, built around international students in Boston.</p><ol class="steps">${names.map((n,i)=>`<li class="${S.step===i?'active':S.step>i?'done':''}"><span>${S.step>i?icon('check'):String(i+1).padStart(2,'0')}</span><div>${n}<small>${['Start close to home','With or without insurance','What matters to you','You control what is shared'][i]}</small></div></li>`).join('')}</ol><div class="sidebar-note">${icon('shield')}<p>Your health details stay on this device. Public searches use only the location and general care category you review.</p></div><button class="text-button" data-action="demo">Explore a fictional example ${icon('arrow')}</button></aside>`;
}
function stepContent() {
  const p=S.input;
  if (S.step===0) return `<div class="section-icon">${icon('pin')}</div><p class="eyebrow">01 / YOUR LOCATION</p><h2>Where should we look?</h2><p class="lede">Let’s start with care close to you.</p><div class="location-choice">${icon('pin')}<div><strong>Boston, Massachusetts</strong><span>Our first supported local directory</span></div><button type="button" class="text-button" data-action="boston">Use Boston</button></div><div class="form-grid">${field('City','city',p.city,'text','required maxlength="70" autocomplete="address-level2"')}${field('State','state',p.state,'text','required pattern="[A-Za-z]{2}" maxlength="2" autocomplete="address-level1"')}${field('ZIP code (optional)','zip',p.zip,'text','pattern="[0-9]{5}" maxlength="5" autocomplete="postal-code"')}</div><button type="button" class="secondary" data-action="geolocate">${icon('pin')} Add my device location</button><p class="hint">${p.lat!=null?'Coordinates added for local distance calculations. Confirm the city above.':'Precise coordinates stay local. They are optional; city and state are enough to start.'}</p><div class="soft-note">Our saved directory starts in Boston. Other cities require live discovery; results always show what still needs confirmation.</div>`;
  if (S.step===1) return `<div class="section-icon">${icon('shield')}</div><p class="eyebrow">02 / YOUR COVERAGE</p><h2>Do you have health insurance?</h2><p class="lede">Either way, there’s a path forward.</p><div class="choice-grid"><button type="button" class="choice ${p.insurance==='yes'?'selected':''}" data-insurance="yes"><span class="choice-radio"></span><strong>Yes, I have insurance</strong><span>Use my benefits and compare my personal cost.</span></button><button type="button" class="choice ${p.insurance==='no'?'selected':''}" data-insurance="no"><span class="choice-radio"></span><strong>No insurance right now</strong><span>Explore self-pay care and optional coverage.</span></button></div>
    ${p.insurance==='no'?`<div class="branch"><h3>Would you like to explore insurance?</h3><div class="segmented"><button type="button" class="${!p.wants_insurance?'selected':''}" data-wants="no">Continue without it</button><button type="button" class="${p.wants_insurance?'selected':''}" data-wants="yes">Compare getting a plan</button></div><p class="hint">You’ll see self-pay options in both cases. Check your school account first—you may already be enrolled in student coverage. Self-pay care does not replace school insurance requirements.</p></div>`:''}
    ${p.insurance==='yes'||p.wants_insurance?`<div class="branch"><h3>${p.insurance==='yes'?'Your current plan':'A plan you’re considering'}</h3><p class="hint">${p.insurance==='yes'?'Enter what you know. You can find providers before all your benefits are confirmed.':'Use an actual plan quote, or leave these blank and explore enrollment resources after your search.'}</p>${planFields(p.plan)}${planResources()}</div>`:''}`;
  if (S.step===2) return `<div class="section-icon">${icon('heart')}</div><p class="eyebrow">03 / YOUR CARE NEEDS</p><h2>What matters for this visit?</h2><p class="lede">A little context helps us organize care around you.</p><div class="form-grid">${select('What are you arranging?','service',[['primary_care','A primary-care appointment'],['follow_up','A primary-care follow-up'],['unsure','I’m unsure what care I need']],p.service)}${field('Planned visit date','visit_date',p.visit_date,'date',`required min="${today()}"`)}${select('Preferred language','language',[['English','English'],['Chinese','Chinese / 中文'],['Spanish','Spanish / Español']],p.language)}${field('Visit budget ($, optional)','budget',p.budget,'number','min="0" step="0.01" placeholder="Your comfort zone"')}</div>${select('Put this first','priority',[['balanced','My fit: language, budget, then cost'],['cost','Lowest supported personal cost'],['rating','Highest sourced patient rating'],['distance','Closest known location']],p.priority)}<label class="field"><span>What brings you here? <small>Optional · stays local</small></span><textarea name="description" rows="3" maxlength="3000" placeholder="For example: my doctor asked me to arrange a follow-up.">${esc(p.description)}</textarea></label><details class="private-details"><summary>Medical history & medications <span>Optional, private</span></summary><label class="field"><span>Relevant history or clinician instructions</span><textarea name="history" maxlength="3000" rows="3">${esc(p.history)}</textarea></label>${field('Current medications (optional)','medications',p.medications,'text','maxlength="1000"')}<p class="hint">Used locally to prepare your visit. This prototype does not infer diagnoses or select specialists from symptoms.</p></details><div class="care-boundary"><label class="checkline"><input type="checkbox" name="adult" ${p.adult?'checked':''} required><span>I’m arranging care for an adult (18+).</span></label><label class="checkline"><input type="checkbox" name="routine_confirmed" ${p.routine_confirmed?'checked':''} required><span>I’m arranging known non-emergency outpatient care.</span></label><p>If you need help deciding what care you need, contact a clinician or nurse line. If you think you may have an emergency, call 911. This search cannot assess urgency.</p></div>`;
  const queries = S.preview?.queries || [];
  return `<div class="section-icon">${icon('lock')}</div><p class="eyebrow">04 / REVIEW & FIND CARE</p><h2>Your information. Your control.</h2><p class="lede">Here’s what we’ll use to find your next step.</p><div class="review-list"><div><span>Search area</span><strong>${esc(p.city)}, ${esc(p.state)} ${esc(p.zip)}</strong></div><div><span>Care</span><strong>${p.service==='follow_up'?'Primary-care follow-up':'Primary-care appointment'}</strong></div><div><span>Payment</span><strong>${p.insurance==='yes'?'Insurance + self-pay comparison':p.wants_insurance?'Self-pay + optional insurance scenario':'Self-pay; optional comparison later'}</strong></div></div><div class="privacy-box"><div>${icon('shield')}<strong>Stays on this device</strong></div><p>Health history, current concerns, medications, exact coordinates, benefits, and personal rankings.</p></div>
    ${!S.state.unlocked?`<div class="branch"><h3>${S.state.vault_exists?'Unlock your private vault':'Create your private vault'}</h3>${field('Vault passphrase','passphrase','','password',`required minlength="8" maxlength="1000" autocomplete="${S.state.vault_exists?'current-password':'new-password'}"`)}<p class="hint">Encrypts saved care journeys on this computer. Keep your passphrase safe; there is no password recovery.</p></div>`:''}
    ${S.preview?`<div class="branch"><h3>${queries.length?'Public search preview':'Ready to compare'}</h3>${queries.map(q=>`<div class="query"><span>${esc(q.provider)}</span><code>${esc(q.query)}</code></div>`).join('')}<p class="hint">${queries.length?`Recipients: ${S.preview.destinations.map(esc).join(', ')}. Search providers can infer a general interest in this care category.`:p.demo?'No external search. All sample providers, prices, reviews and plan relationships are fictional.':'No live search connection is configured. The Boston directory has official source links; prices and coverage require confirmation.'}</p>${queries.length?'<label class="checkline"><input type="checkbox" name="live" checked><span>Send these queries to find additional providers. Uncheck to use the local directory only.</span></label>':''}</div>`:'<p class="hint">The next step previews any public queries before you approve sending them.</p>'}`;
}
function render() {
  renderHeader();
  if (S.step===4 && S.current) return renderResults();
  $('#app').innerHTML = `<div class="wizard-layout">${sidebar()}<section class="form-panel">${S.input.demo?'<div class="demo-banner">FICTIONAL DEMO · No actual providers, prices, ratings or insurance offers</div>':''}<form id="wizard">${stepContent()}<div class="form-actions">${S.step>0?'<button type="button" class="text-button" data-action="back">← Back</button>':'<span class="small-note">A few steps to a clearer choice.</span>'}<button type="submit" class="primary">${S.step===3?(S.preview?'Find my care':'Review search'):'Continue'} ${icon('arrow')}</button></div><div id="working" role="status" class="working"></div></form></section></div>`;
  $('#wizard').addEventListener('submit', event => {event.preventDefault(); advance();});
}
async function advance() {
  if (!$('#wizard').reportValidity()) return;
  collect();
  if(S.step===1 && !S.input.insurance) return toast('Choose whether you have insurance.');
  if(S.step===2 && S.input.service==='unsure') return toast('Please contact a clinician or nurse line to establish the right care before comparing providers.');
  if(S.step<3) {S.step++; S.preview=null; render(); window.scrollTo(0,0); return;}
  await work(async()=>{
    if (!S.state.unlocked) {
      const passphrase=$('[name="passphrase"]').value;
      S.state=await api(S.state.vault_exists?'/api/vault/unlock':'/api/vault/create',{passphrase});
      $('[name="passphrase"]').value='';
    }
    if(!S.preview) {S.preview=await api('/api/preview',S.input); render(); return;}
    S.current=await api('/api/search',{token:S.preview.token,approved:true,live:!!$('[name="live"]')?.checked});
    S.preview=null; S.step=4; S.state=await api('/api/state'); render(); window.scrollTo(0,0);
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
function renderResults() {
  const c=S.current,p=c.input,known=c.results.filter(r=>r.supported&&r.cost.amount!=null),min=known.length?Math.min(...known.map(r=>r.cost.amount)):null;
  $('#app').innerHTML=`<div class="results-page">${p.demo?'<div class="demo-banner">FICTIONAL DEMO · These are not actual care recommendations or insurance offers.</div>':''}<div class="results-heading"><div><p class="eyebrow">YOUR NEXT STEP, A LITTLE CLEARER</p><h1>Care around <em>you.</em></h1><p>${esc(p.city)}, ${esc(p.state)} <span class="dot">·</span> ${p.service==='follow_up'?'Primary-care follow-up':'Primary-care appointment'} <span class="dot">·</span> ${esc(p.visit_date)}</p></div><button class="secondary" data-action="new">Start a new search ${icon('arrow')}</button></div><div class="result-metrics"><div><span>OPTIONS FOUND</span><strong>${c.results.length}<small> in your shortlist</small></strong></div><div><span>LOWEST SUPPORTED COST</span><strong>${dollars(min)}<small>${known.length?' for this visit':' · confirm quotes first'}</small></strong></div><div><span>YOUR HEALTH PROFILE</span><strong>${icon('lock')} Stays local</strong></div></div>${c.errors.length?`<div class="notice">Live discovery had a problem: ${c.errors.map(esc).join('; ')}. Available local results remain below.</div>`:''}<div class="results-layout"><section><div class="results-toolbar"><div><h2>Your shortlist</h2><p>Ordered by your preferences, among the options found.</p></div>${select('Sort by','result_priority',[['balanced','My fit'],['cost','Lowest cost'],['rating','Patient rating'],['distance','Distance']],p.priority)}</div>${c.results.length?c.results.map(providerCard).join(''):'<div class="empty"><h3>No local providers found here yet.</h3><p>Live discovery is not connected. You can use the official health-center finder below; this shortlist will not substitute providers from another city.</p><a href="https://findahealthcenter.hrsa.gov/" target="_blank" rel="noopener noreferrer">Find a community health center ↗</a></div>'}</section><aside class="results-aside"><div class="aside-panel"><span class="aside-icon">${icon('shield')}</span><h3>${p.insurance==='yes'?'Make your benefits work for you.':'Would insurance change the picture?'}</h3><p>Compare the same visit, then include what the plan itself costs.</p>${p.plan?`<div class="plan-chip"><span>PLAN SCENARIO</span><strong>${esc(p.plan.name)}</strong><small>${p.plan.start?'Starts '+esc(p.plan.start):'Start date unconfirmed'} · ${p.plan.eligible?'Eligibility entered as confirmed':'Eligibility unconfirmed'}</small></div>`:'<p class="hint">No plan entered. Add a quote to calculate a scenario; unknown prices stay unknown.</p>'}<button class="primary full" data-action="plan">${p.plan?'Edit plan comparison':'Compare an insurance plan'} ${icon('arrow')}</button><p class="hint">Potential savings depend on eligibility, coverage dates, exact network and benefit rules. A lower visit copay does not always mean a lower total.</p><a href="${p.state==='MA'?'https://betterhealthconnector.com/get-started/individuals-families':'https://www.healthcare.gov/see-plans/'}" target="_blank" rel="noopener noreferrer" class="text-button">Explore official coverage options ↗</a></div><div class="aside-panel quiet"><h3>What we know. What we don’t.</h3><p>${p.demo?'This sample illustrates the complete comparison with fictional data.':c.live_searched?'Live discovery adds leads to a small sourced directory. Search matches still need provider confirmation.':'This is a small sourced directory, not an exhaustive search.'}</p><p>Appointments, exact networks and complete charges need confirmation. Unknown price never means free.</p><a href="https://www.healthcare.gov/choose-a-plan/your-total-costs/" target="_blank" rel="noopener noreferrer">How health costs work ↗</a></div><div class="aside-panel quiet"><h3>Your ongoing care journey</h3><p>Status: <strong>${esc(c.status)}</strong></p><p class="hint">A booking link does not confirm an appointment. Record the outcome after contacting the provider.</p><button class="text-button" data-action="contact">Update appointment status →</button></div></aside></div></div>`;
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
  openDialog('Add a quote or confirmation',`<p>${esc(p.name)} · ${S.current.input.service==='follow_up'?'Primary-care follow-up':'Primary-care appointment'}</p><form id="quote-form"><div class="form-grid">${field('Complete self-pay quote ($)','cash',p.cash.amount,'number','min="0" step="0.01"')}${field('Date you checked','checked_on',today(),'date',`required max="${today()}"`)}${field('Exact plan / network name','plan_name',plan?.name)}${field('Allowed amount for this service ($)','allowed_amount','','number','min="0" step="0.01"')}</div>${field('Source (person, quote reference, or URL)','source','','text','required placeholder="For example: billing office call, Nov 7" maxlength="500"')}<label class="checkline"><input type="checkbox" name="service_confirmed"><span>I confirmed this location offers this service for adult patients.</span></label><label class="checkline"><input type="checkbox" name="scope_confirmed"><span>I confirmed the quote covers the defined visit, including applicable facility/professional fees.</span></label><label class="checkline"><input type="checkbox" name="network_confirmed"><span>I confirmed this exact plan, provider, location and service are in-network.</span></label><details class="private-details"><summary>Add sourced patient reviews (optional)</summary><div class="form-grid">${field('Patient rating (0–5)','rating','','number','min="0" max="5" step="0.1"')}${field('Number of reviews','rating_count','','number','min="1" step="1"')}</div>${field('Rating source URL','rating_source','','url')}</details><p class="hint">Saved as user-entered evidence, not independently verified. Additional services are excluded from the visit comparison.</p><button type="submit" class="primary">Save & rerank ${icon('arrow')}</button></form>`,true);
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
  if(target.dataset.insurance){collect();S.input.insurance=target.dataset.insurance;S.preview=null;render();return;}
  if(target.dataset.wants){collect();S.input.wants_insurance=target.dataset.wants==='yes';render();return;}
  if(target.dataset.quote)return quoteDialog(target.dataset.quote);
  if(target.dataset.prepare)return preparationDialog(target.dataset.prepare);
  if(target.dataset.case)return work(async()=>{S.current=await api('/api/case?id='+encodeURIComponent(target.dataset.case));S.step=4;closeDialog();render();});
  const action=target.dataset.action;
  if(action==='close')return closeDialog();
  if(action==='back'){collect();S.step--;S.preview=null;render();return;}
  if(action==='home'||action==='new'){S.input=fresh();S.step=0;S.current=null;S.preview=null;render();return;}
  if(action==='boston'){collect();Object.assign(S.input,{city:'Boston',state:'MA',zip:'',lat:null,lon:null});render();return;}
  if(action==='demo'){
    const year=today().slice(0,4);S.input={...fresh(),demo:true,insurance:'no',wants_insurance:true,lat:42.3505,lon:-71.1054,language:'Chinese',budget:200,adult:true,routine_confirmed:true,
      description:'My clinician recommended a routine primary-care follow-up.',plan:{name:'Demo Student PPO',rule:'copay',premium:95,copay:25,deductible_remaining:50,coinsurance:20,oop_remaining:3000,start:year+'-01-01',end:year+'-12-31',eligible:false}};S.step=0;S.preview=null;S.current=null;render();return;
  }
  if(action==='geolocate'){
    collect();if(!navigator.geolocation)return toast('Device location is unavailable. Enter your city instead.');
    navigator.geolocation.getCurrentPosition(position=>{S.input.lat=position.coords.latitude;S.input.lon=position.coords.longitude;render();toast('Coordinates stay on this device. Confirm your city before continuing.');},()=>toast('Location was unavailable or declined. You can continue with city and state.'),{timeout:10000,maximumAge:60000});return;
  }
  if(action==='plan')return planDialog();
  if(action==='contact')return contactDialog();
  if(action==='unlock')return unlockDialog();
  if(action==='saved')return work(savedDialog);
  if(action==='privacy')return work(privacyDialog);
  if(action==='offline')return work(async()=>{S.state=await api('/api/offline',{offline:!S.state.offline});await privacyDialog();});
  if(action==='lock')return work(async()=>{S.state=await api('/api/vault/lock',{});S.input=fresh();S.current=null;S.step=0;S.preview=null;closeDialog();render();toast('Vault locked. Private information cleared from this page.');});
  if(action==='model-prep')return work(async()=>{if($('#prep-output'))$('#prep-output').textContent='Preparing a draft with your local model…';showPrep(await api('/api/case/preparation',{id:S.current.id,use_model:true}));});
  if(action==='copy-prep')return work(async()=>{const script=$('#script-text')?.textContent;if(!script)throw Error('Prepare a script first.');await navigator.clipboard.writeText(script);toast('Copied. You control where you share it.');});
});
$('#dialog').addEventListener('cancel',()=>{$('#dialog').innerHTML='';});
async function init(){try{S.state=await api('/api/state');S.input.visit_date=S.state.today;}catch(e){toast(e.message);}render();}
init();
setInterval(async()=>{if(S.busy||!S.state.unlocked)return;try{const state=await api('/api/state');if(!state.unlocked){S.state=state;S.input=fresh();S.current=null;S.step=0;S.preview=null;closeDialog();render();toast('Your vault locked after inactivity. Unlock to resume your saved journey.');}}catch{}},30000);
