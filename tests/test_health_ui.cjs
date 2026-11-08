const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const helpers=src.split('\n').filter(l=>/^(const esc =)/.test(l)).join('\n');
const todoRow=src.slice(src.indexOf('function todoRow('),src.indexOf('const JOURNEY_KINDS='));
const health=src.slice(src.indexOf('const COVERAGE_LABEL='),src.indexOf('function listRows('));
const src_={url:'https://www.uspreventiveservicestaskforce.org/',title:'USPSTF A and B recommendations'};
function overview(extra={}){
 return {scope:'只整理你填写或核对过的事实 / Only facts you entered or reviewed.',
  overview:{age:24,sex:'female',language:'English',coverage:'insured',plan:'SYNTHETIC PPO',conditions:[],medications:['Med A'],allergies:[],follow_ups:[{what:'Repeat blood test',due:'2026-11-20'}],
   reports:[{id:'r1',label:'firstvisit-lab-demo.pdf',reviewed_on:'2026-11-08',rows:17,flagged:1}],last_visit:null,visits:0},
  attention:{report_flags:[{report_id:'r1',report:'firstvisit-lab-demo.pdf',reviewed_on:'2026-11-08',name:'Creatinine',result:'0.52 mg/dL',reference:'0.57-1.00',flag:'Low',
    note:'标记照抄自报告，不是诊断 / Flag copied from the report, not a diagnosis',ask:'My report marks Creatinine 0.52 mg/dL as “Low” (reported range: 0.57-1.00). What does this mean for me?'}],
   due:[{id:'follow:Repeat blood test',kind:'follow_up',title:'Repeat blood test',why:'Due by 2026-11-20.'}],
   preventive:[{id:'bp',kind:'screening',title:'Blood pressure check',why:'Recommended for adults 18 and older.',source:src_}],done:[],needs_birth_year:false},
  plan_direction:{coverage:'insured',note:'Counts come only from what’s on file.',has_sbc:true,
   expected_use:[{need:'primary',label:'Primary care visits',count:2,basis:['1 yearly checkup (preventive)','A visit to ask about 1 flagged report row(s)']},{need:'labs',label:'Lab tests',count:1,basis:['Follow-up: Repeat blood test']}],
   needs:{primary:2,labs:1},current_plan:[{need:'primary',label:'Primary care visits',value:'$25.00 copay'},{need:'labs',label:'Lab tests',value:'未知，不按 0 计算 / Unknown, not $0'}],
   look_for:[{title:'The out-of-pocket maximum',why:'The most you pay.',source:{url:'https://www.healthcare.gov/',title:'HealthCare.gov'}}],choices:[]},...extra};
}
function fixture(o){
 const app={innerHTML:''},c={S:{overview:o,view:'health',state:{unlocked:true,preview_mode:false,cases:[{id:'c1',status:'planning',next_action:'Call the clinic'}]}},
  $:s=>s==='#app'?app:null,meChips:()=>'<div class="me"></div>',icon:()=>'',api:async()=>o,toast(){},render(){}};
 vm.runInNewContext(helpers+'\n'+todoRow+'\n'+health+'\nglobalThis.renderHealth=renderHealth;globalThis.flagRow=healthFlagRow;',c);
 return {c,app};
}
test('My health shows overview, needs attention and plan direction, and no task list',()=>{
 const {c,app}=fixture(overview());c.renderHealth();const html=app.innerHTML;
 const at=['概况 / Overview','需要留意 / Needs attention','选保险的方向 / Plan direction'].map(t=>html.indexOf(t));
 assert.ok(at.every(i=>i>0));assert.deepEqual([...at].sort((a,b)=>a-b),at);
 assert.ok(!html.includes('Continue your care'));assert.ok(!html.includes('data-case='));assert.ok(!html.includes('Call the clinic'));
});
test('a report can be added and forgotten from My health',()=>{
 const {c,app}=fixture(overview());c.renderHealth();const html=app.innerHTML;
 assert.match(html,/<input type="file" id="health-lab-file" accept="application\/pdf"/);
 assert.ok(html.includes('data-forget-health-report="r1"'));assert.ok(html.includes('17 rows'));
});
test('report flags are quoted verbatim, kept untranslated, and labeled as not a diagnosis',()=>{
 const {c}=fixture(overview());const row=c.flagRow(overview().attention.report_flags[0]);
 assert.match(row,/data-i18n-keep><strong>Creatinine<\/strong> <span>0\.52 mg\/dL<\/span> <span class="muted">reference 0\.57-1\.00<\/span> <span class="flag-chip">Low<\/span>/);
 assert.ok(row.includes('Flag copied from the report, not a diagnosis'));assert.ok(row.includes('<q>My report marks Creatinine'));
 assert.ok(!/abnormal|you have/i.test(row));
});
test('plan direction links to plan comparison and entry D, and shows unknown plan costs as unknown',()=>{
 const {c,app}=fixture(overview());c.renderHealth();const html=app.innerHTML;
 assert.ok(html.includes('data-action="health-compare-plans"'));assert.ok(html.includes('data-action="health-insurance"'));
 assert.ok(html.includes('Lab tests</span><strong>× 1'));assert.ok(html.includes('Unknown, not $0'));assert.ok(html.includes('$25.00 copay'));
});
test('user text is escaped and a missing overview is fetched, not rendered empty',async()=>{
 const o=overview();o.overview.reports[0].label='<img src=x>';o.attention.report_flags[0].name='<b>x</b>';
 const {c,app}=fixture(o);c.renderHealth();assert.ok(!app.innerHTML.includes('<img src=x>'));assert.ok(!app.innerHTML.includes('<b>x</b>'));
 const empty=fixture(null);let rendered=false;empty.c.render=()=>{rendered=true;};empty.c.renderHealth();assert.ok(empty.app.innerHTML.includes('Loading'));
 await new Promise(r=>setImmediate(r));assert.ok(rendered);
});
test('nothing due shows a calm empty state; missing birth year asks for it',()=>{
 const o=overview();o.attention={report_flags:[],due:[],preventive:[],done:[],needs_birth_year:false};
 let f=fixture(o);f.c.renderHealth();assert.ok(f.app.innerHTML.includes('Nothing needs attention'));
 o.attention.needs_birth_year=true;f=fixture(o);f.c.renderHealth();assert.ok(f.app.innerHTML.includes('Add your birth year'));
});
test('the shared report review screen saves My health reports to My health',()=>{
 const review=src.slice(src.indexOf('function renderReportReview('),src.indexOf('const prepSections='));
 assert.ok(review.includes("if(draft.for_health){S.overview=await api('/api/health/reports/confirm',body)"));
 assert.ok(review.includes("S.view='health'"));
});
test('a saved report opens to an at-a-glance summary before its full results, and visits are listed',()=>{
 const o=overview();
 o.overview.reports=[{id:'r1',label:'firstvisit-lab-demo.pdf',reviewed_on:'2026-11-08',rows:2,flagged:1,
  digest:{total:2,not_flagged:1,low:1,high:0,note:'n',flagged:[{name:'Creatinine',result:'0.52 mg/dL',reference:'0.57-1.00',flag:'Low',position:{low:'0.57',high:'1.00',pct:19.2}}]},
  results:[{name:'Glucose',result:'98 mg/dL',reference:'70-99',flag:''},{name:'<b>Creatinine</b>',result:'0.52 mg/dL',reference:'0.57-1.00',flag:'Low'}]}];
 o.overview.visit_history=[{date:'2026-11-02',reason:'SYNTHETIC checkup',place:'Clinic',notes:'',added:{follow_ups:['Recheck']}}];
 const {c,app}=fixture(o);c.renderHealth();const html=app.innerHTML;
 assert.ok(html.indexOf('At a glance')>0&&html.indexOf('At a glance')<html.indexOf('report-table'));
 assert.ok(html.includes('range-dot at-20'));assert.ok(html.includes('1 Low · 0 High'));
 assert.ok(html.indexOf('&lt;b&gt;Creatinine')<html.indexOf('Glucose'));  // flagged first, escaped
 assert.ok(!html.includes('<b>Creatinine'));
 assert.ok(html.includes('SYNTHETIC checkup')&&html.includes('Added: Recheck'));
});
