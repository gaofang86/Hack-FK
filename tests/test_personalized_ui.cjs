const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const helpers = source.split('\n').filter(line=>/^(const esc =|const dollars =|const serviceName=)/.test(line)).join('\n');
const start = source.indexOf('const PRIORITY_LABELS=');
const end = source.indexOf('function renderResults()', start);
const context = {I18n:{locale:'en'},directionsLink:()=>'',bookingLink:()=>''};
vm.runInNewContext(helpers+'\n'+source.slice(start,end)+'\nglobalThis.ui={personalizedContext,nextStepPanel};',context);
const {personalizedContext,nextStepPanel}=context.ui;

function careCase() {
  return {status:'comparing',input:{service:'follow_up',language:'Spanish',budget:120,priority:'cost',
    insurance:'no',visit_date:'2026-11-08',zip:'02445',state:'MA'},next_action:'Confirm the exact service',
    results:[{provider:{id:'backup',name:'Backup clinic'},unavailable:true},
             {provider:{id:'active',name:'Available clinic'},unavailable:false}]};
}

test('preferences reflect this task rather than an example profile; text is escaped',()=>{
  const c=careCase();
  const html=personalizedContext(c);
  assert.ok(html.includes('Spanish'));
  assert.ok(html.includes('$120.00'));
  assert.ok(html.includes('02445'));
  assert.ok(html.includes('Cost first'));
  assert.ok(!html.includes('NUSHP'));
  c.input.insurance='yes';c.input.plan={name:'<script>bad()</script>'};
  assert.ok(!personalizedContext(c).includes('<script>'));
  assert.ok(personalizedContext(c).includes('&lt;script&gt;'));
});

test('next action skips unavailable clinics and binds both actions to the same candidate',()=>{
  const html=nextStepPanel(careCase());
  assert.ok(html.includes('Available clinic'));
  assert.ok(html.includes('data-prepare="active"'));
  assert.ok(html.includes('data-answer="active"'));
  assert.ok(!html.includes('data-prepare="backup"'));
});

test('a recorded booking prepares the booked provider even with an older negative reply',()=>{
  const c=careCase();c.status='booked';c.contact={provider_id:'backup'};
  const html=nextStepPanel(c);
  assert.ok(html.includes('data-prepare="backup"'));
  assert.ok(!html.includes('data-answer='));
});

test('no actionable clinic leads to another candidate; attended care leads to follow-ups',()=>{
  const c=careCase();c.results.forEach(r=>r.unavailable=true);
  assert.ok(nextStepPanel(c).includes('data-action="add-candidate"'));
  assert.ok(!nextStepPanel(c).includes('data-prepare='));
  c.status='attended';
  assert.ok(nextStepPanel(c).includes('data-action="home-page"'));
  assert.ok(!nextStepPanel(c).includes('data-answer='));
});

test('a chosen clinic shows the contact checklist, ticked from saved data',()=>{
  const c=careCase();c.contact={provider_id:'active'};c.preparation={provider_id:'active'};
  c.results[1].provider.answers=[{key:'language'}];
  const html=nextStepPanel(c);
  assert.ok(html.includes('contact-checklist'));assert.ok(html.includes('data-answer="active"'));assert.ok(html.includes('data-action="mark-booked"'));
  assert.equal((html.match(/<li class="done">/g)||[]).length,2); // script prepared + reply recorded
  assert.ok(html.includes('not a booking'));
});
